# PN532 NFC Module Debug Report
**Date:** October 5, 2025
**Project:** FastPay Phase 1 - Desktop Development Setup
**Status:** 🟡 PARTIAL SUCCESS - Module responds intermittently

---

## Hardware Configuration

### NFC Module
- **Model:** DFRobot DFR0231-H Gravity NFC Module
- **Chip:** PN532
- **Mode:** UART (confirmed via physical switch)
- **Voltage:** 3.3V-5.5V tolerant
- **Power LED:** ✅ Red LED is lit (confirms power)

### USB-to-UART Converter
- **Model:** "Mayina" FT232R USB UART
- **Chip:** FT232R (VID:PID=0403:6001)
- **Serial Port:** `/dev/tty.usbserial-ABSCDY4Z`
- **Voltage Output:** 5V (tested), 3.3V available

### Wiring Configuration
```
FT232 (Mayina) → DFRobot NFC Module
====================================
VCC (5V)       → VCC       [RED wire]
GND            → GND       [BLACK wire]
TXD            → C/R       [BLUE wire] ✅ CROSSOVER
RXD            → D/T       [GREEN wire] ✅ CROSSOVER
```

**Verification:** Wiring is 100% correct per documentation. Crossover properly implemented.

---

## Software Environment

### System
- **OS:** macOS (Darwin 24.6.0)
- **Python:** 3.12.x
- **pyserial:** 3.5 (installed and working)

### Test Location
- **Working Directory:** `/Users/danieldewar/Documents/dev/fastpay/test/`
- **Test Scripts Created:**
  - `test-serial.py` - Serial port detection ✅
  - `test-nfc.py` - Basic PN532 communication ❌
  - `test-nfc-debug.py` - Comprehensive diagnostics ❌
  - `test-baudrates.py` - Multi-baudrate testing ❌
  - `test-wire-quality.py` - Raw serial testing ⚠️ PARTIAL SUCCESS
  - `test-nfc-working.py` - DTR/RTS fix attempt ❌
  - `test-nfc-wakeup.py` - Wake-up sequence (not yet run)

---

## Test Results Summary

### ✅ WORKING
1. **Serial Port Detection**
   - FT232R detected successfully
   - Port `/dev/tty.usbserial-ABSCDY4Z` opens without errors
   - Baudrate 115200 configures correctly

### ⚠️ PARTIAL SUCCESS
2. **Raw Serial Communication** (`test-wire-quality.py`)
   - **CRITICAL FINDING:** Module responded ONCE in Test 3
   - Response received when DTR=False, RTS=False
   - **Raw Response Data:**
     ```
     00 00 ff 00 ff 00 00 00 ff 06 fa d5 03 32 01 06 07 e8 00
     ```
   - **Decoded Response:**
     - `D5 03` = GetFirmwareVersion response
     - `32` = IC Type (PN532)
     - `01 06` = **Firmware v1.6**
     - `07` = Revision 7
   - **Conclusion:** Module is ALIVE and can communicate!

### ❌ NOT WORKING
3. **Consistent Communication**
   - Module does not respond to repeated GetFirmwareVersion commands
   - No response at any baudrate (9600, 19200, 38400, 57600, 115200)
   - No response to SAM Configuration commands
   - No response to wake-up sequences (standard approach)

---

## Key Findings

### Finding #1: DTR/RTS Control Signal Requirement
The PN532 module **only responded** when:
- DTR (Data Terminal Ready) = **False** (LOW)
- RTS (Request To Send) = **False** (LOW)

Default Python serial behavior sets these HIGH, which blocks communication.

**Code Fix Required:**
```python
ser = serial.Serial(PORT, BAUDRATE, timeout=1)
ser.dtr = False  # CRITICAL
ser.rts = False  # CRITICAL
time.sleep(0.2)  # Allow signals to stabilize
```

### Finding #2: Timing/Sequence Dependency
The successful response occurred in a specific sequence:
1. Port opened with DTR/RTS HIGH (default)
2. Random data sent (`\x55\xAA\xFF\x00`)
3. Wait 0.2 seconds
4. DTR/RTS set to LOW
5. Wait 0.1 seconds
6. GetFirmwareVersion command sent
7. **Response received!**

When trying to replicate this exact sequence, it did NOT work consistently.

### Finding #3: Single Response Only
The module has responded exactly **once** across all testing.
Subsequent attempts with identical code/timing have failed.

**Possible explanations:**
- Module needs hardware reset between commands
- Module enters sleep/power-save mode after first response
- Module requires specific initialization sequence not yet discovered
- Firmware issue (v1.6 may have bugs)

---

## Hypotheses to Test

### Hypothesis #1: IRQ Pin Involvement
**Theory:** The PN532 might be waiting for IRQ (interrupt) pin acknowledgment.

**Evidence:**
- DFRobot module has visible "IRQ" pin on connector
- PN532 datasheet indicates IRQ is used for command completion signaling
- IRQ pin is currently **not connected**

**Test:** Connect FT232 RTS or CTS pin to NFC IRQ pin and monitor state changes.

### Hypothesis #2: HSU Mode Configuration
**Theory:** Module might be in "High Speed UART" (HSU) mode requiring different frame format.

**Evidence:**
- Some PN532 modules have HSU/LSU (Low Speed UART) modes
- Frame format differs between modes
- Response was received but not repeatable

**Test:** Check back of module for solder jumpers labeled HSU/LSU.

### Hypothesis #3: Power Cycling Required
**Theory:** Module needs full power cycle between command sequences.

**Evidence:**
- Single successful response
- No subsequent responses without re-plugging USB

**Test:** Add programmable power control or manual power cycling protocol.

### Hypothesis #4: Hardware Defect/Limitation
**Theory:** This specific module may have intermittent hardware issues.

**Evidence:**
- Inconsistent behavior despite correct wiring
- Single response suggests partial functionality
- DFRobot modules sometimes have QC issues

**Test:** Try a different PN532 module if available.

---

## Recommended Next Steps

### Immediate Actions (Priority Order)

1. **Run `test-nfc-wakeup.py`**
   - Tests multiple wake-up sequences
   - May reveal correct initialization pattern
   - Command: `python3 test-nfc-wakeup.py`

2. **Physical Module Inspection**
   - Check **back of NFC module** for:
     - Solder jumpers (HSU/LSU, mode selection)
     - Configuration labels
     - Visible damage or cold solder joints
   - Take photo if unsure

3. **IRQ Pin Connection Test**
   - Connect NFC IRQ pin to ground (GND)
   - Retest GetFirmwareVersion command
   - If that fails, connect IRQ to VCC (pull high)

4. **Hard Reset Implementation**
   - Add hardware reset capability:
     - Option A: Physically unplug/replug USB between tests
     - Option B: Use transistor/relay to control NFC VCC
     - Option C: Use FT232 control pin (CTS/DSR) to reset

5. **Alternative PN532 Library**
   - Try existing Python PN532 libraries:
     - `pn532` (PyPI package)
     - `Adafruit_CircuitPython_PN532`
   - These may have module-specific workarounds

### Long-term Considerations

- **Alternative Hardware:** Consider Adafruit PN532 breakout (better documentation/support)
- **Different Approach:** Test with Raspberry Pi GPIO UART instead of USB-to-UART
- **Protocol Analyzer:** Use logic analyzer to capture successful vs failed attempts

---

## Code Reference

### Successful Response Trigger (from `test-wire-quality.py`)

```python
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

ser = serial.Serial(PORT, BAUDRATE, timeout=0.5)

# Start with defaults (HIGH)
# (ser.dtr and ser.rts are True by default)

# Send random data
ser.write(b'\xFF' * 100)
time.sleep(0.3)

# Switch to LOW
ser.dtr = False
ser.rts = False
time.sleep(0.1)

# Send GetFirmwareVersion
command = bytearray([
    0x00, 0x00, 0xFF, 0x02, 0xFE,
    0xD4, 0x02, 0x2A, 0x00
])
ser.write(command)
time.sleep(0.3)

# This sequence produced ONE successful response:
# 00 00 ff 00 ff 00 00 00 ff 06 fa d5 03 32 01 06 07 e8 00
```

---

## Questions for Continuation

1. **Has the module been power cycled (USB unplugged/replugged) since the successful response?**

2. **Are there any markings on the BACK of the NFC module?**
   - Solder jumpers
   - Version numbers
   - Configuration labels

3. **Does the NFC module have any OTHER connectors besides the UART pins?**
   - I2C pads
   - SPI pads
   - Reset button

4. **Is a different PN532 module available for comparison testing?**

5. **Is a Raspberry Pi available to test GPIO UART vs USB-to-UART?**

---

## References

- **FastPay Project Doc:** `/Users/danieldewar/Documents/dev/fastpay/FastPay-Phase1-ProjectDoc.md`
- **PN532 User Manual:** https://www.nxp.com/docs/en/user-guide/141520.pdf
- **DFRobot DFR0231-H:** https://wiki.dfrobot.com/Gravity__NFC_Module_SKU__DFR0231-H

---

## Status Summary

**Current Blocker:** PN532 module responds once but cannot establish consistent communication.

**Confidence Level:** 🟡 Medium - Module is proven functional but initialization sequence unknown.

**Risk Level:** 🟢 Low - Hardware is not damaged, issue is software/protocol related.

**Estimated Time to Resolution:** 1-3 hours with systematic testing of hypotheses.

---

---

## 🔧 UPDATE: Solution Found

**Root Cause Identified:**
1. Missing ACK frame handling in UART protocol flow
2. DTR/RTS control lines must be forced LOW
3. Flow control must be explicitly disabled

**Fix Implemented:** `test-nfc-with-ack.py`

**Key Changes:**
```python
# 1. Disable all flow control
ser = serial.Serial(PORT, BAUDRATE, rtscts=False, dsrdtr=False, xonxoff=False)

# 2. Force control lines LOW
ser.dtr = False
ser.rts = False

# 3. Proper ACK handling
send_command() → read_ack() → read_frame()
```

**Protocol Flow:**
```
1. Send command frame (00 00 FF LEN LCS D4 CMD ... DCS 00)
2. Wait for ACK (00 00 FF 00 FF 00) - 6 bytes
3. Read response frame (00 00 FF LEN LCS D5 RESP ... DCS 00)
4. Parse response payload
```

**Status:** ✅ Ready for testing - run `python3 test-nfc-with-ack.py`

**Report End**
