#!/usr/bin/env python3
"""
PN532 test with proper ACK handling and control-line management
Based on debug analysis - implements full PN532 UART protocol
Updated to mimic Adafruit wake + SAM sequence and improve robustness
"""
import os
import serial
import time

# Allow env overrides and prefer provided port
PORT = os.getenv('PORT', '/dev/tty.usbserial-ABSCDY4Z')
BAUDRATE = int(os.getenv('BAUD', '115200'))

def read_ack(ser, timeout=1.5):
    """Read and verify ACK frame: 00 00 FF 00 FF 00 (scan-friendly)"""
    deadline = time.time() + timeout
    buf = b''
    target = b'\x00\x00\xff\x00\xff\x00'

    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buf += chunk
            if target in buf:
                return True
        else:
            time.sleep(0.005)  # brief yield

    if buf:
        print(f"   ⚠️ Bytes seen (no ACK): {buf.hex(' ')}")
    else:
        print("   ❌ No ACK received (timeout)")
    return False

def read_frame(ser, timeout=1.0):
    """Read PN532 response frame with proper parsing"""
    end = time.time() + timeout

    # Find preamble: 00 00 FF
    preamble_found = False
    while time.time() < end:
        byte1 = ser.read(1)
        if not byte1:
            time.sleep(0.01)
            continue

        if byte1 == b'\x00':
            byte2 = ser.read(1)
            byte3 = ser.read(1)
            if byte2 == b'\x00' and byte3 == b'\xFF':
                preamble_found = True
                break

    if not preamble_found:
        print("   ❌ No preamble found")
        return None

    # Read length and length checksum
    length_bytes = ser.read(2)
    if len(length_bytes) != 2:
        print("   ❌ Incomplete length bytes")
        return None

    length = length_bytes[0]
    lcs = length_bytes[1]

    # Verify length checksum
    if ((length + lcs) & 0xFF) != 0:
        print(f"   ❌ Invalid length checksum: {length:02X} + {lcs:02X}")
        return None

    # Read data + data checksum
    data = ser.read(length + 1)
    if len(data) != length + 1:
        print(f"   ❌ Incomplete data (expected {length + 1}, got {len(data)})")
        return None

    # Strip TFI (first byte) and DCS (last byte), return payload
    payload = data[1:-1]
    return payload

def wake_and_toggle(ser):
    """Attempt to wake PN532 and reproduce the one-time success sequence.
    Sequence: assert lines HIGH → send wake bytes → clear → set LOW.
    """
    # Assert control lines HIGH briefly
    ser.dtr = True
    ser.rts = True
    time.sleep(0.1)

    # Send HSU wake bytes (commonly recognized)
    ser.write(b'\x55\x55\x00\x00\x00')
    ser.flush()
    time.sleep(0.2)

    # Also send the prior "worked once" junk pattern
    ser.write(b'\x55\xAA\xFF\x00')
    ser.flush()
    time.sleep(0.1)

    # Clear any garbage
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    # Drop control lines LOW (critical for this board)
    ser.dtr = False
    ser.rts = False
    time.sleep(0.2)

def wait_ready(ser, timeout=1.0):
    """Poll the UART like Adafruit's _wait_ready to avoid busy reads."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ser.in_waiting > 0:
            return True
        time.sleep(0.01)
    return False

def adafruit_style_wakeup_and_sam(ser):
    """Mimic Adafruit PN532_UART._wakeup() + SAM_configuration()."""
    # Ensure low power flag equivalent: always perform wake on first call
    # Write long wake stream (per Adafruit): 0x55 0x55 followed by many 0x00
    ser.reset_input_buffer()
    ser.write(b"\x55\x55" + b"\x00" * 15)
    ser.flush()
    time.sleep(0.02)

    # Immediately send SAMConfiguration and verify ACK/response
    sam_cmd = bytearray([0x14, 0x01, 0x14, 0x01])
    frame = send_command(ser, sam_cmd)
    if not wait_ready(ser, timeout=1.0):
        return False
    if not read_ack(ser, timeout=1.5):
        return False
    # Wait for SAM response
    if not wait_ready(ser, timeout=1.0):
        return False
    resp = read_frame(ser, timeout=1.5)
    return resp is not None

def send_command(ser, command_data):
    """Send PN532 command frame"""
    # Build frame: preamble + length + data + checksums
    preamble = b'\x00\x00\xFF'
    length = len(command_data) + 1  # +1 for TFI
    lcs = (0x100 - length) & 0xFF
    tfi = 0xD4  # Host to PN532

    # Calculate data checksum
    dcs = (0x100 - (tfi + sum(command_data))) & 0xFF

    # Build complete frame
    frame = bytearray(preamble)
    frame.append(length)
    frame.append(lcs)
    frame.append(tfi)
    frame.extend(command_data)
    frame.append(dcs)
    frame.append(0x00)  # Postamble

    # Clear any stale bytes before sending (Adafruit does this)
    try:
        ser.reset_input_buffer()
    except Exception:
        pass
    ser.write(frame)
    try:
        ser.flush()
    except Exception:
        pass
    return frame

print("🔧 PN532 Test with Proper ACK Handling")
print("="*60)
print(f"Port: {PORT}")
print(f"Baudrate: {BAUDRATE}\n")

try:
    # Open serial with flow control DISABLED
    ser = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=1,
        rtscts=False,   # No hardware flow control
        dsrdtr=False,   # No modem flow control
        xonxoff=False   # No software flow control
    )

    # CRITICAL: Force control lines LOW
    ser.dtr = False
    ser.rts = False

    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    print("✅ Serial port configured")
    print(f"   DTR: {ser.dtr} (LOW)")
    print(f"   RTS: {ser.rts} (LOW)")
    print(f"   Flow control: all disabled\n")

    time.sleep(0.2)  # Let signals stabilize

    # Test 0: Adafruit-style wake & SAM
    print("TEST 0: Wake + SAM (Adafruit style)")
    print("-" * 60)
    if adafruit_style_wakeup_and_sam(ser):
        print("   ✅ Wake + SAM successful\n")
    else:
        print("   ⚠️  Wake + SAM did not get ACK/response\n")

    # Test 1: GetFirmwareVersion
    print("TEST 1: GetFirmwareVersion")
    print("-" * 60)

    # Try waking/toggling before sending
    wake_and_toggle(ser)

    # Send command
    cmd = bytearray([0x02])  # GetFirmwareVersion command code
    frame = send_command(ser, cmd)
    print(f"📤 Sent: {frame.hex(' ')}")

    time.sleep(0.15)  # Give module time to process

    # Read ACK
    print("📥 Reading ACK...")
    # Poll for readiness first (like Adafruit)
    wait_ready(ser, timeout=1.0)
    if read_ack(ser, timeout=1.5):
        print("   ✅ ACK received!")

        # Read response frame
        print("📥 Reading response frame...")
        wait_ready(ser, timeout=1.0)
        response = read_frame(ser, timeout=1.5)

        if response:
            print(f"   ✅ Response: {response.hex(' ')}")

            # Parse firmware info
            if len(response) >= 4 and response[0] == 0x03:  # Response code
                ic = response[1]
                ver = response[2]
                rev = response[3]
                support = response[4] if len(response) > 4 else 0

                print("\n" + "="*60)
                print("🎉 PN532 MODULE DETECTED!")
                print("="*60)
                print(f"   IC Type: 0x{ic:02X} (PN532)")
                print(f"   Firmware: v{ver}.{rev}")
                print(f"   Support: 0x{support:02X}")
                print("\n✅ Module is working correctly!")
            else:
                print(f"   ⚠️  Unexpected response format")
        else:
            print("   ❌ No response frame received")
    else:
        print("   ❌ No ACK - module not responding")

        # Debug: show what we got
        if ser.in_waiting > 0:
            leftover = ser.read(ser.in_waiting)
            print(f"   Debug: Leftover data: {leftover.hex(' ')}")

    # Test 2: SAM Configuration (optional)
    print("\n" + "-"*60)
    print("TEST 2: SAM Configuration")
    print("-" * 60)

    # Wake again before SAM
    wake_and_toggle(ser)

    # SAM Configuration: normal mode, 1 sec timeout, use IRQ
    sam_cmd = bytearray([0x14, 0x01, 0x14, 0x01])
    frame = send_command(ser, sam_cmd)
    print(f"📤 Sent: {frame.hex(' ')}")

    time.sleep(0.15)

    print("📥 Reading ACK...")
    if read_ack(ser, timeout=1.5):
        print("   ✅ SAM ACK received!")

        print("📥 Reading SAM response...")
        response = read_frame(ser, timeout=1.5)

        if response:
            print(f"   ✅ SAM Response: {response.hex(' ')}")
            print("   ✅ SAM configured successfully!")
        else:
            print("   ⚠️  No SAM response (might be okay)")
    else:
        print("   ❌ No SAM ACK")

        # Optional retry: try SAM without IRQ flag
        print("   ↻ Retrying SAM without IRQ (0x00)...")
        wake_and_toggle(ser)
        sam_cmd_no_irq = bytearray([0x14, 0x01, 0x14, 0x00])
        frame = send_command(ser, sam_cmd_no_irq)
        print(f"📤 Sent: {frame.hex(' ')}")
        time.sleep(0.15)
        print("📥 Reading ACK...")
        if read_ack(ser, timeout=1.5):
            print("   ✅ SAM(no IRQ) ACK received!")
            print("📥 Reading SAM response...")
            response = read_frame(ser, timeout=1.5)
            if response:
                print(f"   ✅ SAM(no IRQ) Response: {response.hex(' ')}")
                print("   ✅ SAM configured successfully (no IRQ)!")
            else:
                print("   ⚠️  No SAM(no IRQ) response")
        else:
            print("   ❌ No SAM(no IRQ) ACK either")

    ser.close()

    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("\n💡 If successful, use this pattern in your production code:")
    print("   1. Open serial with flow control disabled")
    print("   2. Set DTR=False, RTS=False")
    print("   3. Send command frame")
    print("   4. Read ACK frame (6 bytes)")
    print("   5. Read response frame (with proper parsing)")

except serial.SerialException as e:
    print(f"❌ Serial error: {e}")
except KeyboardInterrupt:
    print("\n⚠️  Interrupted by user")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
