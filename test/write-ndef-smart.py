#!/usr/bin/env python3
"""
Smart NDEF writer - checks existing format first
Many NTAG tags come pre-formatted, so we just write data
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

payment = {
    "v": 1,
    "addr": "0x742d35Cc...bEb",
    "merchant": "Alice Coffee",
    "amt": "5.00 USDC",
    "item": "Latte",
    "time": int(time.time())
}

def create_ndef_text_record(text):
    """Create NDEF Text Record"""
    text_bytes = text.encode('utf-8')
    header = 0xD1  # MB=1, ME=1, SR=1, TNF=Well-known
    type_field = b'T'
    language = b'\x02en'
    payload = language + text_bytes

    record = bytearray()
    record.append(header)
    record.append(len(type_field))
    record.append(len(payload))
    record.extend(type_field)
    record.extend(payload)
    return bytes(record)

def create_ndef_message(text):
    """Create TLV-wrapped NDEF message"""
    ndef_record = create_ndef_text_record(text)

    tlv = bytearray()
    tlv.append(0x03)  # NDEF Message
    tlv.append(len(ndef_record))
    tlv.extend(ndef_record)
    tlv.append(0xFE)  # Terminator
    return bytes(tlv)

def check_ndef_formatted(pn532, uid):
    """Check if tag is already NDEF formatted"""
    try:
        cc = pn532.ntag2xx_read_block(3)
        print(f"   Current CC (page 3): {cc.hex()}")

        if cc[0] == 0xE1:
            print(f"   ✅ Already NDEF formatted!")
            print(f"      Version: {cc[1]:02X}")
            print(f"      Size: {cc[2]:02X}")
            print(f"      Access: {cc[3]:02X}")
            return True
        else:
            print(f"   ⚠️  Not NDEF formatted (CC={cc.hex()})")
            return False
    except Exception as e:
        print(f"   ⚠️  Can't read CC: {e}")
        return False

def write_ndef_data(pn532, uid, ndef_message):
    """Write NDEF data starting at page 4"""
    print(f"   Writing {len(ndef_message)} bytes...")

    # Pad to 4-byte boundary
    padded = bytearray(ndef_message)
    while len(padded) % 4 != 0:
        padded.append(0x00)

    pages = len(padded) // 4
    print(f"   Pages to write: {pages}")

    success_count = 0
    fail_count = 0

    for i in range(pages):
        page_num = 4 + i
        chunk = padded[i*4:(i+1)*4]

        try:
            pn532.ntag2xx_write_block(page_num, bytes(chunk))
            success_count += 1

            # Show progress
            if i < 2 or i >= pages - 2:
                print(f"   ✅ Page {page_num}: {chunk.hex()}")
            elif i == 2:
                print(f"   ... writing pages 6-{3+pages} ...")

        except Exception as e:
            fail_count += 1
            if fail_count < 3:  # Only show first few errors
                print(f"   ❌ Page {page_num}: {e}")

    print(f"\n   Results: {success_count} success, {fail_count} failed")
    return success_count > 0

print("🔧 Smart NDEF Writer")
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
    payment_json = json.dumps(payment, separators=(',', ':'))
    print(f"Payment: {payment_json}")
    print(f"Size: {len(payment_json)} bytes\n")

    ndef_msg = create_ndef_message(payment_json)
    print(f"NDEF size: {len(ndef_msg)} bytes\n")

    print("="*60)
    print("📱 PLACE TAG ON MODULE")
    print("="*60)
    print()

    attempts = 0
    while attempts < 20:
        uid = pn532.read_passive_target(timeout=0.5)

        if uid and len(uid) == 4:
            uid_hex = uid.hex().upper()
            print(f"🎉 Tag: {uid_hex}\n")

            # Check if already formatted
            is_formatted = check_ndef_formatted(pn532, uid)

            if not is_formatted:
                print("\n   Tag not NDEF formatted.")
                print("   Trying to format page 3...")
                try:
                    cc = bytearray([0xE1, 0x10, 0x12, 0x00])
                    pn532.ntag2xx_write_block(3, cc)
                    print(f"   ✅ Formatted!")
                except:
                    print(f"   ❌ Can't write page 3 (might be locked)")
                    print(f"   Continuing anyway - will write data pages...\n")

            # Write data regardless of CC success
            print(f"\n📝 Writing data pages...")
            if write_ndef_data(pn532, uid, ndef_msg):
                print("\n" + "="*60)
                print("✅ DATA WRITTEN!")
                print("="*60)

                # Try to read back
                print("\n📖 Reading back...")
                try:
                    data = bytearray()
                    for p in range(4, 8):
                        page_data = pn532.ntag2xx_read_block(p)
                        if page_data:
                            data.extend(page_data)

                    text = data.decode('utf-8', errors='ignore').rstrip('\x00')
                    print(f"   Read: {text[:80]}...")

                    if '{"v":1' in text:
                        print("\n   ✅ Looks good!")
                except Exception as e:
                    print(f"   ⚠️  {e}")

                print("\n" + "="*60)
                print("📱 TEST WITH PHONE:")
                print("="*60)
                print("\n1. Open NFC Tools app")
                print("2. Tap READ")
                print("3. Scan the tag")
                print("\nExpected: Text record with JSON")
                print(f"Content: {payment_json[:50]}...")

                break

        attempts += 1
        if attempts % 5 == 0:
            print(f"   Waiting... ({attempts}/20)")
        time.sleep(0.5)

    uart.close()
    print("\n✅ Done")

except KeyboardInterrupt:
    print("\n⚠️  Stopped")
    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
