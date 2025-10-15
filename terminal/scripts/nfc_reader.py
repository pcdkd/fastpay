#!/usr/bin/env python3
"""
FastPay NFC Reader - Production Version

This script runs as a child process spawned by Node.js terminal.
It continuously scans for NFC device taps and outputs JSON events via stdout.

IPC Protocol (stdout):
  - JSON events for Node.js to parse
  - One event per line
  - Events: ready, tap, error, shutdown, heartbeat

Logging (stderr):
  - Debug messages for diagnostics
  - Does not interfere with JSON IPC

Environment Variables:
  - NFC_PORT: Serial port path (required)
  - NFC_BAUD_RATE: Baudrate (default: 115200)
  - NFC_TAP_DEBOUNCE_MS: Debounce window in ms (default: 1000)
  - NFC_DEDUP_BUFFER_SIZE: UID dedup buffer size (default: 10)
"""

import os
import sys
import time
import json
import signal
import serial
from collections import deque
from adafruit_pn532.uart import PN532_UART

# Timing constants (extracted magic numbers)
SERIAL_TIMEOUT_S = 1.0
SIGNAL_STABILIZE_DELAY_S = 0.2
NFC_SCAN_TIMEOUT_S = 0.5
HEARTBEAT_INTERVAL_S = 30
BACKOFF_CHECK_INTERVAL_S = 0.5  # Check shutdown/heartbeat during backoff

# Configuration from environment with robust validation
try:
    PORT = os.getenv('NFC_PORT')
    if not PORT:
        raise ValueError("NFC_PORT environment variable not set")
    BAUD_RATE = int(os.getenv('NFC_BAUD_RATE', '115200'))
    DEBOUNCE_MS = int(os.getenv('NFC_TAP_DEBOUNCE_MS', '1000'))
    DEDUP_BUFFER_SIZE = int(os.getenv('NFC_DEDUP_BUFFER_SIZE', '10'))
except ValueError as e:
    print(json.dumps({
        "event": "error",
        "message": f"Configuration error: {e}",
        "fatal": True,
        "timestamp": int(time.time())
    }), flush=True)
    sys.exit(1)

# UID deduplication buffer
recent_taps = deque(maxlen=DEDUP_BUFFER_SIZE)

# Reconnection settings
MAX_RETRIES = 5
retry_count = 0

# Heartbeat tracking (use monotonic time for intervals)
last_heartbeat = time.monotonic()

# Graceful shutdown flag
shutdown_requested = False
fatal_exit = False  # Track if we had a fatal error

# Resource handles
uart = None
pn532 = None


def emit_event(event_type, **data):
    """Output JSON event to stdout (Node.js reads this)"""
    event = {
        "event": event_type,
        "timestamp": int(time.time()),  # Wall clock time for timestamps
        **data
    }
    print(json.dumps(event), flush=True)


def log_debug(message):
    """Output debug info to stderr (doesn't interfere with IPC)"""
    print(f"[NFC] {message}", file=sys.stderr, flush=True)


def cleanup_resources():
    """Close serial port and release resources"""
    global uart, pn532
    try:
        if uart and uart.is_open:
            uart.close()
            log_debug("Serial port closed")
    except Exception as e:
        log_debug(f"Error closing serial port: {e}")
    finally:
        uart = None
        pn532 = None


def handle_shutdown(signum, frame):
    """Handle SIGINT and SIGTERM gracefully"""
    global shutdown_requested
    shutdown_requested = True
    emit_event('shutdown', reason=f'Signal {signum} received')
    log_debug(f'Shutdown signal {signum} received')
    # Don't call sys.exit() here - let main loop cleanup and exit


# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def is_duplicate_tap(uid_hex):
    """Check if this UID was tapped recently (within debounce window)"""
    now = time.monotonic()  # Use monotonic time for interval measurement
    for tap in recent_taps:
        if tap['uid'] == uid_hex and (now - tap['time']) < DEBOUNCE_MS / 1000:
            return True
    return False


def record_tap(uid_hex):
    """Record this tap in deduplication buffer"""
    recent_taps.append({
        'uid': uid_hex,
        'time': time.monotonic()  # Use monotonic time for interval measurement
    })


def send_heartbeat_if_needed():
    """Send heartbeat event every 30 seconds to prove process is alive"""
    global last_heartbeat
    now = time.monotonic()  # Use monotonic time for interval measurement
    if now - last_heartbeat >= HEARTBEAT_INTERVAL_S:
        emit_event('heartbeat')
        last_heartbeat = now


def interruptible_sleep(total_seconds):
    """
    Sleep in short intervals, allowing heartbeat emission and shutdown checks.
    Returns True if sleep completed, False if interrupted by shutdown.
    """
    end_time = time.monotonic() + total_seconds
    while time.monotonic() < end_time and not shutdown_requested:
        # Sleep in short bursts
        remaining = end_time - time.monotonic()
        time.sleep(min(BACKOFF_CHECK_INTERVAL_S, remaining))
        # Send heartbeat during long waits
        send_heartbeat_if_needed()
    return not shutdown_requested


def handle_retry(error_type, error_message):
    """
    Common retry/backoff handler for all recoverable errors.
    Returns True if should retry, False if max retries reached.
    """
    global retry_count

    log_debug(f"{error_type} error: {error_message}")
    emit_event('error', message=f"{error_type} error: {error_message}", fatal=False)
    cleanup_resources()

    retry_count += 1
    if retry_count >= MAX_RETRIES:
        emit_event('error', message="Max retries reached", fatal=True)
        log_debug("Max retries reached, exiting")
        return False

    # Exponential backoff with interruptible sleep
    wait_time = 2 ** retry_count
    log_debug(f"Retrying in {wait_time} seconds... (attempt {retry_count}/{MAX_RETRIES})")

    # Use interruptible sleep to allow heartbeats and shutdown
    if not interruptible_sleep(wait_time):
        log_debug("Retry interrupted by shutdown signal")
        return False

    return True


# Main loop with reconnection logic
while retry_count < MAX_RETRIES and not shutdown_requested:
    try:
        log_debug(f"Attempting to connect to PN532 on {PORT} at {BAUD_RATE} baud...")

        # Initialize serial connection
        uart = serial.Serial(PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT_S)

        # CRITICAL: Set DTR/RTS LOW for USB-to-UART converters
        # This is required for FT232, CP2102, and similar adapters
        uart.dtr = False
        uart.rts = False
        time.sleep(SIGNAL_STABILIZE_DELAY_S)  # Allow signals to stabilize

        # Initialize PN532 with Adafruit library
        pn532 = PN532_UART(uart, debug=False)

        # Configure PN532 SAM (Secure Access Module)
        pn532.SAM_configuration()

        # Get firmware version
        firmware = pn532.firmware_version
        firmware_str = f"{firmware[1]}.{firmware[2]}"

        # Emit ready event
        emit_event('ready', firmware=firmware_str, port=PORT)
        log_debug(f"PN532 ready - Firmware v{firmware_str}")

        # Reset retry count on successful connection
        retry_count = 0

        # Main scanning loop
        while not shutdown_requested:
            # Check for heartbeat
            send_heartbeat_if_needed()

            # Scan for ISO14443A devices (phones, payment cards, tags)
            uid = pn532.read_passive_target(timeout=NFC_SCAN_TIMEOUT_S)

            if uid:
                # Convert UID bytes to hex string (Python 3.5+ built-in)
                uid_hex = uid.hex().upper()

                # Check for duplicate (debouncing)
                if is_duplicate_tap(uid_hex):
                    log_debug(f"Debounced re-tap: {uid_hex}")
                    continue

                # Record and emit tap event
                record_tap(uid_hex)
                emit_event('tap', uid=uid_hex)
                log_debug(f"Tap detected: {uid_hex}")

    except (serial.SerialException, RuntimeError, OSError) as e:
        # Common handler for Serial and PN532 communication errors
        error_type = "Serial" if isinstance(e, serial.SerialException) else "PN532"
        if not handle_retry(error_type, str(e)):
            break

    except Exception as e:
        # Unexpected error (truly fatal)
        log_debug(f"Unexpected fatal error: {e}")
        emit_event('error', message=str(e), fatal=True)
        fatal_exit = True
        break

# Final cleanup
cleanup_resources()

# Exit with appropriate code
exit_code = 1 if (fatal_exit or retry_count >= MAX_RETRIES) else 0
log_debug(f"Exiting with code {exit_code}")
sys.exit(exit_code)
