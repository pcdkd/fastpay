#!/usr/bin/env python3
"""
FastPay Card Emulation - using nfcpy

This script uses the `nfcpy` library to emulate an NFC Forum Type 2 Tag,
serving a JSON payment request as an NDEF Text Record.

nfcpy's tag emulation requires handling APDU commands from the phone.
The library provides helper classes for common tag types.
"""
import json
import time
import nfc
import ndef
from nfc.tag.tt2 import Type2Tag

# The serial port where the PN532 is connected.
SERIAL_PORT = 'tty:usbserial-ABSCDY4Z'

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

class CardEmulator:
    def __init__(self, device_path):
        self.device_path = device_path
        self.clf = None
        self.ndef_record = None

    def on_connect(self, tag):
        # This callback is required but we don't need to do anything here
        # for a read-only tag. The session is handled by the library.
        return True

    def on_release(self, tag):
        # This callback is required and terminates the listen loop.
        return True

    def run(self):
        print("✅ FastPay Card Emulation with nfcpy")
        print("=" * 60)
        print(f"Using device: {self.device_path}")

        # Prepare NDEF message content
        payment_json = json.dumps(payment, separators=(',', ':'))
        ndef_message = [ndef.TextRecord(payment_json)]
        ndef_data = b''.join(ndef.message_encoder(ndef_message))

        print(f"   NDEF Size: {len(ndef_data)} bytes")
        print(f"   Payment: {payment_json[:60]}...")
        print("=" * 60)
        print("📱 TAP YOUR PHONE NOW!")
        print("=" * 60)
        print("(Press Ctrl+C to stop)")
        print()

        tap_count = 0

        try:
            self.clf = nfc.ContactlessFrontend(self.device_path)

            while True:
                print(f"[{time.strftime('%H:%M:%S')}] Listening for phone tap...")

                # Configure LocalTarget for NFC-A (Type 2 Tag emulation)
                # This makes the PN532 act as a passive tag that responds to readers
                target = nfc.clf.LocalTarget('106A')
                target.sensf_res = bytearray.fromhex('01 FE FF FF FF FF FF FF C0 C1 C2 C3 C4 C5 C6 C7 FF FF')
                target.sens_res = bytearray.fromhex('0001')  # SENS_RES for Type 2
                target.sel_res = bytearray.fromhex('00')      # SEL_RES for Type 2
                target.sdd_res = bytearray.fromhex('08123456')  # 4-byte UID

                # NDEF data payload (will be requested by phone via READ commands)
                # For Type 2 Tag, data is stored in memory pages
                # We need to format this as Type 2 Tag memory structure

                # Type 2 Tag memory structure:
                # Pages 0-3: UID + lock bytes (read-only)
                # Page 4+: NDEF TLV (Type-Length-Value) structure

                # Create NDEF TLV structure
                ndef_tlv = bytearray()
                ndef_tlv.append(0x03)  # NDEF Message TLV type
                if len(ndef_data) < 255:
                    ndef_tlv.append(len(ndef_data))  # Length (1 byte)
                else:
                    ndef_tlv.append(0xFF)  # Extended length marker
                    ndef_tlv.append((len(ndef_data) >> 8) & 0xFF)  # Length MSB
                    ndef_tlv.append(len(ndef_data) & 0xFF)  # Length LSB
                ndef_tlv.extend(ndef_data)  # NDEF message
                ndef_tlv.append(0xFE)  # Terminator TLV

                # Build complete tag memory (simulating 64 pages of 4 bytes each)
                tag_memory = bytearray(64 * 4)

                # Pages 0-3: UID and lock bytes
                tag_memory[0:4] = bytearray.fromhex('08123456')  # UID
                tag_memory[4:8] = bytearray.fromhex('00000000')  # Internal/Lock
                tag_memory[8:12] = bytearray.fromhex('E1100600')  # CC (Capability Container)
                tag_memory[12:16] = bytearray.fromhex('00000000')  # Lock bits

                # Pages 4+: NDEF TLV data
                tag_memory[16:16+len(ndef_tlv)] = ndef_tlv

                # Store in target (nfcpy will serve this on READ commands)
                target.tt2_data = bytes(tag_memory)

                print(f"   Tag memory prepared: {len(tag_memory)} bytes")
                print(f"   NDEF TLV size: {len(ndef_tlv)} bytes")
                print()

                # Listen as a target (card emulation mode)
                result = self.clf.listen(target, timeout=30.0)

                if result:
                    tap_count += 1
                    print(f"\n🎉 PHONE TAP #{tap_count} DETECTED!")
                    print(f"   Time: {time.strftime('%H:%M:%S')}")
                    print(f"   Initiator: {result}")
                    print()
                    print("=" * 60)
                    print(f"✅ Session #{tap_count} complete")
                    print("=" * 60)
                    print()

                time.sleep(0.5)

        except IOError as e:
            print(f"\n❌ Error: Could not connect to PN532 on {self.device_path}")
            print("   - Is the device connected and the port correct?")
            print(f"   - {e}")
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
        finally:
            if self.clf:
                self.clf.close()

if __name__ == '__main__':
    emulator = CardEmulator(SERIAL_PORT)
    try:
        emulator.run()
    except KeyboardInterrupt:
        print("\n📊 Shutting down...")
    finally:
        if emulator.clf:
            emulator.clf.close()
        print("✅ Test complete")