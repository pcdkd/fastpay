# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Phase 1 vs Phase 2 Architecture

**⚠️ IMPORTANT:** FastPay has two distinct phases with different payment models:

### Phase 1 (CURRENT - What's Built)
- **Payment Model:** Traditional PUSH payments via Coinbase Commerce API
- **NFC Role:** Tap detection only (reader mode) - does NOT transfer transaction data
- **Customer Flow:** Tap phone (optional) → Scan QR code → Open Coinbase Commerce → Approve payment
- **Blockchain:** Customer PUSHES funds to merchant's deposit address (standard crypto payment)
- **Status:** ✅ Implemented in `terminal/` directory, ready for testing

### Phase 2 (FUTURE - Not Yet Built)
- **Payment Model:** TRUE PULL payments via smart contracts
- **NFC Role:** Transfers transaction data to phone (payment request details)
- **Customer Flow:** Tap phone → Transaction appears in wallet → Sign to complete
- **Blockchain:** Smart contract PULLS funds from customer when they sign (merchant-initiated)
- **Status:** ⏳ Documented in `terminal-implementation.md`, planned for Months 2-3

**Key Insight:** Phase 1 is NOT a pull payment model. The "pull" refers only to merchant-initiated UX (merchant creates request first), not blockchain-level pull payments. Phase 2 is where true pull payments happen.

## Project Status

**What's Currently Built:**
- ✅ Terminal software (`terminal/`) - Node.js + Python NFC bridge
- ✅ NFC hardware integration - PN532 reader mode (tap detection only)
- ✅ Coinbase Commerce integration - Charge creation, hosted checkout, webhooks
- ✅ Payment orchestration - QR codes, tap association, payment confirmations

**What's Next:**
1. Configure Coinbase Commerce API key in `terminal/.env`
2. Test first end-to-end payment
3. Deploy to Raspberry Pi (optional)
4. Build Phase 2 smart contracts (future)

**Key Documentation:**
- `terminal/QUICKSTART.md` - Step-by-step setup (start here)
- `terminal/IMPLEMENTATION-SUMMARY.md` - Complete implementation details
- `PAYMENT-INTENT-DECISION.md` - Why Coinbase Commerce for Phase 1
- `test/CARD-EMULATION-FINDINGS.md` - Why card emulation was abandoned

## High-Level Architecture

FastPay is a tap-to-pay crypto payment terminal (merchant-initiated, like credit card terminals).

**Tech Stack:**
- **Terminal:** Node.js v20 (payment orchestration) + Python 3.11+ (NFC hardware bridge)
- **NFC Hardware:** PN532 module (UART), reader mode (tap detection only)
- **Payment Provider:** Coinbase Commerce (charge creation, hosted checkout, webhooks)
- **Blockchain:** Base L2, USDC token
- **Customer App:** Any wallet (MetaMask, Coinbase Wallet, etc.)

## Key Architectural Decisions

### 1. Three-Layer Architecture (Separation of Concerns)

```
Layer 1: NFC TAP DETECTION (Python + PN532)
└── Only detects taps and reports UID - no payment logic

Layer 2: PAYMENT ORCHESTRATION (Node.js)
└── Creates charges, displays QR, associates taps, monitors webhooks

Layer 3: PAYMENT PROCESSING (External)
└── Coinbase Commerce handles checkout, blockchain settlement, webhooks
```

**Why:** NFC layer is portable (no payment coupling), payment logic is testable (Node.js), terminal works even if NFC fails (QR fallback).

### 2. Reader Mode (Not Card Emulation or Physical Tags)

After testing three approaches, reader mode was selected:
- **Card Emulation:** Failed - PN532 UART too slow for ISO-DEP timing (see `test/CARD-EMULATION-FINDINGS.md`)
- **Physical Tags:** Works but unnecessary - customers need internet for blockchain anyway
- **Reader Mode:** ✅ Selected - detects taps, payment via Coinbase Commerce

### 3. Desktop-First Development

Develop on Mac/Linux with USB-UART, deploy to Pi later. Same codebase, just change `NFC_PORT`.
- **Development:** `/dev/tty.usbserial-*` (USB-UART adapter)
- **Production:** `/dev/ttyAMA0` (Raspberry Pi GPIO UART)

## Project Structure

```
fastpay/
├── terminal/                          # ✅ IMPLEMENTED: Terminal software
│   ├── src/
│   │   ├── index.js                   # Main application entry point
│   │   ├── nfc.js                     # NFC bridge (Node.js ↔ Python IPC)
│   │   ├── commerce.js                # Coinbase Commerce API wrapper
│   │   ├── payment.js                 # Charge lifecycle management
│   │   └── webhook.js                 # Webhook server
│   ├── scripts/
│   │   └── nfc_reader.py              # Python NFC hardware bridge
│   ├── config/
│   │   └── index.js                   # Environment configuration
│   ├── package.json
│   ├── .env.example
│   ├── README.md
│   ├── QUICKSTART.md
│   └── IMPLEMENTATION-SUMMARY.md
│
├── test/                              # Hardware validation scripts
│   ├── detect-phone-tap.py            # Original tap detection (basis for terminal NFC)
│   ├── test-adafruit-pn532.py         # Hardware verification
│   ├── SETUP-SUCCESS.md               # Hardware setup guide
│   ├── CARD-EMULATION-FINDINGS.md     # Card emulation investigation
│   └── ...                            # Other diagnostic scripts
│
├── CLAUDE.md                          # This file
├── README.md                          # Project overview
├── PAYMENT-INTENT-DECISION.md         # Phase 1 architecture decision
├── terminal-implementation.md         # Implementation plan + Phase 2 spec
└── implementation-history.md          # Historical debugging notes
```

## Development Commands

### Initial Setup
```bash
# Python dependencies (for NFC hardware)
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages

# Terminal dependencies
cd terminal
npm install

# Configure environment
cp .env.example .env
# Edit .env with your Coinbase Commerce API key and serial port
```

### Running the Terminal
```bash
cd terminal

# Development mode (auto-restart on changes)
npm run dev

# Production mode
npm start
```

### Hardware Testing
```bash
cd test

# Verify PN532 hardware
python3 test-adafruit-pn532.py

# Test tap detection (standalone)
python3 detect-phone-tap.py
```

### Terminal Testing
```bash
# Test NFC reader standalone (without full terminal)
cd terminal
python3 scripts/nfc_reader.py

# Find serial port
ls /dev/tty.usbserial*   # macOS/Linux USB-UART
ls /dev/ttyUSB*          # Linux USB
ls /dev/ttyAMA*          # Raspberry Pi GPIO
```

## Phase 1 Payment Flow (Current Implementation)

```
1. Merchant enters amount → Terminal creates Coinbase Commerce charge
2. Terminal displays QR code (hosted_url)
3. Customer taps phone (optional) → PN532 detects tap, associates with charge
4. Customer scans QR code → Opens Coinbase Commerce checkout in browser
5. Customer selects wallet → Approves payment → PUSHES funds to deposit address
6. Coinbase webhook fires → Terminal shows "Payment Confirmed!"
```

**Time:** <10 seconds total
**NFC Role:** Tap detection only (for UX/tracking) - does NOT transfer payment data
**Fallback:** QR code works even if NFC fails

See `terminal/IMPLEMENTATION-SUMMARY.md` for detailed flow and code examples.

## Terminal Implementation Details

### Key Modules (terminal/src/)

**index.js** - Main application
- State machine: IDLE → WAITING_FOR_PAYMENT → COMPLETED
- Coordinates all services (NFC, Commerce, Webhooks)
- Handles merchant input (sale amount)

**nfc.js** - NFC Bridge (Node.js ↔ Python)
- Spawns Python child process (`scripts/nfc_reader.py`)
- Parses JSON events from stdout (tap, ready, error)
- Auto-restarts Python on crash

**commerce.js** - Coinbase Commerce API
- Creates charges with metadata (terminal_id, tap_uid)
- Verifies webhook signatures

**payment.js** - Charge Lifecycle
- Tracks pending charges (Map-based)
- Associates taps with most recent charge
- Auto-expires charges after 3 minutes
- Generates QR codes

**webhook.js** - Payment Confirmations
- Express server on port 3000
- Handles `charge:confirmed` events
- Emits events for main app

### Python NFC Bridge (terminal/scripts/nfc_reader.py)

**IPC Protocol (stdout JSON):**
```json
{"event": "ready", "firmware": "1.6", "port": "...", "timestamp": ...}
{"event": "tap", "uid": "086AF124", "timestamp": ...}
{"event": "error", "message": "...", "fatal": false, "timestamp": ...}
```

**Key Features:**
- Continuous scanning with debounce (ignores re-taps within 1s)
- Exponential backoff on errors (max 5 retries)
- Graceful shutdown on SIGINT/SIGTERM
- Can run standalone for testing

## NFC Hardware Configuration

**Library:** `adafruit-circuitpython-pn532`

**Critical Fix for USB-UART:** DTR/RTS must be set LOW
```python
uart = serial.Serial(PORT, 115200, timeout=1)
uart.dtr = False  # Required for FT232/CP2102 USB-UART converters
uart.rts = False  # Required for FT232/CP2102 USB-UART converters
time.sleep(0.2)   # Signal stabilization
```

**Wiring:** TX/RX must crossover:
- Module TX → Converter RX
- Module RX → Converter TX

See `test/SETUP-SUCCESS.md` for verified wiring diagram.

## Blockchain (Base L2)

**Phase 1:** Coinbase Commerce handles all blockchain interaction (charge creation, monitoring, confirmations)

**Key Details:**
- Chain ID: 8453 (Base Mainnet)
- Token: USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
- Confirmation: 1 block (~2-6 seconds)
- Gas: Paid by customer via Coinbase Commerce

**Phase 2:** Direct smart contract interaction for pull payments (see `terminal-implementation.md`)

## Phase Roadmap

### Phase 1 (Weeks 1-4): ✅ MOSTLY COMPLETE

**Week 1-2: ✅ DONE**
- ✅ Hardware setup and validation
- ✅ Terminal software implemented (`terminal/`)
- ✅ NFC reader mode integration
- ✅ Coinbase Commerce API integration
- ✅ Webhook endpoint
- ✅ Documentation complete

**Week 3-4: IN PROGRESS**
- [ ] Get Coinbase Commerce API key
- [ ] Configure `terminal/.env`
- [ ] Test first end-to-end payment
- [ ] Deploy to Raspberry Pi (optional)
- [ ] Measure performance (<10s target)

### Phase 2 (Months 2-3): Pull Payment Smart Contracts

**Features:**
- On-chain payment request creation
- True pull payment model (smart contract pulls funds)
- NFC transfers transaction data (not just tap detection)
- Customer signs to become counterparty
- Bypasses Coinbase Commerce for settlement

See `terminal-implementation.md` for detailed Phase 2 architecture and smart contract spec.

## Key Dependencies

**Node.js:** express, qrcode, dotenv, axios (see `terminal/package.json`)
**Python:** adafruit-circuitpython-pn532, pyserial
**External Services:** Coinbase Commerce API, Base L2 RPC (via Commerce)
**Customer:** Any wallet app (MetaMask, Coinbase Wallet, etc.)

## Common Issues

**"No module named 'adafruit_pn532'"**
```bash
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
```

**PN532 not responding**
1. Power cycle (unplug USB, wait 5s, replug)
2. Verify DTR/RTS set LOW in code (`uart.dtr = False`, `uart.rts = False`)
3. Check serial port: `ls /dev/tty.usbserial*`
4. Run diagnostic: `python3 test/test-adafruit-pn532.py`

**Phone tap not detected**
- Enable phone NFC (Android Settings → Connected devices)
- Place phone flat on PN532 (not just near it, ~3-5cm range)
- Remove phone case (some block NFC)
- iOS requires active scan intent (not passive like Android)

**Serial port permissions (Linux/Pi)**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

**Webhook not receiving events**
- Use ngrok for local testing: `ngrok http 3000`
- Configure webhook URL in Coinbase Commerce dashboard
- Verify `COINBASE_WEBHOOK_SECRET` matches dashboard

**TX/RX wiring**
- Must crossover: Module TX → Converter RX, Module RX → Converter TX
- See `test/SETUP-SUCCESS.md` for verified diagram

## Next Actions

**For first-time setup:**
1. Read `terminal/QUICKSTART.md` for step-by-step setup
2. Get Coinbase Commerce API key from https://commerce.coinbase.com/
3. Configure `terminal/.env` with API key and serial port
4. Test: `cd terminal && npm run dev`

**For development:**
- Implementation complete - see `terminal/IMPLEMENTATION-SUMMARY.md` for details
- Phase 2 planning - see `terminal-implementation.md` for smart contract spec
- Hardware reference - see `test/SETUP-SUCCESS.md` for wiring

## Reference Documentation

**For AI Assistants:**
- This file (CLAUDE.md) - High-level architecture and commands
- `terminal/IMPLEMENTATION-SUMMARY.md` - Complete implementation details
- `terminal-implementation.md` - Implementation plan + Phase 2 spec
- `PAYMENT-INTENT-DECISION.md` - Why Coinbase Commerce for Phase 1

**For Users:**
- `README.md` - Project overview
- `terminal/QUICKSTART.md` - Step-by-step setup guide
- `terminal/README.md` - Terminal documentation
- `test/SETUP-SUCCESS.md` - Hardware wiring guide

**Technical Deep Dives:**
- `test/CARD-EMULATION-FINDINGS.md` - Why card emulation failed
- `implementation-history.md` - Historical debugging notes
