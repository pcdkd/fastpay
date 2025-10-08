#!/usr/bin/env python3
"""
PN532 Card Emulation using RAW commands
Implements TgInitAsTarget manually since Adafruit library doesn't have it
"""
import serial
import json
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

payment = {
    "v": 1,
    "merchant": "Alice's Coffee",
    "amount": "5.00 USDC",
    "item": "Latte",
    "addr": "0x742d...bEb",
    "time": int(time.time())
}

def send_command(ser, command_code, params=None):
    """Send PN532 command and return response"""
    if params is None:
        params = []

    # Build frame
    frame = bytearray([
        0x00, 0x00, 0xFF,  # Preamble
    ])

    # Length
    length = len(params) + 2  # TFI + command
    frame.append(length)
    frame.append((~length + 1) & 0xFF)  # Length checksum

    frame.append(0xD4)  # TFI (host to PN532)
    frame.append(command_code)
    frame.extend(params)

    # Data checksum
    dcs = (~(0xD4 + command_code + sum(params)) + 1) & 0xFF
    frame.append(dcs)
    frame.append(0x00)  # Postamble

    # Send
    ser.reset_input_buffer()
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

    # Read data
    data = ser.read(length + 1)  # +1 for DCS
    if len(data) != length + 1:
        return None

    # Return payload (skip TFI and DCS)
    return data[1:-1]

def tg_init_as_target(ser, ndef_data):
    """
    Initialize PN532 as target (card emulation)
    Command: 0x8C
    """
    params = bytearray()

    # Mode: PICC only (0x04) + Passive (0x01) = 0x05
    params.append(0x05)

    # SENS_RES (2 bytes) - Mifare/ISO14443-4
    params.extend([0x04, 0x00])

    # NFCID1t (3 bytes) - will be generated
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

    # General bytes length (0 for now)
    params.append(0x00)

    # Historical bytes length (0 for now)
    params.append(0x00)

    return send_command(ser, 0x8C, params)

def tg_get_data(ser):
    """Get data from initiator (phone)"""
    return send_command(ser, 0x86, [])

def tg_set_data(ser, data):
    """Send data to initiator (phone)"""
    return send_command(ser, 0x8E, list(data))

def create_ndef_text(text):
    """Create NDEF Text Record"""
    text_bytes = text.encode('utf-8')

    record = bytearray()
    record.append(0xD1)  # Header
    record.append(0x01)  # Type length
    record.append(len(text_bytes) + 3)  # Payload length
    record.append(0x54)  # Type: T
    record.append(0x02)  # Language length
    record.extend(b'en')
    record.extend(text_bytes)

    return bytes(record)

print("🔧 PN532 Card Emulation (Raw Commands)")
print("="*60)

try:
    # Setup serial
    ser = serial.Serial(PORT, BAUDRATE, timeout=1,
                       rtscts=False, dsrdtr=False, xonxoff=False)
    ser.dtr = False
    ser.rts = False
    time.sleep(0.2)

    print("✅ Serial port opened\n")

    # Get firmware (using raw command)
    print("Testing PN532 connection...")
    response = send_command(ser, 0x02, [])  # GetFirmwareVersion
    if response and len(response) >= 4:
        print(f"✅ PN532 v{response[1]}.{response[2]}\n")
    else:
        print("❌ PN532 not responding")
        ser.close()
        exit(1)

    # SAM configuration
    send_command(ser, 0x14, [0x01, 0x14, 0x01])
    print("✅ SAM configured\n")

    # Prepare payment
    payment_json = json.dumps(payment, separators=(',', ':'))
    print("Payment Request:")
    print("-" * 60)
    print(json.dumps(payment, indent=2))
    print("-" * 60)
    print(f"Size: {len(payment_json)} bytes\n")

    ndef_msg = create_ndef_text(payment_json)
    print(f"NDEF: {len(ndef_msg)} bytes\n")

    print("="*60)
    print("📱 TAP YOUR PHONE NOW!")
    print("="*60)
    print("Module is acting as NFC tag\n")
    print("Waiting for tap...\n")

    tap_count = 0

    while True:
        try:
            # Initialize as target (blocks until phone taps)
            print(f"[{time.strftime('%H:%M:%S')}] Listening...")

            response = tg_init_as_target(ser, ndef_msg)

            if response:
                tap_count += 1
                print(f"\n🎉 PHONE TAP #{tap_count}!")
                print(f"   Mode: 0x{response[0]:02X}")
                print(f"   Baudrate: 0x{response[1]:02X}")
                print(f"   Response: {response.hex()}\n")

                print("📡 In communication with phone...")
                print("   Waiting for commands...\n")

                # Handle ISO-DEP session
                session_active = True
                cmd_count = 0

                while session_active:
                    # Get command from phone
                    cmd = tg_get_data(ser)

                    if cmd and len(cmd) > 0:
                        cmd_count += 1

                        # Skip status byte if present
                        if cmd[0] == 0x00:
                            cmd = cmd[1:]

                        if len(cmd) >= 2:
                            print(f"   📥 Cmd #{cmd_count}: {cmd.hex()}")

                            # Parse APDU
                            cla = cmd[0]
                            ins = cmd[1]

                            resp = None

                            # SELECT (0xA4)
                            if ins == 0xA4:
                                print(f"      → SELECT")
                                resp = bytes([0x90, 0x00])  # OK

                            # READ BINARY (0xB0)
                            elif ins == 0xB0:
                                print(f"      → READ BINARY")
                                # Send chunk of NDEF
                                resp = ndef_msg[:50] + bytes([0x90, 0x00])

                            else:
                                print(f"      → Unknown (0x{ins:02X})")
                                resp = bytes([0x6A, 0x82])  # Not supported

                            # Send response
                            if resp:
                                result = tg_set_data(ser, resp)
                                if result:
                                    print(f"      ← Sent: {resp[:20].hex()}... ({len(resp)} bytes)\n")
                                else:
                                    print(f"      ⚠️  Send failed\n")
                                    session_active = False

                    else:
                        # No command = phone disconnected
                        print("   📱 Phone disconnected\n")
                        session_active = False

                print("="*60)
                print(f"✅ Session #{tap_count} complete")
                print(f"   Commands handled: {cmd_count}")
                print("="*60)
                print("\nWaiting for next tap...\n")

        except KeyboardInterrupt:
            raise

        except Exception as e:
            if "timeout" not in str(e).lower():
                print(f"   ⚠️  {e}")

        time.sleep(0.1)

except KeyboardInterrupt:
    print(f"\n\n📊 Summary: {tap_count} phone taps detected")
    print("✅ Test complete")
    if 'ser' in locals():
        ser.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    if 'ser' in locals():
        ser.close()
