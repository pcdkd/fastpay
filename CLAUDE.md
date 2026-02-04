# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastPay is a tap-to-pay crypto payment system with three distinct implementations:

### 1. Terminal Application (`terminal/`)
**Status:** ✅ Phase 1 Complete - Traditional PUSH payments via Coinbase Commerce
- **Payment Model:** Customer scans QR → Approves payment → Pushes USDC to merchant
- **NFC Role:** Reader mode (tap detection only) - does NOT transfer transaction data
- **Tech:** Node.js orchestration + Python (PN532 NFC hardware) + Coinbase Commerce API
- **Use Case:** Merchant point-of-sale system

### 2. Smart Contracts (`contracts/`)
**Status:** ✅ Day 1-2 Complete - Pull payment protocol with EIP-712 signatures
- **Payment Model:** TRUE PULL payments - merchant can withdraw from customer's allowance
- **Protocol:** `FastPayCore.sol` - gasless customer signatures, merchant executes & pays gas
- **Tech:** Solidity, Foundry, Base L2, works with any ERC-20 (USDC optimized)
- **Use Case:** AI agent commerce (agents don't need ETH for gas)

### 3. Agent SDK (`agents/`)
**Status:** ✅ Day 1-2 Complete - JavaScript SDK for agent wallets
- **Purpose:** Allows AI agents to create wallets, hold USDC, sign payment authorizations
- **Tech:** ethers.js v6, EIP-712 signing, nonce management
- **Components:** `AgentWallet.js` (class), `demo.js` (example usage)
- **Use Case:** AI agents that need to make/receive crypto payments

**Key Distinction:** Terminal uses Coinbase Commerce (push payments). Contracts + Agents implement true pull payments (EIP-712 signature-based).

## Architecture Summary

### Three-Layer Terminal Architecture (Separation of Concerns)
```
Layer 1: NFC TAP DETECTION (Python + PN532 hardware)
└── Only detects taps and reports UID - no payment logic

Layer 2: PAYMENT ORCHESTRATION (Node.js)
└── Creates charges, displays QR, associates taps, monitors webhooks

Layer 3: PAYMENT PROCESSING (External)
└── Coinbase Commerce handles checkout, blockchain settlement, webhooks
```

**Why This Works:** NFC layer is hardware-specific but portable. Payment logic is in testable Node.js. Terminal works even if NFC fails (QR fallback). Desktop development with USB-UART → Production on Raspberry Pi GPIO (same codebase, just change `NFC_PORT`).

## Development Commands

### Terminal Application (terminal/)
```bash
# Initial setup
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
cd terminal && npm install
cp .env.example .env  # Configure COINBASE_API_KEY and NFC_PORT

# Run terminal
npm run dev          # Development mode (auto-restart)
npm start           # Production mode

# Standalone NFC testing
python3 scripts/nfc_reader.py  # Test NFC without payment logic
```

### Smart Contracts (contracts/)
```bash
# Setup (requires Foundry)
cd contracts
forge install && forge build

# Testing
forge test              # Run all tests
forge test -vv          # Verbose output
forge test --gas-report # Show gas costs
forge test --match-test testExecutePullPayment -vvv  # Specific test

# Deployment
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base_sepolia --broadcast --verify  # Testnet
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base --broadcast --verify          # Mainnet
```

### Agent SDK (agents/)
```bash
cd agents
npm install
cp .env.example .env  # Configure RPC_URL, CONTRACT_ADDRESS, etc.
npm run demo         # Run demo showing agent wallet creation and payment
```

### Hardware Testing (test/)
```bash
cd test
python3 test-adafruit-pn532.py  # Verify PN532 hardware works
python3 detect-phone-tap.py     # Test tap detection
ls /dev/tty.usbserial*          # Find USB-UART port (Mac/Linux)
ls /dev/ttyAMA*                 # Find GPIO UART port (Raspberry Pi)
```

## Key Implementation Details

### Terminal Payment Flow (terminal/)
```
1. Merchant enters amount → Terminal creates Coinbase Commerce charge
2. Terminal displays QR code (hosted_url)
3. Customer taps phone (optional) → PN532 detects tap, associates with charge
4. Customer scans QR code → Opens Coinbase Commerce in browser
5. Customer approves → PUSHES USDC to deposit address
6. Coinbase webhook fires → Terminal shows "Payment Confirmed!"

Time: <10 seconds | NFC: Tap detection only (no data transfer) | Fallback: QR always works
```

**Terminal Modules (terminal/src/):**
- `index.js` - State machine (IDLE → WAITING_FOR_PAYMENT → COMPLETED), merchant input
- `nfc.js` - Node.js ↔ Python IPC bridge, spawns `scripts/nfc_reader.py` child process
- `commerce.js` - Coinbase Commerce API wrapper (charge creation, webhook verification)
- `payment.js` - Charge lifecycle (Map-based tracking, tap association, auto-expire)
- `webhook.js` - Express server on port 3000 for payment confirmations

**Python NFC Bridge IPC Protocol (stdout JSON):**
```json
{"event": "ready", "firmware": "1.6", "port": "...", "timestamp": ...}
{"event": "tap", "uid": "086AF124", "timestamp": ...}
{"event": "error", "message": "...", "fatal": false, "timestamp": ...}
```

### Smart Contract Architecture (contracts/)
```
FastPayCore.sol - Pull payment protocol
├── EIP-712 typed signatures (customer signs payment authorization)
├── Nonce-based replay protection (per-customer incremental)
├── ReentrancyGuard for security
├── Gas-optimized (~100k gas per payment)
└── Token-agnostic (works with any ERC-20)

Flow: Customer signs message → Merchant broadcasts tx → Merchant pays gas
Why: AI agents only need USDC (no ETH for gas)
```

### Agent SDK Design (agents/)
`AgentWallet.js` class provides:
- Wallet creation (random private key generation)
- Balance checking (USDC balance queries)
- EIP-712 signature generation (typed payment authorizations)
- Nonce management (auto-increment for replay protection)
- Demo: `demo.js` shows full customer+merchant interaction

## Critical Technical Details

### NFC Hardware Configuration (PN532)
**Library:** `adafruit-circuitpython-pn532` (Python)

**CRITICAL FIX for USB-UART converters (FT232/CP2102):**
```python
uart = serial.Serial(PORT, 115200, timeout=1)
uart.dtr = False  # REQUIRED - prevents reset on connection
uart.rts = False  # REQUIRED - prevents reset on connection
time.sleep(0.2)   # Signal stabilization
```

**Wiring (TX/RX MUST crossover):**
- PN532 TX → USB-UART RX
- PN532 RX → USB-UART TX
- Power: 3.3V or 5V (both work)

**Reader Mode Details:**
- Continuous scanning with 1s debounce (ignores re-taps)
- Exponential backoff on errors (max 5 retries)
- UID detection only (no NDEF data transfer)
- See `test/SETUP-SUCCESS.md` for verified wiring diagram

**Why Reader Mode (Not Card Emulation):**
- Card emulation tested and failed: PN532 UART too slow for ISO-DEP timing requirements
- See `test/CARD-EMULATION-FINDINGS.md` for full investigation

### Blockchain Configuration (Base L2)
- **Chain ID:** 8453 (Base Mainnet), 84532 (Base Sepolia testnet)
- **Token:** USDC - `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (mainnet)
- **Confirmation:** 1 block (~2-6 seconds)
- **Gas:** Terminal: Customer pays via Coinbase Commerce | Contracts: Merchant pays
- **Testnet Faucets:** Base Sepolia ETH - https://www.alchemy.com/faucets/base-sepolia

### Key Dependencies
- **Terminal:** Node.js 20+, express, qrcode, dotenv, axios | Python 3.11+, adafruit-circuitpython-pn532, pyserial
- **Contracts:** Foundry (forge, anvil, cast), Solidity 0.8.20, OpenZeppelin (ReentrancyGuard, IERC20)
- **Agents:** Node.js, ethers.js v6, dotenv
- **External:** Coinbase Commerce API (terminal only), Base L2 RPC

## Common Issues & Solutions

### NFC Hardware
**PN532 not responding:**
1. Power cycle (unplug USB, wait 5s, replug)
2. Verify `uart.dtr = False` and `uart.rts = False` in code
3. Check serial port exists: `ls /dev/tty.usbserial*`
4. Run diagnostic: `python3 test/test-adafruit-pn532.py`

**Phone tap not detected:**
- Enable NFC: Android Settings → Connected devices
- Place phone FLAT on PN532 (~3-5cm range, not just near)
- Remove phone case (some block NFC)
- iOS requires active scan intent (not passive like Android)

**TX/RX wiring:** Must crossover (Module TX → Converter RX, Module RX → Converter TX)

### Python/Terminal
**"No module named 'adafruit_pn532'":**
```bash
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
```

**Serial port permissions (Linux/Pi):**
```bash
sudo usermod -a -G dialout $USER  # Then log out and back in
```

**Webhook not receiving events:**
- Local testing: Use `ngrok http 3000` to expose webhook
- Configure webhook URL in Coinbase Commerce dashboard
- Verify `COINBASE_WEBHOOK_SECRET` matches dashboard value

### Smart Contracts
**Foundry not installed:**
```bash
curl -L https://foundry.paradigm.xyz | bash && foundryup
```

**Test failures:** Check `.env` has valid `RPC_URL` and funded `PRIVATE_KEY` for testnet

## Documentation Index

### Quick Start
- `README.md` - Project overview and status
- `terminal/QUICKSTART.md` - Terminal setup guide (start here for terminal)
- `contracts/README.md` - Smart contract deployment guide
- `agents/README.md` - Agent SDK usage examples

### Implementation Details
- `terminal/IMPLEMENTATION-SUMMARY.md` - Complete terminal implementation
- `test/SETUP-SUCCESS.md` - Hardware wiring guide
- `test/CARD-EMULATION-FINDINGS.md` - Why card emulation was rejected
- `FastPay-Phase1-ProjectDoc.md` - Original project specification
- `PAYMENT-INTENT-DECISION.md` - Phase 1 architecture rationale
