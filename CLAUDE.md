# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastPay is an NFC-based cryptocurrency payment terminal system that enables tap-to-pay crypto payments in under 10 seconds. The project inverts the traditional crypto payment flow from "push" (customer-initiated) to "pull" (merchant-initiated) to match credit card UX.

**Current Status:** Phase 1 POC - codebase not yet implemented, architectural planning complete

**Tech Stack:**
- **Terminal:** Node.js v20.x (merchant device), Python 3.11+ (NFC bridge)
- **Blockchain:** Base L2, USDC token
- **NFC Hardware:** PN532 module via UART (115200 baud)
- **Customer App:** React Native (Phase 1 test app)
- **Smart Contracts:** Coinbase Commerce Payments Protocol (Week 3)

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

### Development Approaches

**Desktop-First (Recommended):** Use USB-to-UART converter to develop on laptop/desktop before migrating to Raspberry Pi. Identical codebase runs on both platforms by changing serial port path.

**Hardware Paths:**
- Week 1-2: Desktop dev with USB-to-UART converter
- Week 3+: Raspberry Pi deployment
- Phase 3: ESP32 phone dongle
- Phase 4: Custom hardware

## Monorepo Structure

```
fastpay/
├── packages/          # Shared TypeScript types and utilities
│   ├── types/        # payment-request.ts, nfc-payload.ts
│   └── utils/        # EIP-712 signature helpers, validation
│
├── terminal/         # Merchant terminal (Node.js + Python NFC bridge)
│   ├── src/
│   │   ├── wallet.js      # EIP-712 signing with merchant wallet
│   │   ├── payment.js     # Payment request creation
│   │   ├── nfc.js         # NFC communication wrapper
│   │   ├── monitor.js     # Blockchain event monitoring
│   │   └── commerce/      # Week 3: Commerce Payments integration
│   └── scripts/
│       ├── nfc_bridge.py  # Python NFC driver (works on laptop + Pi)
│       ├── test-serial.py # Serial port verification
│       └── test-nfc.py    # NFC hardware test
│
├── customer-app/     # React Native test app
│   └── src/
│       ├── NFCReader.js       # NFC tag reading
│       ├── PaymentVerifier.js # EIP-712 signature verification
│       └── WalletConnector.js # MetaMask deep link generation
│
├── contracts/        # Week 3: Commerce Payments escrow contracts
│   └── CommercePayments.sol
│
├── dongle/          # Phase 3: ESP32 firmware (future)
│
└── hardware/        # Wiring diagrams, 3D models, PCB designs
    ├── desktop-dev/ # USB-to-UART setup
    └── pi-terminal/ # Raspberry Pi GPIO wiring
```

## Development Commands

### Initial Setup

```bash
# Install all dependencies (uses npm workspaces)
npm install

# Desktop development - requires USB-to-UART converter
cd terminal
npm run dev:desktop  # Uses /dev/tty.usbserial-XXXX

# Raspberry Pi deployment
npm run dev:pi       # Uses /dev/ttyAMA0 (GPIO UART)
```

### Testing

```bash
# Run all tests across packages
npm test

# Hardware verification (run in terminal/)
python3 scripts/test-serial.py   # Verify USB/UART connection
python3 scripts/test-nfc.py      # Test PN532 communication
python3 scripts/test-card-detect.py  # Test NFC card detection

# Contract tests (Week 3)
cd contracts
npm test
```

### Environment Configuration

Key environment variables (see `terminal/.env.example`):

```bash
# Serial port path (platform-specific)
NFC_PORT=/dev/ttyAMA0              # Raspberry Pi GPIO
NFC_PORT=/dev/tty.usbserial-0001   # macOS USB-to-UART
NFC_PORT=COM3                       # Windows

# Blockchain
BASE_RPC_URL=https://mainnet.base.org
MERCHANT_PRIVATE_KEY=0x...
USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Week 3: Commerce Payments
ESCROW_CONTRACT_ADDRESS=0x...
SETTLEMENT_WINDOW=3600  # 1 hour in seconds
```

## Payment Flow Implementation

### Week 1-2: Simple USDC Transfers

```javascript
// terminal/src/payment.js
1. Merchant creates payment request (amount, merchant address)
2. Sign with EIP-712 (merchant wallet)
3. Encode as JSON payload
4. Send to Python NFC bridge via IPC
5. Python writes NDEF message to NFC tag emulation
6. Customer taps phone → reads NFC
7. Customer app verifies signature, generates MetaMask deep link
8. Customer approves → USDC.transfer(merchant, amount)
9. Terminal monitors Transfer event on Base L2
10. Display confirmation (<10 seconds total)
```

### Week 3: Commerce Payments Escrow

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

### UART Communication

- **Baud Rate:** 115200 bps (fixed)
- **Protocol:** ISO 14443A (NFC Type 4)
- **Mode:** Card Emulation (terminal acts as NFC tag)
- **Max Payload:** 256 bytes
- **Read Range:** 3-5cm optimal

### Platform-Specific Serial Ports

```python
# terminal/scripts/nfc_bridge.py

# Desktop development (USB-to-UART)
PORT = '/dev/tty.usbserial-0001'  # macOS
PORT = '/dev/ttyUSB0'              # Linux
PORT = 'COM3'                       # Windows

# Raspberry Pi production (GPIO UART)
PORT = '/dev/ttyAMA0'
```

**Important:** TX/RX must be crossed (NFC TX → Pi RX, NFC RX → Pi TX)

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
- **Week 1-2:** Desktop dev → NFC hardware + simple USDC transfers
- **Week 3:** Integrate Commerce Payments escrow protocol
- **Week 4:** Raspberry Pi migration + merchant pilot prep

**Success Criteria:**
- End-to-end payment in <10 seconds
- NFC read reliability >95%
- Video demo for stakeholder validation

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

## Common Gotchas

1. **Serial Port Permissions:** May need `sudo usermod -a -G dialout $USER` on Linux
2. **TX/RX Crossover:** Always connect NFC TX to converter/Pi RX (and vice versa)
3. **Voltage Levels:** PN532 is 3.3V logic, **not** 5V tolerant
4. **UART Config on Pi:** Must disable serial console and enable UART in `/boot/config.txt`
5. **Signature Expiry:** Payment requests expire in 3 minutes (client-side enforcement)
6. **Gas Estimation:** Base gas prices are ~0.001 Gwei, but spike during congestion
7. **NFC Timeout:** Customer must tap within 5 seconds of request creation

## References

- FastPay-Phase1-ProjectDoc.md - Complete architectural specification
- README.md - Project overview and roadmap
- hardware/ - Wiring diagrams and assembly guides
- docs/DESKTOP_DEV.md - Desktop development setup (when implemented)
- docs/TROUBLESHOOTING.md - Common issues and solutions (when implemented)
