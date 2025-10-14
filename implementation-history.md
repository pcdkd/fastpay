# FastPay Implementation History

This document tracks detailed implementation decisions, debugging sessions, and hardware setup for the FastPay project.

---

## Phase 1: Hardware Setup (Week 1)

### Desktop Development Environment

**Hardware Components:**
- **NFC Module:** DFRobot DFR0231-H Gravity (PN532 chip, firmware v1.6)
- **USB-to-UART:** Mayina FT232R (VID:PID 0403:6001)
- **Serial Port:** `/dev/tty.usbserial-ABSCDY4Z` (macOS)
- **Platform:** macOS (Darwin 24.6.0), Python 3.12.x

**Wiring Configuration:**
```
FT232 Mayina → DFRobot NFC Module
===================================
VCC (5V)     → VCC       [RED wire]
GND          → GND       [BLACK wire]
TXD          → C/R       [BLUE wire]  ✅ TX/RX crossover
RXD          → D/T       [GREEN wire] ✅ TX/RX crossover
```

### Critical Debugging Session (Oct 5, 2025)

**Initial Problem:** PN532 module not responding to commands

**Debugging Timeline:**

1. **Serial Port Test** (`test-serial.py`) - ✅ PASSED
   - FT232 detected successfully
   - Port opens without errors at 115200 baud

2. **Basic NFC Communication** (`test-nfc.py`) - ❌ FAILED
   - No response from GetFirmwareVersion command
   - Module power LED confirmed on (hardware powered)

3. **Comprehensive Diagnostics** (`test-nfc-debug.py`) - ❌ FAILED
   - Tested multiple frame formats
   - Tried different timing sequences
   - No ACK or response frames received

4. **Baudrate Scan** (`test-baudrates.py`) - ❌ FAILED
   - Tested: 9600, 19200, 38400, 57600, 115200
   - No response at any baudrate

5. **BREAKTHROUGH** (`test-wire-quality.py`) - ⚠️ PARTIAL SUCCESS
   - Module responded ONCE when DTR/RTS were toggled from HIGH to LOW
   - **Received firmware response:** `00 00 ff 00 ff 00 00 00 ff 06 fa d5 03 32 01 06 07 e8 00`
   - **Decoded:** PN532 firmware v1.6, IC type 0x32, revision 7
   - **Key insight:** DTR=False, RTS=False required for this FT232 module

6. **ACK Protocol Implementation** (`test-nfc-with-ack.py`) - ⚠️ INCONSISTENT
   - Implemented proper UART protocol flow:
     - Send command → Read ACK (6 bytes) → Read response frame
   - Proper flow control disabled (rtscts=False, dsrdtr=False, xonxoff=False)
   - DTR/RTS forced LOW
   - Still inconsistent responses

**Root Cause Analysis:**

The PN532 UART protocol requires:
1. **Control lines LOW:** DTR=False, RTS=False (Python serial defaults to HIGH)
2. **ACK frame handling:** Protocol expects ACK before response frame
3. **No flow control:** All hardware/software flow control must be disabled
4. **Correct timing:** Small delays required for signal stabilization

**Solution: Adafruit Library**

Instead of raw protocol implementation, switched to battle-tested library:

```python
import serial
from adafruit_pn532.uart import PN532_UART

uart = serial.Serial(PORT, baudrate=115200, timeout=1)
uart.dtr = False  # CRITICAL: Force DTR LOW
uart.rts = False  # CRITICAL: Force RTS LOW
time.sleep(0.2)   # Allow signals to stabilize

pn532 = PN532_UART(uart, debug=False)
ic, ver, rev, support = pn532.firmware_version  # ✅ Works immediately!
```

**Result:** Module detected perfectly on first try with Adafruit library

**Time Investment:** ~2 hours of systematic debugging

**Key Lesson:** Use proven libraries for complex protocols instead of raw implementations

### Phone Tap Detection (Oct 5, 2025)

**Test:** `detect-phone-tap.py`

Successfully detected 5 phone taps with different UIDs:
- Tap #1: 086AF124
- Tap #2: 08349FB5
- Tap #3: 08055B46
- Tap #4: 08BB33FB
- Tap #5: 08C2E70B

**Findings:**
- PN532 hardware interaction confirmed working
- Phone NFC changes UID on each tap (privacy feature)
- Detection latency: <100ms
- Reliable detection at 3-5cm range

---

## Phase 1: NFC Writing Experiments

### Attempt 1: Simple Raw Data (`write-simple-payment.py`)

**Goal:** Write raw JSON payment data to NTAG tag

**Payment Payload:**
```json
{
  "v": 1,
  "addr": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "merchant": "Alice's Coffee",
  "amt": "5.00 USDC",
  "item": "Latte",
  "time": 1728404791
}
```

**Approach:**
- Write raw JSON bytes starting at page 4 (NTAG user memory)
- 4 bytes per page
- No NDEF formatting

**Result:** Data written but phone couldn't read (not NDEF formatted)

### Attempt 2: Full Payment Request (`write-full-payment.py`)

**Goal:** Write complete FastPay payment request with all fields

**Payload Size:** 225 bytes (exceeds NTAG213 144-byte limit)

**Result:**
- Data truncated to 144 bytes
- Some page writes succeeded (✅)
- Many checksum errors (⚠️)
- Inconsistent write reliability

**Observation:** User was tapping PHONE (reader mode), not physical NFC tags

### Attempt 3: NDEF Formatted Data (`write-ndef-formatted.py`)

**Goal:** Write NDEF-formatted Text Record that phones can parse

**NDEF Format:**
```
Header:  0xD1 (MB=1, ME=1, SR=1, TNF=Well-known)
Type:    0x01 (length) + 'T' (Text record)
Payload: 0x02 + 'en' (language) + JSON text
```

**TLV Wrapper:**
```
0x03        - NDEF Message TLV
[length]    - Payload size
[NDEF data] - The actual record
0xFE        - Terminator TLV
```

**Capability Container (Page 3):**
```
0xE1  - Magic number
0x10  - Version 1.0
0x12  - Memory size (144 bytes for NTAG213)
0x00  - Full read/write access
```

**Result:**
- CC page write failed with checksum error 132
- Library rejected invalid checksum
- Could not establish proper NDEF formatting

### Attempt 4: Smart NDEF Writer (`write-ndef-smart.py`)

**Goal:** Check if tag already NDEF formatted, skip CC if needed

**Logic:**
1. Read page 3 (CC)
2. If CC[0] == 0xE1, tag already formatted → skip CC write
3. If not formatted, try to write CC
4. Write data pages regardless of CC success

**Result:**
- Only 7/30 page writes succeeded
- Most pages failed with checksum errors
- Inconsistent write behavior

**Final Realization:** User doesn't have physical NTAG tags yet, was tapping phone in reader mode

---

## Phase 1: Card Emulation Investigation (Oct 8, 2025)

### Context: Exploring NFC Approaches

**Initial Exploration:** Testing card emulation as potential approach for NFC communication

**Finding:** After extensive testing, card emulation is not viable for FastPay production. See Phase 1 conclusion below.

### Attempt 1: Adafruit Library (`card-emulation-simple.py`)

**Approach:** Use Adafruit library's TgInitAsTarget method

**Code:**
```python
response = pn532.TgInitAsTarget(
    mode=0x05,  # PICC only + Passive
    mifare_params=mifare_params,
    felica_params=felica_params,
    nfcid3t=nfcid3t,
    timeout=1
)
```

**Result:** ❌ AttributeError: 'PN532_UART' object has no attribute 'TgInitAsTarget'

**Finding:** Adafruit CircuitPython PN532 library doesn't implement card emulation methods

### Attempt 2: Raw PN532 Commands (`card-emulation-raw.py`)

**Approach:** Implement card emulation using raw PN532 protocol commands

**PN532 Commands Implemented:**

1. **TgInitAsTarget (0x8C)** - Initialize as NFC target
   ```python
   params = bytearray()
   params.append(0x05)  # Mode: PICC only + Passive
   params.extend([0x04, 0x00])  # SENS_RES (Type 4 Tag)
   params.extend([0x12, 0x34, 0x56])  # NFCID1t (UID)
   params.append(0x40)  # SEL_RES (ISO14443-4 compliant)
   params.extend([...])  # FeliCa params (required but unused)
   params.extend([...])  # NFCID3t
   params.append(0x00)  # General bytes length
   params.append(0x00)  # Historical bytes length
   ```

2. **TgGetData (0x86)** - Receive data from phone (initiator)
   ```python
   def tg_get_data(ser):
       return send_command(ser, 0x86, [])
   ```

3. **TgSetData (0x8E)** - Send data to phone
   ```python
   def tg_set_data(ser, data):
       return send_command(ser, 0x8E, list(data))
   ```

**ISO-DEP APDU Command Handling:**

Phone sends APDU commands to Type 4 Tags:

- **SELECT (0xA4):** Select application/file
  - Response: `90 00` (success)

- **READ BINARY (0xB0):** Read file contents
  - Response: `[NDEF data...] 90 00`

- **Unknown commands:**
  - Response: `6A 82` (file not found/not supported)

**Payment Data:**
```json
{
  "v": 1,
  "merchant": "Alice's Coffee",
  "amount": "5.00 USDC",
  "item": "Latte",
  "addr": "0x742d...bEb",
  "time": 1728415455
}
```

**NDEF Encoding:**
```python
def create_ndef_text(text):
    text_bytes = text.encode('utf-8')
    record = bytearray()
    record.append(0xD1)  # Header
    record.append(0x01)  # Type length
    record.append(len(text_bytes) + 3)  # Payload length
    record.append(0x54)  # Type: T
    record.append(0x02)  # Language length
    record.extend(b'en')
    record.extend(text_bytes)
    return bytes(record)
```

**Main Loop:**
```python
while True:
    # Wait for phone tap (blocks until tap or timeout)
    response = tg_init_as_target(ser, ndef_msg)

    if response:
        # Phone detected! Handle ISO-DEP session
        while session_active:
            # Get command from phone
            cmd = tg_get_data(ser)

            # Parse APDU
            if cmd[1] == 0xA4:  # SELECT
                tg_set_data(ser, bytes([0x90, 0x00]))
            elif cmd[1] == 0xB0:  # READ BINARY
                tg_set_data(ser, ndef_msg[:50] + bytes([0x90, 0x00]))
            else:
                tg_set_data(ser, bytes([0x6A, 0x82]))
```

**Status:** ✅ Implementation complete, ready for testing

**Next Step:** User needs to run `python3 test/card-emulation-raw.py` and tap phone

---

## Implementation Decisions

### Why Adafruit Library (Not Raw Protocol)

**Decision:** Use `adafruit-circuitpython-pn532` for PN532 communication

**Rationale:**
- Raw UART protocol is complex (ACK frames, checksums, timing)
- 2 hours of debugging raw implementation vs instant success with library
- Library handles edge cases and module-specific quirks
- Proven reliability across different PN532 modules
- Active maintenance and community support

**Trade-off:** Library doesn't support card emulation, requiring raw commands for TgInitAsTarget

**Solution:** Hybrid approach - Use library for initialization, raw commands for card emulation

### Architecture Decision: Reader Mode (Not Card Emulation)

**Decision:** PN532 acts as reader to detect phone taps, payment data flows via Coinbase Commerce API

**Rationale:**
- Customer needs internet to broadcast to Base L2 blockchain anyway
- Coinbase Commerce provides proven hosted checkout
- No card emulation complexity (UART timing issues)
- No physical tags needed
- Tap just provides UX convenience (alternative to QR scan)
- Scalable to high transaction volume

**Implementation:**
- PN532 in reader mode detects ISO14443A devices
- Extracts UID from tapped phone
- Associates tap with pending Coinbase Commerce charge
- Customer completes payment via hosted checkout
- Webhook confirms payment to terminal

### DTR/RTS Control Lines

**Decision:** Always set DTR=False, RTS=False after opening serial port

**Rationale:**
- Python serial library defaults to DTR=True, RTS=True (HIGH)
- Some FT232 modules (like Mayina) use these for flow control
- PN532 module misinterprets HIGH signals as flow control assertion
- Setting LOW disables hardware flow control, allowing communication

**Platform Specificity:**
- Required for: USB-to-UART converters (FT232, CP2102, CH340)
- Not required for: Raspberry Pi GPIO UART (direct connection)
- Environment flag: `NFC_DTR_LOW=true` for conditional application

---

## Test Scripts Reference

### Working Scripts (Production-Ready)

- **test-adafruit-pn532.py** - Firmware detection and SAM configuration
- **detect-phone-tap.py** - Phone tap detection and UID reading (PRODUCTION APPROACH)

### Debug/Development Scripts

- **test-serial.py** - Serial port verification
- **test-nfc.py** - Raw protocol implementation (reference)
- **test-nfc-debug.py** - Comprehensive diagnostics
- **test-baudrates.py** - Baudrate scanning
- **test-wire-quality.py** - Control signal testing (found DTR/RTS issue)
- **test-nfc-with-ack.py** - ACK frame handling implementation
- **test-nfc-wakeup.py** - Wake-up sequence testing

### Experimental Scripts (Not Used in Production)

**Card Emulation Experiments:**
- **card-emulation-hybrid.py** - nfcpy card emulation attempt
- **card-emulation-simple.py** - Adafruit library emulation attempt
- **card-emulation-raw.py** - Raw PN532 command emulation attempt

**Tag Writing Experiments:**
- **write-simple-payment.py** - Raw data writing
- **write-full-payment.py** - Complete payment request
- **write-ndef-formatted.py** - NDEF format with CC
- **write-ndef-smart.py** - Smart NDEF detection and writing
- **write-payment-request.py** - Structured payment data
- **write-payment-tag.py** - NTAG tag writing (hardware validation)
- **write-to-tag.py** - Basic tag writing

**Note:** These scripts proved the hardware works but are not used in production. FastPay uses reader mode, not card emulation or tag writing.

---

## Hardware Platform Notes

### macOS Desktop Development

**Serial Port:** `/dev/tty.usbserial-ABSCDY4Z` (FT232 detected via VID:PID 0403:6001)

**Requirements:**
- DTR/RTS must be LOW
- No driver installation needed (macOS built-in FTDI support)
- Permissions: Usually no sudo required

**Testing Commands:**
```bash
ls /dev/tty.usbserial*  # List USB serial devices
python3 test/test-adafruit-pn532.py  # Quick verification
```

### Raspberry Pi Deployment (Future)

**Serial Port:** `/dev/ttyAMA0` (GPIO UART)

**Requirements:**
- Disable serial console in `/boot/config.txt`
- Enable UART: `enable_uart=1`
- DTR/RTS not applicable (direct GPIO connection)
- Add user to dialout group: `sudo usermod -a -G dialout $USER`

**Config Changes:**
```bash
# /boot/config.txt
enable_uart=1
dtoverlay=disable-bt  # Disable Bluetooth (conflicts with UART)
```

### Code Portability

**Platform-agnostic NFC bridge:**
```python
import os
import serial
from adafruit_pn532.uart import PN532_UART

# Platform detection
if os.path.exists('/dev/ttyAMA0'):
    PORT = '/dev/ttyAMA0'  # Raspberry Pi
    NEEDS_DTR_RTS_FIX = False
elif os.path.exists('/dev/tty.usbserial-ABSCDY4Z'):
    PORT = '/dev/tty.usbserial-ABSCDY4Z'  # macOS dev
    NEEDS_DTR_RTS_FIX = True
else:
    PORT = os.getenv('NFC_PORT', '/dev/ttyUSB0')  # Linux USB
    NEEDS_DTR_RTS_FIX = True

uart = serial.Serial(PORT, 115200, timeout=1)

if NEEDS_DTR_RTS_FIX:
    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)

pn532 = PN532_UART(uart)
```

---

## Phase 1 Conclusion: Reader Mode Architecture Selected

### Final Architecture Decision (Week 2)

After extensive testing of three approaches:
1. **Card Emulation** - ❌ Not viable (PN532 over UART too slow for ISO-DEP timing)
2. **Physical Tag Writing** - ✅ Hardware validated but not needed for production
3. **Reader Mode** - ✅ SELECTED for production

**Why Reader Mode:**
- Customers need internet for blockchain anyway (Base L2 settlement)
- Coinbase Commerce provides proven payment infrastructure
- NFC tap is UX convenience (alternative to QR code)
- No card emulation complexity
- Scalable and reliable

### Production Architecture

```
Payment Flow:
1. Terminal creates Coinbase Commerce charge
2. Displays QR code + "Tap to Pay" prompt
3. PN532 reader detects phone tap (extracts UID)
4. Associates tap with pending charge
5. Customer opens wallet, sees charge (via QR or deep link)
6. Customer approves transaction
7. Broadcasts to Base L2
8. Webhook confirms payment to terminal
```

## Next Implementation Steps

### Week 2: Build Terminal Software

1. **Create terminal/ directory structure**
   - Node.js business logic
   - Python NFC reader bridge
   - IPC via stdin/stdout

2. **Coinbase Commerce Integration**
   - Charge creation API
   - Webhook endpoint
   - Payment confirmation

3. **Reader Mode NFC Bridge**
   - Port `detect-phone-tap.py` to production
   - Add JSON IPC output
   - Implement tap debouncing

4. **Test End-to-End Flow**
   - Create charge → Display QR → Detect tap → Verify payment

### Week 3: Commerce Payments Escrow (Optional)

5. **Escrow Protocol Integration** - If bypassing Coinbase hosted checkout
6. **Direct Blockchain Monitoring** - Base L2 event monitoring
7. **Custom Contract Deployment** - Base Sepolia testnet

### Week 4: Raspberry Pi & Pilot Prep

8. **Raspberry Pi Migration** - Same code, change NFC_PORT
9. **Merchant Pilot Prep** - Packaging, documentation
10. **Video Demo** - Record end-to-end payment

---

**Document Status:** Living document, updated as implementation progresses

**Last Updated:** October 14, 2025 - Architecture finalized: Reader Mode selected
