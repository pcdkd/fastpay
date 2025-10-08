#!/usr/bin/env python3
"""
Replicate the EXACT sequence that worked in test-wire-quality.py
This got a response: DTR/RTS HIGH → send data → DTR/RTS LOW → send command
"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

def read_ack(ser, timeout=1.0):
    """Read ACK frame"""
    deadline = time.time() + timeout
    buf = b''
    while time.time() < deadline and len(buf) < 6:
        chunk = ser.read(6 - len(buf))
        if chunk:
            buf += chunk
    return buf == b'\x00\x00\xFF\x00\xFF\x00'

def read_frame(ser, timeout=1.0):
    """Read response frame"""
    end = time.time() + timeout

    # Find preamble
    while time.time() < end:
        byte1 = ser.read(1)
        if byte1 == b'\x00':
            byte2 = ser.read(1)
            byte3 = ser.read(1)
            if byte2 == b'\x00' and byte3 == b'\xFF':
                break
    else:
        return None

    length_bytes = ser.read(2)
    if len(length_bytes) != 2:
        return None

    length = length_bytes[0]
    data = ser.read(length + 1)
    if len(data) != length + 1:
        return None

    return data[1:-1]  # Strip TFI and DCS

print("🔧 Testing EXACT sequence that worked before")
print("="*60)
print("Replicating test-wire-quality.py successful flow\n")

try:
    # Open serial with flow control disabled
    ser = serial.Serial(PORT, BAUDRATE, timeout=0.5,
                       rtscts=False, dsrdtr=False, xonxoff=False)

    # STEP 1: Start with DTR/RTS HIGH (default)
    ser.dtr = True
    ser.rts = True
    print("Step 1: DTR/RTS set HIGH (default state)")
    print(f"   DTR: {ser.dtr}, RTS: {ser.rts}")
    time.sleep(0.1)

    # STEP 2: Send random wake-up data
    print("\nStep 2: Sending wake-up data...")
    ser.write(b'\x55\xAA\xFF\x00')
    time.sleep(0.2)

    # Clear any response
    if ser.in_waiting > 0:
        garbage = ser.read(ser.in_waiting)
        print(f"   Cleared {len(garbage)} bytes")

    # STEP 3: Send continuous stream (this was in the working test)
    print("\nStep 3: Sending continuous data stream...")
    ser.write(b'\xFF' * 100)
    time.sleep(0.3)

    # Clear response
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"   Got {len(response)} bytes response to stream")

    # STEP 4: NOW switch DTR/RTS to LOW
    print("\nStep 4: Switching DTR/RTS to LOW...")
    ser.dtr = False
    ser.rts = False
    print(f"   DTR: {ser.dtr}, RTS: {ser.rts}")
    time.sleep(0.2)  # Let it stabilize

    # STEP 5: Send GetFirmwareVersion command
    print("\nStep 5: Sending GetFirmwareVersion command...")
    command = bytearray([
        0x00, 0x00, 0xFF, 0x02, 0xFE,
        0xD4, 0x02, 0x2A, 0x00
    ])
    ser.write(command)
    print(f"   Sent: {command.hex(' ')}")
    time.sleep(0.5)  # Give it extra time

    # Read everything available
    print("\nStep 6: Reading response...")
    all_data = b''
    deadline = time.time() + 1.0

    while time.time() < deadline:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            all_data += chunk
            print(f"   Read {len(chunk)} bytes: {chunk.hex(' ')}")
        else:
            time.sleep(0.05)

    if all_data:
        print(f"\n✅ Total received: {len(all_data)} bytes")
        print(f"   Full data: {all_data.hex(' ')}")

        # Try to parse
        if b'\x00\x00\xFF' in all_data:
            print("\n🎉 Valid PN532 frame detected!")

            # Look for firmware response signature
            if b'\xD5\x03' in all_data:
                idx = all_data.index(b'\xD5\x03')
                if idx + 5 <= len(all_data):
                    ic = all_data[idx + 2]
                    ver = all_data[idx + 3]
                    rev = all_data[idx + 4]

                    print("\n" + "="*60)
                    print("🎉 PN532 MODULE WORKING!")
                    print("="*60)
                    print(f"   IC: 0x{ic:02X}")
                    print(f"   Firmware: v{ver}.{rev}")
                    print("\n✅ This sequence works!")
        else:
            print("\n⚠️  Got data but not a valid PN532 frame")
    else:
        print("\n❌ No response received")

        # Try ONE more time with even longer wait
        print("\nRetrying with 2 second wait...")
        ser.write(command)
        time.sleep(2.0)

        if ser.in_waiting > 0:
            late_data = ser.read(ser.in_waiting)
            print(f"✅ Late response: {late_data.hex(' ')}")
        else:
            print("❌ Still no response")

    ser.close()

    print("\n" + "="*60)
    print("Test complete")
    print("\n💡 This replicates the exact sequence from test-wire-quality.py")
    print("   that successfully got firmware v1.6 response")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
