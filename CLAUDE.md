# CLAUDE.md

This file provides essential guidance to Claude Code when working with the FastPay codebase.

## Quick Start - Where We Are Now

**Current Status:** Week 2 of Phase 1 - Hardware validated, implementing reader mode architecture

**What Works:**
- ✅ NFC hardware (PN532 module) communicating via USB-UART
- ✅ Phone tap detection and UID reading (`test/detect-phone-tap.py`)
- ✅ Reader mode fully functional with Adafruit library
- ✅ Tag writing validates hardware works (proof of concept)

**Critical Architecture Decision:**
FastPay uses **READER MODE** - PN532 detects customer phone taps, payment data flows via API/QR.

**Why Reader Mode (Not Card Emulation or Physical Tags):**
- ✅ Merchants have reliable internet (coffee shops, retail)
- ✅ Customer signing requires network emission (Base L2 blockchain)
- ✅ Leverages Coinbase Commerce hosted checkout
- ✅ No physical tag consumables or logistics
- ✅ Fast tap detection without tag writing latency
- ✅ Can handle high transaction volume

**Card Emulation Status:**
NOT VIABLE with PN532 over UART. See `test/CARD-EMULATION-FINDINGS.md` for technical details.

**What's Next:**
1. Create `terminal/` directory structure
2. Build Node.js payment request layer (Coinbase Commerce API integration)
3. Implement reader mode: PN532 detects tap → associates with pending charge
4. Add IPC between Node.js and Python (stdin/stdout for tap detection)
5. Test full payment flow: Create charge → Display QR → Detect tap → Customer pays → Confirm on-chain

**Key Files to Reference:**
- `test/detect-phone-tap.py` - WORKING: Reader mode tap detection (production ready)
- `test/CARD-EMULATION-FINDINGS.md` - Why card emulation failed (technical investigation)
- `test/write-payment-tag.py` - Hardware validation (proves reader/writer works)
- `test/SETUP-SUCCESS.md` - Hardware setup and wiring
- `test/NEXT-STEPS.md` - Detailed implementation roadmap
- `FastPay-Phase1-ProjectDoc.md` - Complete architecture spec (gitignored but critical reference)

## Project Overview

FastPay is an NFC-based cryptocurrency payment terminal that enables tap-to-pay crypto payments in under 10 seconds. The terminal inverts the traditional crypto flow from "push" (customer-initiated) to "pull" (merchant-initiated) to match credit card UX.

**Current Status:** Phase 1 - Hardware setup complete, reader mode validated, ready to build terminal software

**Tech Stack:**
- **Terminal:** Node.js v20.x (business logic, Coinbase Commerce API), Python 3.11+ (NFC reader bridge)
- **Blockchain:** Base L2, USDC token
- **NFC Hardware:** PN532 module (UART), Adafruit CircuitPython library in reader mode
- **Payment Flow:** Coinbase Commerce hosted checkout (customer pays via QR or wallet app)
- **Customer Experience:** Scan QR OR tap phone (both open same payment page)
- **Smart Contracts:** Coinbase Commerce Payments (Week 3)

## Architecture Principles

### Critical Design Pattern: Reader Mode Architecture

The NFC module **only detects taps** - it has ZERO payment logic. This is intentional:

```
Layer 1: NFC TAP DETECTION (Python + PN532)
├── Continuously scans for ISO14443A devices (phones)
├── Reports UID when device detected
├── NO understanding of blockchain, payments, or charges
└── Just detects physical taps (works on laptop, Pi, ESP32, custom PCB)

Layer 2: PAYMENT ORCHESTRATION (Node.js)
├── Creates charges via Coinbase Commerce API
├── Displays QR code + "Tap to Pay" prompt
├── Receives tap events from NFC layer
├── Associates tap UID with pending charge
└── Monitors blockchain for payment confirmation

Layer 3: PAYMENT PROCESSING (External)
├── Customer wallet app (opened via QR or NFC deep link)
├── Coinbase Commerce hosted checkout
├── Base L2 blockchain settlement
└── Webhook confirms payment to terminal
```

**Why this matters:**
- NFC layer is simple and portable (just tap detection)
- Payment logic lives in Node.js where it's testable
- Can swap NFC for other tap technologies (BLE, UWB)
- Terminal works even if NFC reader disconnects (QR fallback)

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
python3 detect-phone-tap.py           # ✅ PRODUCTION READY: Reader mode tap detection

# Hardware validation tests (prove reader/writer works)
python3 write-payment-tag.py          # Validates PN532 can write to tags (not used in production)

# Card emulation experiments (DEPRECATED - see CARD-EMULATION-FINDINGS.md)
# These don't work reliably with PN532+UART, kept for reference only
# python3 card-emulation-hybrid.py
# python3 card-emulation-simple.py
# python3 card-emulation-raw.py

# Legacy experiments (kept for reference)
python3 write-payment-request.py      # Early tag writing experiments
python3 write-simple-payment.py       # Simple payload tests

# Advanced diagnostics
python3 test-serial.py                # Serial port detection and verification
python3 test-wire-quality.py          # Control signal testing (DTR/RTS)
python3 test-baudrates.py             # Baudrate scanning
```

### Production NFC Reader Script

The working reader mode script (`test/detect-phone-tap.py`) will be ported to `terminal/scripts/nfc_reader.py` with these enhancements:

```python
# Production reader features (to be implemented):
- Continuous scanning loop
- JSON output via stdout for Node.js IPC
- Graceful error handling and reconnection
- UID deduplication (ignore rapid re-taps)
- Timeout configuration via environment variable
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
NFC_TAP_DEBOUNCE_MS=1000  # Ignore rapid re-taps within 1 second

# Coinbase Commerce (get API key from https://commerce.coinbase.com/)
COINBASE_COMMERCE_API_KEY=your_api_key_here
COINBASE_WEBHOOK_SECRET=your_webhook_secret_here

# Blockchain (Base Mainnet - Coinbase Commerce handles this)
BASE_RPC_URL=https://mainnet.base.org  # Optional: for direct on-chain monitoring
CHAIN_ID=8453
USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Merchant
MERCHANT_NAME="Test Merchant"
TERMINAL_ID=terminal_001

# Server
PORT=3000  # For webhook endpoint
```

## Payment Flow Implementation

### Current Status: Hardware Validated, Reader Mode Ready

The NFC hardware layer is working and tested with `test/detect-phone-tap.py`. This script demonstrates:
- PN532 initialization with Adafruit library (reader mode)
- ISO14443A device detection (phones, payment cards)
- UID extraction from detected devices
- Continuous scanning with timeout handling

**IMPORTANT:** This is reader mode - PN532 detects taps, payment data flows via Coinbase Commerce API.

**Next step:** Build the Node.js terminal layer that creates charges via Coinbase Commerce and associates taps with pending charges.

### Week 1-2: Simple USDC Transfers via Coinbase Commerce (PLANNED)

```javascript
// When terminal/src/ is created:
1. Merchant enters sale amount in terminal
2. Node.js creates Coinbase Commerce charge via API
   → Returns: charge.id, charge.hosted_url, charge.addresses.base
3. Terminal displays:
   - QR code with charge.hosted_url
   - "Scan QR OR Tap Phone" prompt
4. Python NFC reader continuously scans for taps
5. Customer taps phone → PN532 detects UID
6. Python reports tap to Node.js via stdout (JSON IPC)
7. Node.js associates tap UID with pending charge.id
8. Terminal shows: "✅ Tap detected! Complete payment on your phone"
9. Customer's wallet app opens charge.hosted_url (or was already scanned)
10. Customer approves → USDC.transfer(charge.addresses.base, amount)
11. Coinbase webhook fires → Node.js confirms payment
12. Terminal monitors Base L2 for confirmation (optional, webhook is primary)
13. Display "✅ Payment confirmed!" (<10 seconds total)
```

**Reader Mode Workflow:**
- NFC tap is a **convenience** alternative to QR scan
- Both QR and tap lead to same Coinbase Commerce checkout
- Tap provides better UX ("just tap to pay" like credit card)
- Terminal tracks which customer paid via tap UID or webhook metadata

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

## Coinbase Commerce Integration

### Charge Creation

```javascript
// Week 1-2: Create charge via Coinbase Commerce API
const commerce = require('coinbase-commerce-node');
const Client = commerce.Client;

Client.init(process.env.COINBASE_COMMERCE_API_KEY);

const chargeData = {
  name: 'Coffee Purchase',
  description: 'Grande Latte - Terminal #001',
  local_price: {
    amount: '5.00',
    currency: 'USD'
  },
  pricing_type: 'fixed_price',
  metadata: {
    terminal_id: process.env.TERMINAL_ID,
    merchant_name: process.env.MERCHANT_NAME,
    tap_uid: null  // Will be filled when customer taps
  }
};

const charge = await Charge.create(chargeData);

// Returns:
// charge.id - unique charge identifier
// charge.hosted_url - customer payment page
// charge.addresses.base - Base L2 deposit address for USDC
// charge.pricing.usdc.amount - exact USDC amount required
```

### Webhook Handling

```javascript
// Receive payment confirmations from Coinbase Commerce
app.post('/webhooks/coinbase', (req, res) => {
  const signature = req.headers['x-cc-webhook-signature'];
  const isValid = Webhook.verifyEventBody(
    req.rawBody,
    signature,
    process.env.COINBASE_WEBHOOK_SECRET
  );

  if (isValid) {
    const event = req.body;

    if (event.type === 'charge:confirmed') {
      const charge = event.data;
      console.log(`✅ Payment confirmed for charge: ${charge.id}`);
      // Update terminal display: "Payment confirmed!"
    }
  }

  res.sendStatus(200);
});
```

### Alternative: Direct On-Chain Monitoring (Week 3)

For merchants who want to bypass Coinbase webhooks and verify directly on-chain:

```javascript
// Monitor USDC Transfer events on Base L2
const filter = usdcContract.filters.Transfer(
  null,  // from: any
  charge.addresses.base,  // to: charge deposit address
  null   // amount: any
);

provider.on(filter, async (event) => {
  const amount = ethers.formatUnits(event.args.value, 6);  // USDC has 6 decimals
  console.log(`✅ Received ${amount} USDC at ${charge.addresses.base}`);
  // Verify amount matches charge.pricing.usdc.amount
  // Update terminal display
});
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

### Production Approach: Reader Mode

**CRITICAL DECISION (Week 2):** FastPay uses **reader mode** - PN532 detects customer phone taps.

**Why Reader Mode:**
- ✅ Merchants have reliable internet (coffee shops, retail stores)
- ✅ No physical NFC tags or consumables needed
- ✅ Customer signing requires network emission (Base L2 blockchain)
- ✅ Leverages Coinbase Commerce's proven hosted checkout
- ✅ Faster transaction flow (no tag writing latency)
- ✅ Scales to high transaction volume

**Why Card Emulation Failed:**
See `test/CARD-EMULATION-FINDINGS.md` for detailed investigation report. Summary:
- ❌ PN532 over UART too slow for ISO-DEP card emulation timing requirements
- ❌ Adafruit library doesn't expose card emulation methods
- ❌ Complex APDU protocol implementation required
- ❌ IRQ pin handling critical (not exposed via USB-UART)

**Production Solution: Reader Mode**
1. PN532 continuously scans for ISO14443A devices (phones, payment cards)
2. When device detected, extract UID
3. Report tap to Node.js terminal via IPC
4. Terminal associates tap with pending Coinbase Commerce charge
5. Customer completes payment via Coinbase hosted checkout
6. Webhook confirms payment

**Implementation (`test/detect-phone-tap.py` - production ready):**
```python
from adafruit_pn532.uart import PN532_UART

# Initialize PN532 in reader mode
uart = serial.Serial(PORT, 115200, timeout=1)
uart.dtr = False
uart.rts = False
pn532 = PN532_UART(uart, debug=False)
pn532.SAM_configuration()

print("Waiting for tap...")
tap_count = 0

while True:
    # Continuously scan for ISO14443A devices
    uid = pn532.read_passive_target(timeout=0.5)

    if uid:
        tap_count += 1
        uid_hex = ''.join([f'{b:02X}' for b in uid])
        print(f"Tap #{tap_count}: UID={uid_hex}")

        # In production: output JSON to stdout for Node.js
        # print(json.dumps({"event": "tap", "uid": uid_hex}))

        time.sleep(1)  # Debounce (ignore rapid re-taps)
```

**Key Advantages:**
- Instant tap detection (<100ms)
- No physical consumables
- Works with any NFC-enabled phone
- Simple integration (just detect and report)
- No NDEF formatting complexity

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
- ✅ Tag writing tested (`test/write-payment-tag.py`)
- ✅ Phone tap detection verified (reader mode)
- ✅ NDEF message creation and TLV formatting working
- ✅ Card emulation investigated (not viable for PN532+UART)

**Week 2: NOW - Build Terminal Software**
- [ ] Create `terminal/` directory structure
- [ ] Set up Coinbase Commerce API integration (charge creation)
- [ ] Port `test/detect-phone-tap.py` → `terminal/scripts/nfc_reader.py`
- [ ] Add IPC between Node.js and Python (stdin/stdout JSON)
- [ ] Implement charge → tap association logic
- [ ] Set up webhook endpoint for payment confirmations
- [ ] Test end-to-end: Create charge → Display QR → Detect tap → Verify payment

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

### Terminal (Node.js)
- `coinbase-commerce-node@^1.0.4` - Coinbase Commerce API client
- `express@^4.18` - Webhook server
- `dotenv@^16` - Environment configuration
- `qrcode@^1.5` - QR code generation for charge URLs
- `ethers@^6.x` - Optional: Direct blockchain monitoring

### NFC Reader (Python)
- `adafruit-circuitpython-pn532` - PN532 reader mode
- `pyserial` - UART communication

### Customer Experience
- Customer uses **existing wallet app** (MetaMask, Coinbase Wallet, etc.)
- Wallet opens Coinbase Commerce hosted checkout
- No custom app needed for Phase 1

### Contracts (Week 3 - Optional)
- `@coinbase/commerce-payments` - Escrow protocol (if bypassing Coinbase hosted checkout)
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

3. **PN532 not detecting phone taps**
   - Verify phone NFC is enabled (Android: Settings → Connected devices)
   - Run `python3 test/detect-phone-tap.py` to test hardware
   - Ensure phone is placed flat on PN532 module (not just near it)
   - Some phone cases block NFC - try without case
   - Reader range is ~3-5cm, phone must be very close
   - iOS phones only activate NFC when scanning (not passive like Android)

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

7. **Tap detection working but payment not completing**
   - Check Coinbase Commerce webhook is configured correctly
   - Verify charge.hosted_url is accessible (test in browser)
   - Ensure customer's wallet app supports Base L2
   - Check for sufficient USDC balance in customer wallet
   - Review Coinbase Commerce dashboard for charge status

## References

- **implementation-history.md** - Detailed debugging, hardware setup, implementation decisions
- **test/CARD-EMULATION-FINDINGS.md** - Investigation report: why card emulation failed, why tags work
- **test/SETUP-SUCCESS.md** - Verified hardware wiring and configuration
- **test/NEXT-STEPS.md** - Development roadmap and next tasks
- **FastPay-Phase1-ProjectDoc.md** - Complete architectural specification (gitignored, local only)
- **README.md** - Project overview and roadmap
- **test/** - Working hardware test scripts
