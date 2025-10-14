#!/usr/bin/env python3
"""
FastPay Card Emulation - using libnfc

This script uses the `libnfc` command-line tool `nfc-emulate-tag`
to perform card emulation. It is a simple, robust wrapper that outsources
the complex NFC protocol handling to the battle-tested libnfc library.

This approach was found to be a reliable alternative to Python-native libraries.
"""
import subprocess
import time
import atexit

# Global variable to hold the emulator process
emulator_process = None

def cleanup():
    """Ensure the subprocess is terminated when the script exits."""
    global emulator_process
    if emulator_process and emulator_process.poll() is None:
        print("\n🧹 Cleaning up and stopping emulator...")
        emulator_process.terminate()
        emulator_process.wait()
        print("✅ Emulator stopped.")

atexit.register(cleanup)

def run_emulation():
    """Starts the nfc-emulate-tag subprocess and waits for user input."""
    global emulator_process

    print("✅ FastPay Card Emulation with libnfc")
    print("=" * 60)
    print("Starting `nfc-emulate-ndef` subprocess...")
    print("This will emulate an NFC tag containing a URL (google.com).")
    print("=" * 60)

    try:
        # Start the libnfc NDEF emulation tool. It will serve a URL.
        # This provides a clear action for the phone to take.
        emulator_process = subprocess.Popen(
            ['nfc-emulate-ndef', '-r', 'ndef:url:google.com'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a moment for the process to initialize
        time.sleep(2)

        # Check if the process started correctly
        if emulator_process.poll() is not None:
            stderr_output = emulator_process.stderr.read()
            raise RuntimeError(f"Failed to start nfc-emulate-tag. Error:\n{stderr_output}")

        print("📱 TAP YOUR PHONE NOW!")
        print("=" * 60)
        print("(Press Ctrl+C to stop)")
        
        # The nfc-emulate-tag process runs until terminated.
        # We can monitor its output here if needed.
        while True:
            # Reading stdout can be used to check for interactions
            # For now, we just wait.
            time.sleep(1)

    except FileNotFoundError:
        print("\n❌ Error: `nfc-emulate-tag` command not found.")
        print("   Please ensure `libnfc` is installed correctly and in your PATH.")
    except KeyboardInterrupt:
        print("\n📊 User interrupted. Shutting down...")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == '__main__':
    run_emulation()
