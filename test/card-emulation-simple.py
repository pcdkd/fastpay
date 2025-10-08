#!/usr/bin/env python3
"""
PN532 Card Emulation - Acts as NFC tag that phone can read
This is the FastPay production approach!
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
    "merchant": "Alice's Coffee",
    "amount": "5.00 USDC",
    "item": "Grande Latte",
    "address": "0x742d35Cc...bEb",
    "timestamp": int(time.time())
}

def create_ndef_text_message(text):
    """Create NDEF Text Record"""
    text_bytes = text.encode('utf-8')

    # NDEF Text Record
    record = bytearray()
    record.append(0xD1)  # Header: MB=1, ME=1, SR=1, TNF=Well-known
    record.append(0x01)  # Type length
    record.append(len(text_bytes) + 3)  # Payload length (includes language)
    record.append(0x54)  # Type: 'T' (Text)
    record.append(0x02)  # Language length
    record.extend(b'en')  # Language code
    record.extend(text_bytes)

    return bytes(record)

print("🔧 PN532 Card Emulation - Phone Can Read Payment!")
print("="*60)

try:
    # Setup
    uart = serial.Serial(PORT, baudrate=BAUDRATE, timeout=1)
    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)

    pn532 = PN532_UART(uart, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"✅ PN532 v{ver}.{rev}\n")

    pn532.SAM_configuration()

    # Prepare payment
    payment_json = json.dumps(payment, indent=2)
    compact_json = json.dumps(payment, separators=(',', ':'))

    print("Payment Request:")
    print("-" * 60)
    print(payment_json)
    print("-" * 60)
    print(f"Size: {len(compact_json)} bytes\n")

    # Create NDEF message
    ndef_message = create_ndef_text_message(compact_json)
    print(f"NDEF message: {len(ndef_message)} bytes")
    print(f"Preview: {ndef_message[:40].hex()}...\n")

    print("="*60)
    print("📱 TAP YOUR PHONE ON THE MODULE NOW!")
    print("="*60)
    print("\nThe PN532 is acting as an NFC tag")
    print("Your phone will read the payment request\n")
    print("Waiting for phone tap...")
    print("(Press Ctrl+C to stop)\n")

    tap_count = 0

    while True:
        try:
            # Initialize as target (card emulation)
            # This makes the PN532 act like an NFC tag

            # Mode:
            # 0x04 = PICC only (act as card)
            # 0x01 = Passive only
            mode = 0x05  # 0x04 | 0x01

            # Mifare parameters (Type 4 Tag - like credit cards)
            mifare_params = bytes([
                0x08, 0x00,  # SENS_RES (Type 4 Tag)
                0x12, 0x34, 0x56,  # NFCID1t (will be randomized by PN532)
                0x40  # SEL_RES (ISO14443-4 compliant)
            ])

            # FeliCa parameters (Japanese standard - required but we don't use it)
            felica_params = bytes([
                0x01, 0xFE,
                0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,  # IDm
                0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,  # PMm
                0xFF, 0xFF  # System Code
            ])

            # NFCID3t (for Type F)
            nfcid3t = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A])

            # Wait for phone to initiate (blocks until phone taps or timeout)
            response = pn532.TgInitAsTarget(
                mode=mode,
                mifare_params=mifare_params,
                felica_params=felica_params,
                nfcid3t=nfcid3t,
                timeout=1  # 1 second timeout, then retry
            )

            if response:
                tap_count += 1
                print(f"\n🎉 PHONE DETECTED! (Tap #{tap_count})")
                print(f"   Time: {time.strftime('%H:%M:%S')}")
                print(f"   Mode byte: 0x{response[0]:02X}")
                print(f"   Baudrate: 0x{response[1]:02X}")
                print(f"   Initiator: {response.hex()}\n")

                print("📡 Phone is communicating with module!")
                print("   Waiting for NDEF read commands...\n")

                # Now we're in target mode - phone will send commands
                # We need to respond to ISO-DEP (Type 4 Tag) commands

                session_active = True
                command_count = 0

                while session_active:
                    try:
                        # Receive command from phone
                        received = pn532.TgGetData(timeout=2)

                        if received:
                            command_count += 1
                            print(f"   📥 Command #{command_count}: {received.hex()}")

                            # Parse ISO-DEP / APDU commands
                            # This is simplified - full NDEF requires proper APDU handling

                            # Common commands:
                            # 00 A4 04 00 ... = SELECT application
                            # 00 A4 00 0C ... = SELECT file
                            # 00 B0 ... = READ BINARY

                            if len(received) >= 2:
                                cla = received[0]  # Class byte
                                ins = received[1]  # Instruction byte

                                response_data = None

                                # SELECT command (0xA4)
                                if ins == 0xA4:
                                    print(f"      → SELECT command")
                                    # Response: Success (0x90 0x00)
                                    response_data = bytes([0x90, 0x00])

                                # READ BINARY command (0xB0)
                                elif ins == 0xB0:
                                    print(f"      → READ BINARY command")
                                    # Send NDEF message (simplified)
                                    # In real implementation, need to handle offsets/lengths
                                    response_data = ndef_message[:20] + bytes([0x90, 0x00])

                                # Unknown command
                                else:
                                    print(f"      → Unknown (CLA=0x{cla:02X}, INS=0x{ins:02X})")
                                    # Response: Not supported
                                    response_data = bytes([0x6A, 0x82])

                                # Send response
                                if response_data:
                                    pn532.TgSetData(response_data)
                                    print(f"      ← Response: {response_data.hex()}\n")

                        else:
                            # No command received - phone disconnected
                            print("   📱 Phone disconnected\n")
                            session_active = False

                    except RuntimeError as e:
                        if "timeout" not in str(e).lower():
                            print(f"   Session ended: {e}\n")
                        session_active = False

                print("="*60)
                print(f"✅ Session complete! (Tap #{tap_count})")
                print("="*60)
                print(f"\n💡 Status:")
                print(f"   - Phone detected module: YES")
                print(f"   - ISO-DEP commands: {command_count}")
                print(f"   - NDEF data sent: Partial\n")

                print("ℹ️  Note: Full Type 4 Tag APDU implementation needed")
                print("   for complete NDEF transfer. This proves the")
                print("   connection works! Next: Implement full protocol.\n")

                print("Waiting for next tap...\n")

        except RuntimeError as e:
            # Timeout waiting for phone - this is normal
            if "timeout" not in str(e).lower():
                print(f"⚠️  Error: {e}")

        except KeyboardInterrupt:
            raise

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n📊 Session Summary:")
    print(f"   Total phone taps: {tap_count}")
    print("\n✅ Test complete")

    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

    if 'uart' in locals():
        uart.close()
