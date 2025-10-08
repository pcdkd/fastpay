#!/usr/bin/env python3
"""Check FT232 driver and USB configuration"""
import serial
import serial.tools.list_ports
import subprocess
import sys

PORT = '/dev/tty.usbserial-ABSCDY4Z'

print("🔍 FT232 Driver and USB Configuration Check\n")
print("="*60)

# 1. Get detailed port info
print("\n1. Serial Port Details:")
for port in serial.tools.list_ports.comports():
    if 'ABSCDY4Z' in port.device:
        print(f"   Device: {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
        print(f"   VID:PID: {port.vid:04X}:{port.pid:04X}")
        print(f"   Serial Number: {port.serial_number}")
        print(f"   Manufacturer: {port.manufacturer}")
        print(f"   Product: {port.product}")

# 2. Check macOS USB system info
print("\n2. macOS USB System Info:")
try:
    result = subprocess.run(['system_profiler', 'SPUSBDataType'],
                          capture_output=True, text=True, timeout=5)

    # Find FT232 section
    lines = result.stdout.split('\n')
    in_ft232_section = False

    for line in lines:
        if 'FT232R USB UART' in line or 'ABSCDY4Z' in line:
            in_ft232_section = True

        if in_ft232_section:
            print(f"   {line}")
            if 'Location ID' in line or 'Current Available' in line:
                pass  # Keep printing
            elif line.strip() and ':' not in line:
                break  # End of section

except Exception as e:
    print(f"   ⚠️  Could not get USB info: {e}")

# 3. Check driver version
print("\n3. FT232 Driver Check:")
try:
    # Check for FTDI kext (kernel extension)
    result = subprocess.run(['kextstat'], capture_output=True, text=True)

    ftdi_drivers = [line for line in result.stdout.split('\n')
                    if 'ftdi' in line.lower() or 'serial' in line.lower()]

    if ftdi_drivers:
        print("   Found kernel extensions:")
        for driver in ftdi_drivers[:5]:  # Show first 5
            print(f"   {driver}")
    else:
        print("   ✅ Using built-in macOS driver (Apple's IOUSBFamily)")
        print("   This is normal and preferred for FT232R")

except Exception as e:
    print(f"   ⚠️  Could not check kexts: {e}")

# 4. Test serial port settings
print("\n4. Serial Port Configuration:")
try:
    ser = serial.Serial(PORT, 115200, timeout=1)

    print(f"   Baudrate: {ser.baudrate}")
    print(f"   Bytesize: {ser.bytesize}")
    print(f"   Parity: {ser.parity}")
    print(f"   Stopbits: {ser.stopbits}")
    print(f"   Timeout: {ser.timeout}s")
    print(f"   Xonxoff (software flow): {ser.xonxoff}")
    print(f"   Rtscts (hardware flow): {ser.rtscts}")
    print(f"   Dsrdtr (modem flow): {ser.dsrdtr}")
    print(f"   DTR: {ser.dtr}")
    print(f"   RTS: {ser.rts}")

    # Try different flow control settings
    print("\n5. Testing Flow Control Settings:")

    configs = [
        ("No flow control", False, False, False),
        ("RTS/CTS hardware", True, False, False),
        ("XON/XOFF software", False, True, False),
        ("DSR/DTR modem", False, False, True),
    ]

    for name, rtscts, xonxoff, dsrdtr in configs:
        ser.close()
        ser = serial.Serial(PORT, 115200, timeout=0.5,
                           rtscts=rtscts, xonxoff=xonxoff, dsrdtr=dsrdtr)
        ser.dtr = False
        ser.rts = False

        print(f"\n   Testing: {name}")
        print(f"      rtscts={rtscts}, xonxoff={xonxoff}, dsrdtr={dsrdtr}")

        # Send GetFirmwareVersion
        import time
        time.sleep(0.1)

        cmd = bytearray([0x00, 0x00, 0xFF, 0x02, 0xFE, 0xD4, 0x02, 0x2A, 0x00])
        ser.write(cmd)
        time.sleep(0.3)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"      ✅ RESPONSE! {response.hex(' ')}")
        else:
            print(f"      ❌ No response")

    ser.close()

except Exception as e:
    print(f"   ❌ Error: {e}")

# 6. Check USB power management
print("\n6. USB Power Management:")
try:
    result = subprocess.run(['pmset', '-g'], capture_output=True, text=True)

    for line in result.stdout.split('\n'):
        if 'usb' in line.lower() or 'sleep' in line.lower():
            print(f"   {line}")

    print("\n   Note: USB sleep can cause intermittent communication")
    print("   Try: sudo pmset -a disksleep 0 (to disable USB sleep)")

except Exception as e:
    print(f"   ⚠️  Could not check power settings: {e}")

print("\n" + "="*60)
print("\n📊 DRIVER DIAGNOSIS:")
print("\nIf you see 'Apple's IOUSBFamily' → Using native macOS driver (good)")
print("If you see FTDI kexts → May need to uninstall for testing")
print("\nTo disable FTDI driver temporarily:")
print("  sudo kextunload -b com.FTDI.driver.FTDIUSBSerialDriver")
print("\nTo check if custom driver is interfering:")
print("  ls /System/Library/Extensions/ | grep -i ftdi")
print("  ls /Library/Extensions/ | grep -i ftdi")
