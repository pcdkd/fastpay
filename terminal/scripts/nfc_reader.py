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

# Reconnection settings
MAX_RETRIES = 5


class NFCReader:
    """
    NFC Reader class that manages PN532 hardware and tap detection.
    Encapsulates state and provides clean separation of concerns.
    """

    def __init__(self):
        """Initialize NFC reader with configuration from environment"""
        # Load and validate configuration
        self.config = self._load_config()

        # State management
        self.shutdown_requested = False
        self.fatal_exit = False
        self.retry_count = 0

        # Resource handles
        self.uart = None
        self.pn532 = None

        # UID deduplication buffer
        self.recent_taps = deque(maxlen=self.config['dedup_buffer_size'])

        # Heartbeat tracking (use monotonic time for intervals)
        self.last_heartbeat = time.monotonic()

    def _load_config(self):
        """Load and validate configuration from environment variables"""
        try:
            port = os.getenv('NFC_PORT')
            if not port:
                raise ValueError("NFC_PORT environment variable not set")

            return {
                'port': port,
                'baud_rate': int(os.getenv('NFC_BAUD_RATE', '115200')),
                'debounce_ms': int(os.getenv('NFC_TAP_DEBOUNCE_MS', '1000')),
                'dedup_buffer_size': int(os.getenv('NFC_DEDUP_BUFFER_SIZE', '10'))
            }
        except ValueError as e:
            self._emit_event('error',
                           message=f"Configuration error: {e}",
                           fatal=True)
            sys.exit(1)

    def _emit_event(self, event_type, **data):
        """Output JSON event to stdout (Node.js reads this)"""
        event = {
            "event": event_type,
            "timestamp": int(time.time()),  # Wall clock time for timestamps
            **data
        }
        print(json.dumps(event), flush=True)

    def _log_debug(self, message):
        """Output debug info to stderr (doesn't interfere with IPC)"""
        print(f"[NFC] {message}", file=sys.stderr, flush=True)

    def _cleanup_resources(self):
        """Close serial port and release resources"""
        try:
            if self.uart and self.uart.is_open:
                self.uart.close()
                self._log_debug("Serial port closed")
        except Exception as e:
            self._log_debug(f"Error closing serial port: {e}")
        finally:
            self.uart = None
            self.pn532 = None

    def _handle_shutdown(self, signum, frame):
        """
        Handle SIGINT and SIGTERM gracefully.
        Idempotent - ignores duplicate signals.
        """
        if self.shutdown_requested:
            return  # Already shutting down
        self.shutdown_requested = True
        self._emit_event('shutdown', reason=f'Signal {signum} received')
        self._log_debug(f'Shutdown signal {signum} received')
        # Don't call sys.exit() here - let main loop cleanup and exit

    def _is_duplicate_tap(self, uid_hex):
        """Check if this UID was tapped recently (within debounce window)"""
        now = time.monotonic()  # Use monotonic time for interval measurement
        for tap in self.recent_taps:
            if tap['uid'] == uid_hex and (now - tap['time']) < self.config['debounce_ms'] / 1000:
                return True
        return False

    def _record_tap(self, uid_hex):
        """Record this tap in deduplication buffer"""
        self.recent_taps.append({
            'uid': uid_hex,
            'time': time.monotonic()  # Use monotonic time for interval measurement
        })

    def _send_heartbeat_if_needed(self):
        """Send heartbeat event every 30 seconds to prove process is alive"""
        now = time.monotonic()  # Use monotonic time for interval measurement
        if now - self.last_heartbeat >= HEARTBEAT_INTERVAL_S:
            self._emit_event('heartbeat')
            self.last_heartbeat = now

    def _interruptible_sleep(self, total_seconds):
        """
        Sleep in short intervals, allowing heartbeat emission and shutdown checks.
        Returns True if sleep completed, False if interrupted by shutdown.
        """
        end_time = time.monotonic() + total_seconds
        while time.monotonic() < end_time and not self.shutdown_requested:
            # Sleep in short bursts
            remaining = end_time - time.monotonic()
            time.sleep(min(BACKOFF_CHECK_INTERVAL_S, remaining))
            # Send heartbeat during long waits
            self._send_heartbeat_if_needed()
        return not self.shutdown_requested

    def _handle_retry(self, error_type, error_message):
        """
        Common retry/backoff handler for all recoverable errors.
        Returns True if should retry, False if max retries reached.
        """
        self._log_debug(f"{error_type} error: {error_message}")
        self._emit_event('error', message=f"{error_type} error: {error_message}", fatal=False)
        self._cleanup_resources()

        self.retry_count += 1
        if self.retry_count >= MAX_RETRIES:
            self._emit_event('error', message="Max retries reached", fatal=True)
            self._log_debug("Max retries reached, exiting")
            return False

        # Exponential backoff with interruptible sleep
        wait_time = 2 ** self.retry_count
        self._log_debug(f"Retrying in {wait_time} seconds... (attempt {self.retry_count}/{MAX_RETRIES})")

        # Use interruptible sleep to allow heartbeats and shutdown
        if not self._interruptible_sleep(wait_time):
            self._log_debug("Retry interrupted by shutdown signal")
            return False

        return True

    def _initialize_hardware(self):
        """
        Initialize PN532 hardware and return firmware version.
        Raises exceptions on failure for retry handling.
        """
        self._log_debug(f"Attempting to connect to PN532 on {self.config['port']} at {self.config['baud_rate']} baud...")

        # Initialize serial connection
        self.uart = serial.Serial(self.config['port'], self.config['baud_rate'], timeout=SERIAL_TIMEOUT_S)

        # CRITICAL: Set DTR/RTS LOW for USB-to-UART converters
        # This is required for FT232, CP2102, and similar adapters
        self.uart.dtr = False
        self.uart.rts = False
        time.sleep(SIGNAL_STABILIZE_DELAY_S)  # Allow signals to stabilize

        # Initialize PN532 with Adafruit library
        self.pn532 = PN532_UART(self.uart, debug=False)

        # Configure PN532 SAM (Secure Access Module)
        self.pn532.SAM_configuration()

        # Get firmware version using tuple unpacking
        ic, ver, rev, support = self.pn532.firmware_version
        firmware_str = f"{ver}.{rev}"

        return firmware_str

    def _scan_loop(self):
        """Main NFC scanning loop - runs until shutdown or error"""
        while not self.shutdown_requested:
            # Check for heartbeat
            self._send_heartbeat_if_needed()

            # Scan for ISO14443A devices (phones, payment cards, tags)
            uid = self.pn532.read_passive_target(timeout=NFC_SCAN_TIMEOUT_S)

            if uid:
                # Convert UID bytes to hex string (Python 3.5+ built-in)
                uid_hex = uid.hex().upper()

                # Check for duplicate (debouncing)
                if self._is_duplicate_tap(uid_hex):
                    self._log_debug(f"Debounced re-tap: {uid_hex}")
                    continue

                # Record and emit tap event
                self._record_tap(uid_hex)
                self._emit_event('tap', uid=uid_hex)
                self._log_debug(f"Tap detected: {uid_hex}")

    def run(self):
        """
        Main application loop with reconnection logic.
        Handles initialization, scanning, and graceful shutdown.
        """
        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Main connection/retry loop
        while self.retry_count < MAX_RETRIES and not self.shutdown_requested:
            try:
                # Initialize hardware
                firmware_str = self._initialize_hardware()

                # Emit ready event
                self._emit_event('ready', firmware=firmware_str, port=self.config['port'])
                self._log_debug(f"PN532 ready - Firmware v{firmware_str}")

                # Reset retry count on successful connection
                self.retry_count = 0

                # Start scanning loop
                self._scan_loop()

            except (serial.SerialException, RuntimeError, OSError) as e:
                # Common handler for Serial and PN532 communication errors
                error_type = "Serial" if isinstance(e, serial.SerialException) else "PN532"
                if not self._handle_retry(error_type, str(e)):
                    break

            except Exception as e:
                # Unexpected error (truly fatal)
                self._log_debug(f"Unexpected fatal error: {e}")
                self._emit_event('error', message=str(e), fatal=True)
                self.fatal_exit = True
                break

        # Final cleanup
        self._cleanup_resources()

        # Exit with appropriate code
        exit_code = 1 if (self.fatal_exit or self.retry_count >= MAX_RETRIES) else 0
        self._log_debug(f"Exiting with code {exit_code}")
        sys.exit(exit_code)


def main():
    """Entry point - creates and runs NFCReader instance"""
    reader = NFCReader()
    reader.run()


if __name__ == "__main__":
    main()
