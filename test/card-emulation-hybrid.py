#!/usr/bin/env python3
"""
FastPay Card Emulation - HYBRID APPROACH
Uses Adafruit library for initialization + raw commands for card emulation

This is the production approach:
- Adafruit handles: DTR/RTS, wake-up, SAM config (proven reliable)
- Raw commands handle: TgInitAsTarget, TgGetData, TgSetData (not in Adafruit)
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# Payment request to send
payment = {
    "v": 1,
    "m": "direct",
    "req": {
        "addr": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "name": "Alice's Coffee",
        "token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "amt": "5000000",
        "cur": "USD",
        "fiat": "5.00",
        "desc": "Grande Latte",
        "nonce": str(int(time.time() * 1000)),
        "exp": str(int((time.time() + 180) * 1000)),
        "tid": "term_001"
    },
    "sig": "mockSignatureBase64=="
}

# ============================================================================
# RAW PN532 COMMANDS (for card emulation - not in Adafruit library)
# ============================================================================

def send_command(ser, command_code, params=None):
    """Send raw PN532 command via serial port"""
    if params is None:
        params = []

    # Build PN532 UART frame
    frame = bytearray([0x00, 0x00, 0xFF])  # Preamble

    length = len(params) + 2  # TFI + CMD
    frame.append(length)
    frame.append((~length + 1) & 0xFF)  # Length checksum

    frame.append(0xD4)  # TFI (host to PN532)
    frame.append(command_code)
    frame.extend(params)

    # Data checksum
    dcs = (~(0xD4 + command_code + sum(params)) + 1) & 0xFF
    frame.append(dcs)
    frame.append(0x00)  # Postamble

    # Send via serial port
    ser.write(frame)
    ser.flush()

    return read_response(ser)

def read_response(ser, timeout=2.0):
    """Read PN532 response frame"""
    deadline = time.time() + timeout

    # Wait for preamble
    while time.time() < deadline:
        byte = ser.read(1)
        if byte == b'\x00':
            if ser.read(2) == b'\x00\xFF':
                break
    else:
        return None

    # Read length
    length = ser.read(1)
    if not length:
        return None
    length = length[0]

    lcs = ser.read(1)
    if not lcs:
        return None

    # Verify length checksum
    if ((length + lcs[0]) & 0xFF) != 0:
        return None

    # Read data + DCS
    data = ser.read(length + 1)
    if len(data) != length + 1:
        return None

    # Return payload (skip TFI and DCS)
    return data[1:-1]

def tg_init_as_target(ser):
    """
    Initialize PN532 as NFC target (card emulation)
    Command: 0x8C (TgInitAsTarget)

    This makes the PN532 act like an NFC tag that phones can read.
    """
    params = bytearray()

    # Mode: PICC only (0x04) + Passive (0x01) = 0x05
    params.append(0x05)

    # SENS_RES (2 bytes) - ISO14443-4 Type 4 Tag
    params.extend([0x04, 0x00])

    # NFCID1t (3 bytes) - UID (will be auto-generated)
    params.extend([0x12, 0x34, 0x56])

    # SEL_RES (1 byte) - ISO14443-4 compliant
    params.append(0x40)

    # FeliCa params (18 bytes) - required but not used
    params.extend([
        0x01, 0xFE, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
        0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
        0xFF, 0xFF
    ])

    # NFCID3t (10 bytes)
    params.extend([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A])

    # General bytes length
    params.append(0x00)

    # Historical bytes length
    params.append(0x00)

    return send_command(ser, 0x8C, params)

def tg_get_data(ser):
    """
    Get data from initiator (phone)
    Command: 0x86 (TgGetData)

    Receives APDU commands from the phone.
    """
    return send_command(ser, 0x86, [])

def tg_set_data(ser, data):
    """
    Send data to initiator (phone)
    Command: 0x8E (TgSetData)

    Sends APDU responses back to the phone.
    """
    return send_command(ser, 0x8E, list(data))

# ============================================================================
# NDEF MESSAGE CREATION
# ============================================================================

def create_ndef_text(text):
    """
    Create NDEF Text Record
    Format: Header + Type Length + Payload Length + Type + Language + Text
    """
    text_bytes = text.encode('utf-8')

    record = bytearray()
    record.append(0xD1)  # Header: MB=1, ME=1, SR=1, TNF=Well-known
    record.append(0x01)  # Type length
    record.append(len(text_bytes) + 3)  # Payload length (includes language)
    record.append(0x54)  # Type: 'T' (Text)
    record.append(0x02)  # Language code length
    record.extend(b'en')  # Language code
    record.extend(text_bytes)

    return bytes(record)

# ============================================================================
# MAIN CARD EMULATION LOOP
# ============================================================================

print("🔧 FastPay Card Emulation - HYBRID APPROACH")
print("=" * 60)
print("Using: Adafruit (init) + Raw commands (card emulation)")
print("=" * 60)
print()

try:
    # ========================================================================
    # STEP 1: ADAFRUIT INITIALIZATION (proven reliable)
    # ========================================================================

    print("Step 1: Initializing with Adafruit library...")

    # Open serial with proper settings
    uart = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=1,
        rtscts=False,      # No hardware flow control
        dsrdtr=False,      # No hardware flow control
        xonxoff=False      # No software flow control
    )

    # CRITICAL: Force DTR/RTS LOW (Adafruit library handles this correctly)
    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)  # Allow signals to stabilize

    print("   ✅ Serial port opened")
    print(f"   Port: {PORT}")
    print(f"   DTR: {uart.dtr}, RTS: {uart.rts}")
    print()

    # Initialize PN532 with Adafruit library
    pn532 = PN532_UART(uart, debug=False)

    # Get firmware version
    ic, ver, rev, support = pn532.firmware_version
    print(f"   ✅ PN532 detected: v{ver}.{rev}")
    print()

    # Configure SAM (Security Access Module)
    pn532.SAM_configuration()
    print("   ✅ SAM configured")
    print()

    # ========================================================================
    # STEP 2: PREPARE PAYMENT REQUEST
    # ========================================================================

    print("Step 2: Preparing payment request...")

    payment_json = json.dumps(payment, separators=(',', ':'))
    print(f"   Payment: {payment_json[:60]}...")
    print(f"   Size: {len(payment_json)} bytes")
    print()

    # Create NDEF message
    ndef_message = create_ndef_text(payment_json)
    print(f"   NDEF size: {len(ndef_message)} bytes")
    print(f"   Preview: {ndef_message[:40].hex()}...")
    print()

    # ========================================================================
    # STEP 3: CARD EMULATION (raw PN532 commands)
    # ========================================================================

    print("=" * 60)
    print("📱 TAP YOUR PHONE NOW!")
    print("=" * 60)
    print("Module is acting as NFC tag")
    print("(Press Ctrl+C to stop)")
    print()

    tap_count = 0

    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Listening for tap...")

            # Initialize as target (blocks until phone taps)
            # NOTE: Using raw command because Adafruit doesn't have this
            response = tg_init_as_target(uart)

            if response:
                tap_count += 1
                print(f"\n🎉 PHONE TAP #{tap_count}!")
                print(f"   Mode: 0x{response[0]:02X}")
                print(f"   Baudrate: 0x{response[1]:02X}")
                print(f"   Initiator: {response.hex()}")
                print()

                print("📡 Phone is communicating with module...")
                print("   Handling APDU commands...")
                print()

                # Handle ISO-DEP session
                session_active = True
                apdu_count = 0

                while session_active:
                    # Get APDU command from phone
                    cmd = tg_get_data(uart)

                    if cmd and len(cmd) > 0:
                        apdu_count += 1

                        # Skip status byte if present
                        if cmd[0] == 0x00:
                            cmd = cmd[1:]

                        if len(cmd) >= 2:
                            print(f"   📥 APDU #{apdu_count}: {cmd.hex()}")

                            # Parse APDU
                            cla = cmd[0]
                            ins = cmd[1]

                            resp = None

                            # SELECT command (0xA4)
                            if ins == 0xA4:
                                print(f"      → SELECT")
                                resp = bytes([0x90, 0x00])  # OK

                            # READ BINARY command (0xB0)
                            elif ins == 0xB0:
                                print(f"      → READ BINARY")
                                # Send NDEF message (simplified - first 50 bytes)
                                resp = ndef_message[:50] + bytes([0x90, 0x00])

                            else:
                                print(f"      → Unknown (CLA=0x{cla:02X}, INS=0x{ins:02X})")
                                resp = bytes([0x6A, 0x82])  # Not supported

                            # Send response
                            if resp:
                                result = tg_set_data(uart, resp)
                                if result:
                                    print(f"      ← Response: {resp[:20].hex()}... ({len(resp)} bytes)")
                                    print()
                                else:
                                    print(f"      ⚠️  Send failed")
                                    print()
                                    session_active = False

                    else:
                        # No command = phone disconnected
                        print("   📱 Phone disconnected")
                        print()
                        session_active = False

                print("=" * 60)
                print(f"✅ Session #{tap_count} complete")
                print(f"   APDUs handled: {apdu_count}")
                print("=" * 60)
                print()
                print("Waiting for next tap...")
                print()

        except KeyboardInterrupt:
            raise

        except Exception as e:
            if "timeout" not in str(e).lower():
                print(f"   ⚠️  Error: {e}")

        time.sleep(0.1)

except KeyboardInterrupt:
    print(f"\n\n📊 Summary: {tap_count} phone taps detected")
    print("✅ Test complete")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    if 'uart' in locals():
        uart.close()
        print("Serial port closed")
