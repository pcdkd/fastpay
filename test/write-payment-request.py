#!/usr/bin/env python3
"""
Write a signed EIP-712 payment request to NFC card emulation
Test by reading with any NFC app on your phone
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# Test payment request (you'll generate this from Node.js in production)
payment_request = {
    "version": 1,
    "mode": "direct",
    "request": {
        "merchantAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "merchantName": "Alice's Coffee Shop",
        "tokenAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "amount": "5000000",  # 5.00 USDC (6 decimals)
        "currency": "USD",
        "fiatAmount": "5.00",
        "description": "Grande Latte",
        "nonce": str(int(time.time() * 1000)),
        "expiry": str(int((time.time() + 180) * 1000)),  # 3 minutes
        "terminalId": "terminal_001"
    },
    "signature": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234"  # Mock signature for testing
}

def create_ndef_text_message(text):
    """
    Create NDEF Text Record
    Format: [MB ME SR TNF] [Type Length] [Payload Length] [Type] [Payload]
    """
    payload = text.encode('utf-8')

    # NDEF record header
    ndef_record = bytearray()
    ndef_record.append(0xD1)  # MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x01 (Well Known)
    ndef_record.append(0x01)  # Type length = 1
    ndef_record.append(len(payload))  # Payload length (short record)
    ndef_record.append(0x54)  # Type = "T" (Text)
    ndef_record.extend(payload)

    return bytes(ndef_record)

def create_ndef_uri_message(uri):
    """
    Create NDEF URI Record
    More universal - works with most NFC reader apps
    """
    # URI identifier codes (0x00 = no prefix)
    uri_payload = bytearray([0x00])  # No prefix
    uri_payload.extend(uri.encode('utf-8'))

    ndef_record = bytearray()
    ndef_record.append(0xD1)  # Header
    ndef_record.append(0x01)  # Type length
    ndef_record.append(len(uri_payload))  # Payload length
    ndef_record.append(0x55)  # Type = "U" (URI)
    ndef_record.extend(uri_payload)

    return bytes(ndef_record)

print("🔧 Writing Payment Request to NFC")
print("="*60)
print("This will write a signed payment request that your phone can read\n")

try:
    # Open serial port
    print("Opening serial port...")
    uart = serial.Serial(PORT, baudrate=BAUDRATE, timeout=1)
    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)

    # Initialize PN532
    print("Initializing PN532...")
    pn532 = PN532_UART(uart, debug=False)

    # Get firmware version
    ic, ver, rev, support = pn532.firmware_version
    print(f"✅ PN532 Firmware v{ver}.{rev}\n")

    # Configure SAM
    pn532.SAM_configuration()
    print("✅ SAM configured\n")

    # Create NDEF message with payment request
    payment_json = json.dumps(payment_request, indent=2)
    print("Payment Request:")
    print("-" * 60)
    print(payment_json)
    print("-" * 60)

    # Create compact version for NFC (remove whitespace)
    compact_json = json.dumps(payment_request, separators=(',', ':'))

    # Check size
    if len(compact_json) > 245:  # PN532 NDEF limit ~245 bytes in basic mode
        print(f"\n⚠️  Payload too large: {len(compact_json)} bytes")
        print("   Using shortened version...")
        # Use URI format with just essential data
        short_payload = f"fastpay://pay?amount=5.00&merchant=Alice"
        ndef_message = create_ndef_uri_message(short_payload)
        print(f"   Shortened to: {len(ndef_message)} bytes")
    else:
        print(f"\n✅ Payload size: {len(compact_json)} bytes (fits!)")
        ndef_message = create_ndef_text_message(compact_json)

    print(f"   NDEF message: {len(ndef_message)} bytes")
    print(f"   Hex: {ndef_message.hex()[:60]}...\n")

    # Initialize as target (card emulation mode)
    print("🎯 Initializing card emulation mode...")
    print("=" * 60)
    print("📱 TAP YOUR PHONE ON THE NFC MODULE NOW!")
    print("=" * 60)
    print("\nWaiting for phone tap...")
    print("(Use any NFC reader app - NFC Tools, NFC TagInfo, etc.)")
    print("(Press Ctrl+C to stop)\n")

    # Card emulation parameters
    # Mode bits: PICC only (0x04), Passive only (0x01) = 0x05
    mode = 0x05

    # MIFARE params (Type 4 Tag)
    mifare_params = bytearray([
        0x04, 0x00,  # SENS_RES
        0x12, 0x34, 0x56,  # NFCID1t (will be replaced)
        0x40  # SEL_RES (ISO14443-4 compliant)
    ])

    # General bytes (empty for now)
    general_bytes = bytearray([])

    # Historical bytes (optional)
    historical_bytes = bytearray([])

    # Prepare full data with NDEF
    # Note: This is simplified - full implementation needs proper Type 4 Tag formatting
    target_data = bytearray()
    target_data.extend(mifare_params)
    target_data.extend([len(general_bytes)])
    target_data.extend(general_bytes)
    target_data.extend([len(historical_bytes)])
    target_data.extend(historical_bytes)

    timeout_counter = 0
    max_timeout = 60  # 60 seconds

    while timeout_counter < max_timeout:
        try:
            # Call TgInitAsTarget
            # This blocks until a phone initiates communication or timeout
            response = pn532.TgInitAsTarget(
                mode=mode,
                mifare_params=bytes(mifare_params),
                felica_params=b'\x01\xFE\xA2\xA3\xA4\xA5\xA6\xA7\xC0\xC1\xC2\xC3\xC4\xC5\xC6\xC7\xFF\xFF',
                nfcid3t=b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A',
                timeout=1
            )

            if response:
                print("\n🎉 Phone detected!")
                print(f"   Initiator mode: 0x{response[0]:02X}")
                print(f"   Response: {response.hex()}\n")

                # Try to send NDEF data
                print("📤 Sending NDEF message to phone...")

                # In a real implementation, you'd handle NDEF Select/Read commands
                # For now, this demonstrates the connection works
                # Full Type 4 Tag implementation requires handling APDU commands

                try:
                    # Wait for commands from phone
                    received = pn532.TgGetData(timeout=2)
                    if received:
                        print(f"📥 Received from phone: {received.hex()}")

                        # Send response (simplified - real implementation needs APDU handling)
                        pn532.TgSetData(ndef_message[:20])  # Send first 20 bytes as test
                        print("✅ Sent NDEF preview to phone")

                except RuntimeError as e:
                    print(f"   Phone disconnected: {e}")

                print("\n✅ Connection established!")
                print("   (Full NDEF transfer requires Type 4 Tag APDU implementation)")
                print("\n💡 Next steps:")
                print("   1. Implement full Type 4 Tag protocol")
                print("   2. Or use simpler Type 2 Tag format")
                print("   3. Or write to physical NFC tag first")

                break

        except RuntimeError as e:
            if "timeout" in str(e).lower():
                timeout_counter += 1
                if timeout_counter % 10 == 0:
                    print(f"   Still waiting... ({timeout_counter}s)")
            else:
                print(f"   Error: {e}")
                break

    if timeout_counter >= max_timeout:
        print("\n⏱️  Timeout - no phone detected")
        print("\n💡 Troubleshooting:")
        print("   - Make sure phone NFC is enabled")
        print("   - Hold phone within 1-2cm of module")
        print("   - Try a different NFC reader app")
        print("   - Some phones need the screen to be on")

    uart.close()
    print("\n✅ Test complete")

except KeyboardInterrupt:
    print("\n\n⚠️  Stopped by user")
    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    if 'uart' in locals():
        uart.close()
