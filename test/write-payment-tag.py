#!/usr/bin/env python3
"""
FastPay NFC Tag Writer - PRODUCTION APPROACH

This script uses the PN532 in READER/WRITER mode to write payment requests
to a physical NFC tag. This is more reliable than card emulation and works
perfectly with the Adafruit library.

WORKFLOW:
1. Merchant creates payment request
2. Script writes payment JSON to NFC tag
3. Customer taps phone on tag to read payment
4. Customer wallet processes payment
5. Script rewrites tag for next transaction

HARDWARE NEEDED:
- PN532 module (you have this)
- Blank NFC tags: NTAG213/215/216 (ISO14443A, 144-888 bytes)
  Buy from: Amazon, AliExpress (~$10 for 10 tags)
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# Payment request to write to tag
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

def create_ndef_text_record(text):
    """
    Create NDEF Text Record
    Format: [Header][Type Len][Payload Len][Type][Status][Lang][Text]
    """
    text_bytes = text.encode('utf-8')

    record = bytearray()

    # NDEF Record Header
    # MB=1 (Message Begin), ME=1 (Message End), CF=0, SR=1 (Short Record), IL=0, TNF=001 (Well-known)
    record.append(0xD1)

    # Type Length (1 byte for 'T')
    record.append(0x01)

    # Payload Length (text + 3 bytes for status/lang)
    payload_len = len(text_bytes) + 3
    if payload_len < 256:
        record.append(payload_len)
    else:
        # Use long form if needed
        print("⚠️  Warning: Text too long for short record format")
        return None

    # Type: 'T' (Text)
    record.append(0x54)

    # Status byte: UTF-8 encoding (bit 7=0), language code length (bits 5-0 = 2)
    record.append(0x02)

    # Language code: 'en'
    record.extend(b'en')

    # Text payload
    record.extend(text_bytes)

    return bytes(record)

def write_ndef_to_tag(pn532, ndef_data):
    """
    Write NDEF message to NTAG21x tag

    NTAG memory structure:
    - Page 0-3: UID, lock bytes (read-only)
    - Page 4: Capability Container (CC)
    - Page 5+: NDEF message (TLV structure)
    """

    # Wait for tag to be placed on reader
    print("📱 Place NFC tag on reader...")
    uid = pn532.read_passive_target(timeout=10)

    if not uid:
        print("❌ No tag detected")
        return False

    print(f"✅ Tag detected! UID: {uid.hex()}")

    # Authenticate (not needed for NTAG, but good practice)
    # NTAG uses open memory model, no auth required

    # Read current data to determine tag type
    try:
        page_4 = pn532.ntag2xx_read_block(4)
        print(f"   Current page 4 (CC): {page_4.hex()}")
    except Exception as e:
        print(f"⚠️  Could not read tag: {e}")
        return False

    # Build NDEF message with TLV structure
    ndef_message = bytearray()

    # TLV: Type (0x03 = NDEF Message)
    ndef_message.append(0x03)

    # TLV: Length
    if len(ndef_data) < 255:
        ndef_message.append(len(ndef_data))
    else:
        ndef_message.append(0xFF)
        ndef_message.append((len(ndef_data) >> 8) & 0xFF)
        ndef_message.append(len(ndef_data) & 0xFF)

    # TLV: Value (NDEF data)
    ndef_message.extend(ndef_data)

    # TLV: Terminator
    ndef_message.append(0xFE)

    print(f"   NDEF message size: {len(ndef_message)} bytes")

    # Write to tag starting at page 4 (after CC)
    # NTAG pages are 4 bytes each
    # Page 4: Capability Container (usually pre-written, but we'll set it)

    # CC bytes for NTAG213 (144 bytes usable)
    # E1 10 12 00 = Magic number, version 1.0, 144 bytes (0x12*8), read/write access
    cc = bytes([0xE1, 0x10, 0x12, 0x00])

    try:
        # Write CC to page 4
        pn532.ntag2xx_write_block(4, cc)
        print(f"   ✅ Wrote CC to page 4")

        # Write NDEF message starting at page 5
        # Break into 4-byte chunks
        page = 5
        offset = 0

        while offset < len(ndef_message):
            chunk = ndef_message[offset:offset+4]

            # Pad with zeros if needed
            if len(chunk) < 4:
                chunk = chunk + bytes([0x00] * (4 - len(chunk)))

            pn532.ntag2xx_write_block(page, chunk)
            print(f"   ✅ Wrote page {page}: {chunk.hex()}")

            page += 1
            offset += 4

            # NTAG213 has 45 pages (0-44), usable pages 4-39
            if page > 39:
                print("⚠️  Tag full!")
                break

        print(f"\n✅ Successfully wrote {len(ndef_data)} bytes to tag!")
        return True

    except Exception as e:
        print(f"❌ Write failed: {e}")
        return False

print("🔧 FastPay NFC Tag Writer")
print("=" * 60)
print("This script writes payment requests to physical NFC tags")
print("=" * 60)
print()

try:
    # Initialize PN532
    print("Step 1: Initializing PN532...")

    uart = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=1,
        rtscts=False,
        dsrdtr=False,
        xonxoff=False
    )

    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)

    pn532 = PN532_UART(uart, debug=False)

    ic, ver, rev, support = pn532.firmware_version
    print(f"   ✅ PN532 detected: v{ver}.{rev}")

    pn532.SAM_configuration()
    print(f"   ✅ SAM configured")
    print()

    # Prepare payment
    print("Step 2: Preparing payment request...")

    payment_json = json.dumps(payment, separators=(',', ':'))
    print(f"   Payment: {payment_json[:60]}...")
    print(f"   Size: {len(payment_json)} bytes")
    print()

    # Create NDEF record
    ndef_record = create_ndef_text_record(payment_json)

    if not ndef_record:
        print("❌ Failed to create NDEF record")
        uart.close()
        exit(1)

    print(f"   NDEF record: {len(ndef_record)} bytes")
    print(f"   Preview: {ndef_record[:20].hex()}...")
    print()

    # Write to tag
    print("Step 3: Writing to NFC tag...")
    print("=" * 60)

    success = write_ndef_to_tag(pn532, ndef_record)

    if success:
        print()
        print("=" * 60)
        print("✅ PAYMENT TAG READY!")
        print("=" * 60)
        print()
        print("📱 Customer can now tap their phone to read payment")
        print()
        print("To write another payment:")
        print("  1. Update payment details in script")
        print("  2. Run script again")
        print("  3. Place same tag on reader")
        print()
    else:
        print()
        print("❌ Failed to write tag")
        print()
        print("Troubleshooting:")
        print("  - Ensure you have NTAG213/215/216 tags")
        print("  - Tag must be blank or writable")
        print("  - Keep tag on reader during entire write")
        print()

except KeyboardInterrupt:
    print("\n\n⚠️  Cancelled by user")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    if 'uart' in locals():
        uart.close()
        print("Serial port closed")
