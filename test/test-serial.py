#!/usr/bin/env python3
"""Test FT232 USB-to-UART serial port connectivity"""
import serial
import serial.tools.list_ports

print("🔍 Scanning for USB serial devices...\n")

# List all serial ports
ports = serial.tools.list_ports.comports()

if not ports:
    print("❌ No serial ports found!")
    print("   - Make sure USB cable is plugged in")
    print("   - Try a different USB port")
    exit(1)

print("Available serial ports:")
for port in ports:
    print(f"\n  📍 {port.device}")
    print(f"     Description: {port.description}")
    print(f"     Hardware ID: {port.hwid}")

# Your specific FT232 port
PORT = '/dev/tty.usbserial-ABSCDY4Z'

print(f"\n{'='*50}")
print(f"Testing connection to: {PORT}")
print(f"{'='*50}\n")

try:
    ser = serial.Serial(PORT, 115200, timeout=1)
    print(f"✅ Successfully opened {PORT}")
    print(f"   Baudrate: {ser.baudrate}")
    print(f"   Timeout: {ser.timeout}s")
    print(f"\n🎉 Serial port is ready for NFC communication!")
    ser.close()
except FileNotFoundError:
    print(f"❌ Port not found: {PORT}")
    print(f"   Current port from ls command: {PORT}")
    print(f"   If the port name changed, update PORT variable in this script")
except serial.SerialException as e:
    print(f"❌ Failed to open port: {e}")
    print(f"   - Check if another program is using the port")
    print(f"   - Try unplugging and replugging the USB")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
