#!/usr/bin/env python3
"""
Write payment request as proper NDEF format that phones can read
NDEF = NFC Data Exchange Format (the standard phones understand)
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# Compact payment (must fit in 144 bytes total with NDEF overhead)
payment = {
    "v": 1,
    "addr": "0x742d35Cc...f0bEb",  # Shortened for space
    "name": "Alice's Coffee",
    "amt": "5.00",
    "desc": "Latte",
    "time": int(time.time())
}

def create_ndef_text_record(text):
    """
    Create NDEF Text Record that phones can read
    Format: Header + Type Length + Payload Length + Type + Language + Text
    """
    text_bytes = text.encode('utf-8')

    # NDEF Text Record header
    # Bit 7: MB (Message Begin) = 1
    # Bit 6: ME (Message End) = 1
    # Bit 5: CF (Chunk Flag) = 0
    # Bit 4: SR (Short Record) = 1
    # Bit 3: IL (ID Length) = 0
    # Bits 2-0: TNF (Type Name Format) = 001 (Well-known)
    header = 0xD1  # 11010001

    type_field = b'T'  # Text record
    type_length = len(type_field)

    # Language code (0x02 = UTF-8, 'en')
    language = b'\x02en'
    payload = language + text_bytes
    payload_length = len(payload)

    # Build NDEF record
    record = bytearray()
    record.append(header)
    record.append(type_length)
    record.append(payload_length)
    record.extend(type_field)
    record.extend(payload)

    return bytes(record)

def create_ndef_message(text):
    """
    Create complete NDEF message with TLV wrapper
    TLV = Type-Length-Value format required for NTAG
    """
    # Create the NDEF record
    ndef_record = create_ndef_text_record(text)

    # Wrap in TLV structure
    # TLV format: [Type][Length][Value]
    # Type: 0x03 = NDEF Message
    # Length: size of NDEF record
    # Value: the NDEF record

    tlv = bytearray()
    tlv.append(0x03)  # NDEF Message TLV

    if len(ndef_record) < 255:
        tlv.append(len(ndef_record))  # 1-byte length
    else:
        tlv.append(0xFF)  # Extended length marker
        tlv.extend(len(ndef_record).to_bytes(2, 'big'))

    tlv.extend(ndef_record)
    tlv.append(0xFE)  # Terminator TLV

    return bytes(tlv)

def format_ntag_for_ndef(pn532, uid):
    """
    Write NDEF capability container to page 3
    Required for phones to recognize this as an NDEF tag
    """
    # NTAG213 Capability Container (CC)
    # Byte 0: Magic number (0xE1)
    # Byte 1: Version (0x10 = v1.0)
    # Byte 2: Memory size (0x12 = 144 bytes for NTAG213)
    # Byte 3: Read/Write access (0x00 = full access)
    cc = bytearray([0xE1, 0x10, 0x12, 0x00])

    print("   Formatting tag for NDEF...")
    try:
        pn532.ntag2xx_write_block(3, cc)
        print(f"   ✅ Capability Container written: {cc.hex()}")
        return True
    except Exception as e:
        print(f"   ❌ CC write failed: {e}")
        return False

def write_ndef_to_ntag(pn532, uid, ndef_message):
    """
    Write NDEF message starting at page 4
    """
    print(f"   NDEF message size: {len(ndef_message)} bytes")

    # NTAG user memory starts at page 4
    start_page = 4
    bytes_per_page = 4

    # Pad to multiple of 4
    padded = bytearray(ndef_message)
    while len(padded) % bytes_per_page != 0:
        padded.append(0x00)

    pages_needed = len(padded) // bytes_per_page
    print(f"   Pages needed: {pages_needed}")

    if pages_needed > 36:  # NTAG213 limit
        print(f"   ⚠️  Too large! Max 36 pages (144 bytes)")
        return False

    # Write each page
    for i in range(pages_needed):
        page_num = start_page + i
        start_idx = i * bytes_per_page
        chunk = padded[start_idx:start_idx + bytes_per_page]

        try:
            pn532.ntag2xx_write_block(page_num, bytes(chunk))
            # Only print first few and last few pages to reduce spam
            if i < 3 or i >= pages_needed - 2:
                print(f"   ✅ Page {page_num}: {chunk.hex()}")
            elif i == 3:
                print(f"   ... (writing pages {page_num} to {start_page + pages_needed - 3}) ...")
        except Exception as e:
            print(f"   ❌ Page {page_num} failed: {e}")
            return False

    return True

print("🔧 Write NDEF-Formatted Payment Request")
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

    # Create compact payment JSON
    payment_json = json.dumps(payment, separators=(',', ':'))

    print("Payment Request:")
    print("-" * 60)
    print(json.dumps(payment, indent=2))
    print("-" * 60)
    print(f"\nCompact: {payment_json}")
    print(f"Size: {len(payment_json)} bytes\n")

    # Create NDEF message
    ndef_msg = create_ndef_message(payment_json)
    print(f"NDEF message size: {len(ndef_msg)} bytes (includes headers)")
    print(f"First 20 bytes: {ndef_msg[:20].hex()}\n")

    if len(ndef_msg) > 140:  # Leave room for TLV overhead
        print("⚠️  Payload too large for NTAG213!")
        print("   Shortening to fit...\n")

        short_payment = {
            "v": 1,
            "amt": "5.00",
            "merchant": "Alice",
            "item": "Latte"
        }
        payment_json = json.dumps(short_payment, separators=(',', ':'))
        ndef_msg = create_ndef_message(payment_json)
        print(f"   Shortened payload: {payment_json}")
        print(f"   New NDEF size: {len(ndef_msg)} bytes\n")

    print("="*60)
    print("📱 PLACE NFC TAG ON MODULE")
    print("="*60)
    print("Waiting for NTAG tag...\n")

    tag_found = False
    attempts = 0

    while not tag_found and attempts < 30:
        uid = pn532.read_passive_target(timeout=0.5)

        if uid and len(uid) == 4:
            uid_hex = uid.hex().upper()
            print(f"🎉 NTAG detected: {uid_hex}\n")

            # Format tag with NDEF capability container
            if not format_ntag_for_ndef(pn532, uid):
                print("   ⚠️  Could not format tag")
                attempts += 1
                time.sleep(1)
                continue

            # Write NDEF message
            print("\n📝 Writing NDEF message...")
            if write_ndef_to_ntag(pn532, uid, ndef_msg):
                print("\n" + "="*60)
                print("✅ NDEF MESSAGE WRITTEN!")
                print("="*60)

                # Verify
                print("\n📖 Verifying...")
                try:
                    cc = pn532.ntag2xx_read_block(3)
                    print(f"   CC (page 3): {cc.hex()}")

                    page4 = pn532.ntag2xx_read_block(4)
                    print(f"   Data start (page 4): {page4.hex()}")

                    # Check if it's NDEF formatted
                    if cc[0] == 0xE1:
                        print("   ✅ NDEF format confirmed!")
                    else:
                        print(f"   ⚠️  Unexpected CC: {cc.hex()}")

                except Exception as e:
                    print(f"   ⚠️  Verify failed: {e}")

                print("\n" + "="*60)
                print("📱 NOW SCAN WITH YOUR PHONE!")
                print("="*60)
                print("\n1. Open NFC Tools app")
                print("2. Go to READ tab")
                print("3. Tap phone on tag")
                print("4. Should show:")
                print(f"   Type: Text")
                print(f"   Content: {payment_json}")

                tag_found = True
            else:
                print("\n❌ Write failed, will retry...")
                time.sleep(1)

        attempts += 1
        if attempts % 5 == 0 and not tag_found:
            print(f"   Waiting... ({attempts}/30)")

        time.sleep(0.5)

    if not tag_found:
        print("\n⏱️  No tag detected")

    uart.close()
    print("\n✅ Test complete")

except KeyboardInterrupt:
    print("\n⚠️  Stopped")
    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
