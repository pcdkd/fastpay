# CLAUDE.md

This file provides essential guidance to Claude Code when working with the FastPay codebase.

## Project Overview

FastPay is an NFC-based cryptocurrency payment terminal that enables tap-to-pay crypto payments in under 10 seconds. The terminal inverts the traditional crypto flow from "push" (customer-initiated) to "pull" (merchant-initiated) to match credit card UX.

**Current Status:** Phase 1 - Hardware setup complete, building NFC bridge and terminal software

**Tech Stack:**
- **Terminal:** Node.js v20.x (business logic), Python 3.11+ (NFC hardware bridge)
- **Blockchain:** Base L2, USDC token
- **NFC Hardware:** PN532 module (UART), Adafruit CircuitPython library
- **Customer App:** React Native test app (Phase 1)
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

### Setup
```bash
npm install  # Install all workspace dependencies

# Python dependencies
pip3 install adafruit-circuitpython-pn532 pyserial
```

### Testing
```bash
# Hardware verification (from test/)
python3 test-adafruit-pn532.py    # Verify NFC module
python3 detect-phone-tap.py       # Test phone detection
python3 card-emulation-raw.py     # Test card emulation

# Terminal (when implemented)
cd terminal && npm test
```

### Environment Configuration

```bash
# NFC Hardware
NFC_PORT=/dev/tty.usbserial-ABSCDY4Z  # Platform-specific
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

## Common Issues

1. **"No module named 'adafruit_pn532'"**: Run `pip3 install adafruit-circuitpython-pn532`
2. **Module not responding**: Set `uart.dtr = False` and `uart.rts = False` after opening port
3. **TX/RX crossover**: Module TX → Converter RX, Module RX → Converter TX
4. **Serial permissions (Linux)**: Add user to dialout group or use sudo
5. **Card emulation**: Adafruit library doesn't support TgInitAsTarget - use raw PN532 commands

## References

- **implementation-history.md** - Detailed debugging, hardware setup, implementation decisions
- **FastPay-Phase1-ProjectDoc.md** - Complete architectural specification (local only)
- **README.md** - Project overview and roadmap
- **test/** - Working hardware test scripts and setup documentation
