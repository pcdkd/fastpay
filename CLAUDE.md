# CLAUDE.md

This file provides essential guidance to Claude Code when working with the FastPay codebase.

## Quick Start - Where We Are Now

**Current Status:** Week 2 of Phase 1 - Hardware testing complete, building terminal software

**What Works:**
- ✅ NFC hardware (PN532 module) communicating via USB-UART
- ✅ Card emulation with phone tap detection (`test/card-emulation-hybrid.py`)
- ✅ NDEF message creation and transmission
- ✅ ISO-DEP APDU protocol handling

**What's Next:**
1. Create `terminal/` directory structure (doesn't exist yet)
2. Build Node.js payment request layer (EIP-712 signing)
3. Copy `test/card-emulation-hybrid.py` → `terminal/scripts/nfc_bridge.py`
4. Add IPC between Node.js and Python (JSON over stdin/stdout)
5. Test full payment flow with phone

**Key Files to Reference:**
- `test/card-emulation-hybrid.py` - Working NFC card emulation (PRODUCTION READY)
- `test/SETUP-SUCCESS.md` - Hardware setup and wiring
- `test/NEXT-STEPS.md` - Detailed implementation roadmap
- `FastPay-Phase1-ProjectDoc.md` - Complete architecture spec (gitignored but critical reference)

## Project Overview

FastPay is an NFC-based cryptocurrency payment terminal that enables tap-to-pay crypto payments in under 10 seconds. The terminal inverts the traditional crypto flow from "push" (customer-initiated) to "pull" (merchant-initiated) to match credit card UX.

**Current Status:** Phase 1 - Hardware setup complete, card emulation working, ready to build terminal software

**Tech Stack:**
- **Terminal:** Node.js v20.x (planned - business logic), Python 3.11+ (NFC hardware bridge)
- **Blockchain:** Base L2, USDC token
- **NFC Hardware:** PN532 module (UART), Adafruit CircuitPython library + raw commands for card emulation
- **Customer App:** React Native test app (Phase 1, planned)
- **Smart Contracts:** Coinbase Commerce Payments (Week 3)

## Architecture Principles

### Critical Design Pattern: Layer Separation

The NFC module has **ZERO blockchain awareness**. This is intentional:

```
Layer 1: NFC COMMUNICATION
├── Reads/writes NDEF messages via 13.56MHz radio
├── NO understanding of blockchain, signatures, or payments
└── Just transmits data (works on laptop, Pi, ESP32, custom PCB)

Layer 2: BUSINESS LOGIC (Node.js)
├── Creates payment requests
├── Signs with merchant wallet (EIP-712)
└── Coordinates between NFC and blockchain

Layer 3: BLOCKCHAIN (Base L2)
├── Settlement layer for transactions
└── Monitored independently of NFC activity
```

**Why this matters:** Enables hardware versatility, testability without blockchain access, and NFC tap works even if RPC is down.

### Development Approach

**Desktop-First:** Develop on Mac/Linux desktop with USB-to-UART converter, then migrate to Raspberry Pi. Same codebase, just change `NFC_PORT` environment variable.

**Current:** macOS desktop with FT232 USB-UART converter (`/dev/tty.usbserial-ABSCDY4Z`)
**Production:** Raspberry Pi GPIO UART (`/dev/ttyAMA0`)

## Current Project Structure

```
fastpay/
├── test/                    # Hardware testing and validation (CURRENT WORK)
│   ├── card-emulation-hybrid.py       # WORKING: Card emulation with hybrid approach
│   ├── detect-phone-tap.py            # WORKING: Phone tap detection
│   ├── test-adafruit-pn532.py         # WORKING: Basic hardware verification
│   ├── write-payment-request.py       # WORKING: Write payment to NFC
│   ├── SETUP-SUCCESS.md               # Hardware setup documentation
│   ├── NEXT-STEPS.md                  # Development roadmap
│   └── DEBUG-REPORT.md                # Troubleshooting history
│
├── CLAUDE.md                # This file - AI assistant guidance
├── README.md                # Project overview
├── implementation-history.md # Detailed implementation decisions
└── FastPay-Phase1-ProjectDoc.md # Complete architectural spec (gitignored)

# PLANNED STRUCTURE (not yet implemented):
├── packages/          # Shared TypeScript types and utilities
├── terminal/          # Merchant terminal (Node.js + Python NFC bridge)
│   ├── src/          # Business logic (wallet, payment, nfc, monitor)
│   └── scripts/      # Production NFC bridge (copy from test/card-emulation-hybrid.py)
├── customer-app/      # React Native test app
└── contracts/         # Week 3: Commerce Payments escrow contracts
```

## Development Commands

### Setup
```bash
# Python dependencies (REQUIRED)
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages

# Node.js dependencies (NOT YET IMPLEMENTED - terminal/ doesn't exist yet)
# npm install  # Will be needed when terminal/ is created
```

### Hardware Testing (test/ directory)
```bash
cd test

# Core hardware verification (run these first)
python3 test-adafruit-pn532.py        # Verify PN532 module responding
python3 detect-phone-tap.py           # Test phone tap detection

# Card emulation (CURRENT FOCUS)
python3 card-emulation-hybrid.py      # Full ISO-DEP card emulation with payment request
python3 card-emulation-simple.py      # Simplified card emulation test
python3 card-emulation-raw.py         # Raw PN532 commands only

# Payment request writing
python3 write-payment-request.py      # Write payment request to NFC tag
python3 write-simple-payment.py       # Write simplified payment data

# Advanced diagnostics
python3 test-serial.py                # Serial port detection and verification
python3 test-wire-quality.py          # Control signal testing (DTR/RTS)
python3 test-baudrates.py             # Baudrate scanning
```

### Running Tests
All tests assume the PN532 module is connected to `/dev/tty.usbserial-ABSCDY4Z`. If your port is different, edit the `PORT` variable at the top of each test file.

### Environment Configuration

**Current:** No `.env` file needed yet - hardware tests use hardcoded port `/dev/tty.usbserial-ABSCDY4Z`

**When terminal/ is created:** Create `terminal/.env`:
```bash
# NFC Hardware
NFC_PORT=/dev/tty.usbserial-ABSCDY4Z  # macOS desktop with FT232 USB-UART
NFC_BAUD_RATE=115200

# Blockchain (Base Sepolia testnet for development)
BASE_RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
USDC_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e

# Merchant
MERCHANT_PRIVATE_KEY=0x...
MERCHANT_NAME="Test Merchant"
TERMINAL_ID=terminal_001
```

## Payment Flow Implementation

### Current Status: Hardware Testing Complete

The NFC hardware layer is working and tested with `test/card-emulation-hybrid.py`. This script demonstrates:
- PN532 initialization with Adafruit library
- ISO-DEP card emulation with raw PN532 commands
- NDEF message creation and transmission
- Phone tap detection and APDU command handling

**Next step:** Build the Node.js terminal layer that creates signed payment requests and spawns the Python NFC bridge.

### Week 1-2: Simple USDC Transfers (PLANNED)

```javascript
// When terminal/src/ is created:
1. Merchant creates payment request (amount, merchant address)
2. Sign with EIP-712 (merchant wallet)
3. Encode as JSON payload
4. Send to Python NFC bridge via IPC (use card-emulation-hybrid.py as base)
5. Python writes NDEF message to NFC tag emulation
6. Customer taps phone → reads NFC
7. Customer app verifies signature, generates MetaMask deep link
8. Customer approves → USDC.transfer(merchant, amount)
9. Terminal monitors Transfer event on Base L2
10. Display confirmation (<10 seconds total)
```

### Week 3: Commerce Payments Escrow (PLANNED)

```javascript
// Enhanced flow with escrow contract
1-7. Same as above
8. Customer approves → CommercePay.deposit(escrow_params)
9. Funds held in escrow contract
10. Terminal monitors DepositEvent
11. Display "Payment escrowed - refund window active"
12. After settlement window: merchant withdraws OR customer refunds
```

## EIP-712 Payment Request Schema

```javascript
// Weeks 1-2: Direct transfer
const types = {
  PaymentRequest: [
    { name: "merchantAddress", type: "address" },
    { name: "merchantName", type: "string" },
    { name: "tokenAddress", type: "address" },  // USDC
    { name: "amount", type: "uint256" },
    { name: "currency", type: "string" },       // "USD"
    { name: "fiatAmount", type: "string" },     // "5.00"
    { name: "description", type: "string" },
    { name: "nonce", type: "uint256" },
    { name: "expiry", type: "uint256" },
    { name: "terminalId", type: "string" }
  ]
};

// Week 3: Add escrow fields
// { name: "escrowContract", type: "address" },
// { name: "paymentId", type: "bytes32" },
// { name: "settlementWindow", type: "uint256" },
// { name: "metadata", type: "string" }
```

## NFC Hardware Integration

### Critical Configuration

**Library:** `adafruit-circuitpython-pn532` (handles complex UART protocol)

**Control Lines:** DTR and RTS must be set LOW for USB-to-UART converters:
```python
uart = serial.Serial(PORT, 115200, timeout=1)
uart.dtr = False  # Required for FT232/CP2102
uart.rts = False  # Required for FT232/CP2102
time.sleep(0.2)   # Signal stabilization
```

**Platform Ports:**
- macOS/Linux USB: `/dev/tty.usbserial-*` or `/dev/ttyUSB*`
- Raspberry Pi GPIO: `/dev/ttyAMA0`
- Windows: `COM3`, `COM4`, etc.

**Wiring:** TX/RX must cross (Module TX → Converter RX, Module RX → Converter TX)

### Production Approach: Tag Writing (NOT Card Emulation)

**CRITICAL FINDING (Week 2):** After extensive testing, card emulation is **NOT VIABLE** for FastPay Phase 1. The production approach uses **physical NFC tag writing**.

**Why Card Emulation Doesn't Work:**
- ❌ Adafruit PN532 library doesn't expose card emulation methods
- ❌ nfcpy card emulation doesn't work with PN532 over UART
- ❌ Raw PN532 commands (TgInitAsTarget) require complex APDU protocol handling
- ❌ Hardware/firmware compatibility issues prevent reliable phone tap detection

**Production Solution: Tag Writing**
✅ PN532 acts as **reader/writer** (not emulated tag)
✅ Write payment request to **physical rewritable NFC tag** (NTAG213/215/216)
✅ Customer taps phone on physical tag to read payment
✅ Rewrite same tag for next transaction

**Implementation (`test/write-payment-tag.py`):**
```python
from adafruit_pn532.uart import PN532_UART

# Initialize PN532
uart = serial.Serial(PORT, 115200, timeout=1)
uart.dtr = False
uart.rts = False
pn532 = PN532_UART(uart, debug=False)
pn532.SAM_configuration()

# Create NDEF Text Record
payment_json = json.dumps(payment, separators=(',', ':'))
ndef_record = create_ndef_text_record(payment_json)

# Wait for tag
uid = pn532.read_passive_target(timeout=10)

# Write NDEF message to tag (NTAG213/215/216)
# Page 4: Capability Container
pn532.ntag2xx_write_block(4, bytes([0xE1, 0x10, 0x12, 0x00]))

# Pages 5+: NDEF TLV structure
ndef_tlv = bytearray([0x03, len(ndef_record)]) + ndef_record + bytearray([0xFE])
page = 5
for i in range(0, len(ndef_tlv), 4):
    chunk = ndef_tlv[i:i+4].ljust(4, b'\x00')
    pn532.ntag2xx_write_block(page, chunk)
    page += 1
```

**Hardware Required:**
- **NTAG213**: 144 bytes usable (~$8 for 10 tags on Amazon)
- **NTAG215**: 504 bytes usable (~$10 for 10 tags) ← RECOMMENDED
- **NTAG216**: 888 bytes usable (~$12 for 10 tags)
- Search: "NTAG215 NFC stickers" or "NFC tags blank NTAG"

**Key Advantages:**
- Fast write: <2 seconds per transaction
- Unlimited rewrites (same tag for all customers)
- Works with existing Adafruit library (no custom protocols)
- Reliable - no card emulation complexity

### ISO-DEP APDU Protocol

When the terminal emulates an NFC Type 4 Tag, phones communicate using ISO-DEP APDU commands:

**APDU Command Structure:**
```
[CLA] [INS] [P1] [P2] [Lc] [Data] [Le]
```

**Key Commands:**

1. **SELECT (INS=0xA4)** - Select application or file
   ```
   Command:  00 A4 04 00 07 D2760000850101 00
   Response: 90 00  (success)
   ```

2. **READ BINARY (INS=0xB0)** - Read file contents
   ```
   Command:  00 B0 00 00 20  (read 32 bytes from offset 0)
   Response: [NDEF data...] 90 00
   ```

3. **UPDATE BINARY (INS=0xD6)** - Write file contents (not used in our read-only flow)

**Response Status Codes:**
- `90 00` - Success
- `6A 82` - File not found / command not supported
- `6A 86` - Incorrect parameters
- `67 00` - Wrong length

**Implementation in card-emulation-raw.py:**
```python
while session_active:
    cmd = tg_get_data(ser)  # Receive APDU from phone

    if cmd[1] == 0xA4:  # SELECT
        tg_set_data(ser, bytes([0x90, 0x00]))
    elif cmd[1] == 0xB0:  # READ BINARY
        offset = (cmd[2] << 8) | cmd[3]
        length = cmd[4]
        data = ndef_message[offset:offset+length]
        tg_set_data(ser, data + bytes([0x90, 0x00]))
    else:
        tg_set_data(ser, bytes([0x6A, 0x82]))  # Not supported
```

**Why this matters:** Understanding ISO-DEP is critical for debugging NFC issues. If phones can't read the terminal, check APDU command/response flow.

## Blockchain Integration (Base L2)

### Network Details

- **Chain ID:** 8453 (Base Mainnet)
- **RPC:** https://mainnet.base.org
- **USDC Token:** 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- **Block Time:** ~2 seconds
- **Confirmation:** 1 block (2-6 seconds)
- **Gas Cost:** ~50k units (direct), ~75k units (escrow)
- **Total Fee:** ~$0.001-0.015 per transaction

### Event Monitoring Pattern

```javascript
// terminal/src/monitor.js
async startMonitoring(paymentRequest, onPaymentReceived) {
  const startTime = Date.now();

  // Week 1-2: Monitor Transfer events
  const filter = usdcContract.filters.Transfer(
    null,  // from: any
    paymentRequest.merchantAddress,  // to: merchant
    paymentRequest.amount
  );

  // Week 3: Monitor DepositEvent from Commerce Payments
  const escrowFilter = commerceContract.filters.DepositEvent(
    paymentRequest.paymentId,
    null,  // from: any
    paymentRequest.amount
  );

  provider.on(filter, (event) => {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
    onPaymentReceived({ success: true, elapsed, txHash: event.transactionHash });
  });
}
```

## Phase Roadmap

### Phase 1 (Weeks 1-4): POC Validation

**Week 1 Status: ✅ COMPLETE**
- ✅ Hardware setup (PN532 + FT232 USB-UART)
- ✅ NFC communication working (Adafruit library)
- ✅ Card emulation tested (`test/card-emulation-hybrid.py`)
- ✅ Phone tap detection verified
- ✅ NDEF message creation working

**Week 2: NOW - Build Terminal Software**
- [ ] Create `terminal/` directory structure
- [ ] Implement Node.js payment request creation (EIP-712 signing)
- [ ] Copy `test/card-emulation-hybrid.py` → `terminal/scripts/nfc_bridge.py`
- [ ] Add IPC between Node.js and Python (stdin/stdout JSON)
- [ ] Test end-to-end: payment request → NFC → phone reads

**Week 3: Commerce Payments Integration**
- [ ] Integrate Commerce Payments escrow protocol
- [ ] Deploy test contracts to Base Sepolia
- [ ] Update payment schema with escrow fields
- [ ] Implement blockchain monitoring for DepositEvent

**Week 4: Raspberry Pi Migration**
- [ ] Test on Raspberry Pi (change `NFC_PORT` to `/dev/ttyAMA0`)
- [ ] Create systemd service for terminal auto-start
- [ ] Merchant pilot preparation
- [ ] Video demo for stakeholder validation

**Success Criteria:**
- End-to-end payment in <10 seconds
- NFC read reliability >95%
- Works on both macOS desktop and Raspberry Pi

### Phase 2+ (Deferred Features)
- EIP-4337 gas sponsorship (merchant pays gas)
- Production companion app (WalletConnect support)
- POS system integration
- Multi-merchant deployment

## Key Dependencies

### Terminal
- `ethers@^6.x` - Blockchain interaction, EIP-712 signing
- `serialport` (Node.js) or `pyserial` (Python) - UART communication
- `dotenv` - Environment configuration

### Customer App
- `react-native-nfc-manager` - NFC tag reading
- `@ethersproject/wallet` - Signature verification
- `react-native-deeplinking` - MetaMask deep links

### Contracts (Week 3)
- `@coinbase/commerce-payments` - Escrow protocol
- `hardhat` - Contract testing and deployment

## Common Issues and Solutions

1. **"No module named 'adafruit_pn532'"**
   ```bash
   pip3 install adafruit-circuitpython-pn532 --break-system-packages
   ```

2. **Module not responding / timeout errors**
   - Power cycle: Unplug USB, wait 5 seconds, replug
   - Verify DTR/RTS are set LOW: `uart.dtr = False` and `uart.rts = False`
   - Check serial port: `ls /dev/tty.usbserial*` should show your device
   - Run diagnostic: `python3 test/test-adafruit-pn532.py`

3. **Phone can't read NFC tag**
   - Verify card emulation is running: `python3 test/card-emulation-hybrid.py`
   - Check ISO-DEP APDU responses in debug output
   - Ensure NDEF message is properly formatted (see `create_ndef_text()` in test scripts)
   - Try different phone positions/angles on module

4. **TX/RX wiring issues**
   - Module TX → Converter RX (crossover required)
   - Module RX → Converter TX (crossover required)
   - See `test/SETUP-SUCCESS.md` for verified wiring diagram

5. **Serial port permissions (Linux/Raspberry Pi)**
   - Add user to dialout group: `sudo usermod -a -G dialout $USER`
   - Or use sudo: `sudo python3 test/test-adafruit-pn532.py`

6. **Port changed after reboot**
   - USB-UART adapters may enumerate differently
   - Find new port: `ls /dev/tty.usbserial*` or `ls /dev/ttyUSB*`
   - Update `PORT` variable in test scripts

## References

- **implementation-history.md** - Detailed debugging, hardware setup, implementation decisions
- **FastPay-Phase1-ProjectDoc.md** - Complete architectural specification (local only)
- **README.md** - Project overview and roadmap
- **test/** - Working hardware test scripts and setup documentation
