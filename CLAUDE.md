# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastPay is a pull payment protocol for AI agent commerce on Base L2. The core innovation: **Customer signs gasless authorization, merchant executes and pays gas.**

### Current Status (Hackathon - Day 3 Complete)
**✅ Deployed:** `0xa6Dde921ef709471C61a52c0faAf47a97D59c35a` on Base Sepolia
**✅ Tested:** Live transaction processed 0.50 USDC with 137k gas
**🎯 Focus:** Smart contracts + Agent SDK (hackathon submission)

### Three Component System

#### 1. Smart Contracts (`contracts/`) - **PRIMARY FOCUS**
**Status:** ✅ Deployed & Verified on Base Sepolia
- **Contract:** `FastPayCore.sol` - Pull payment execution with EIP-712 signatures
- **Tech:** Solidity 0.8.24, Foundry, OpenZeppelin (ReentrancyGuard, IERC20)
- **Gas:** ~137k per payment (~$0.0006 on Base L2)
- **Security:** Nonce-based replay protection, expiration timestamps, signature verification
- **Use Case:** AI agents make payments with only USDC (no ETH needed)

#### 2. Agent SDK (`agents/`) - **PRIMARY FOCUS**
**Status:** ✅ Working end-to-end demo
- **Classes:** `MerchantAgent`, `CustomerAgent` (in `AgentWallet.js`)
- **Tech:** ethers.js v6, EIP-712 typed signatures, policy-based approval
- **Features:** Gasless signing, spending policies, balance management
- **Demo:** `demo.js` shows complete payment flow
- **Use Case:** JavaScript agents that autonomously handle payments

#### 3. Terminal (`terminal/`) - **LEGACY (separate from hackathon)**
**Status:** ✅ Phase 1 Complete (different payment model)
- **Payment Model:** PUSH payments via Coinbase Commerce (NOT pull payments)
- **Tech:** Node.js + Python (PN532 NFC) + Coinbase Commerce API
- **NFC Role:** Tap detection only (no data transfer)
- **Use Case:** Physical POS system for walk-in customers
- **Note:** Uses QR codes + Coinbase Commerce, customer pays gas via Coinbase abstraction

**Critical Distinction:** Terminal is a separate implementation using traditional push payments. The hackathon submission focuses on contracts + agents implementing TRUE pull payments for agent commerce.

## Core Architecture

### Pull Payment Flow (Hackathon Focus)
```
┌─────────────────┐                    ┌─────────────────┐
│ Customer Agent  │                    │ Merchant Agent  │
│ (needs USDC)    │                    │ (needs ETH)     │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │ 1. Receives payment request          │
         │    {merchant, customer, token,       │
         │     amount, validUntil, nonce}       │
         │<─────────────────────────────────────│
         │                                      │
         │ 2. Evaluates spending policy         │
         │    - Check amount limit              │
         │    - Check merchant whitelist        │
         │    - Check daily limit               │
         │                                      │
         │ 3. Signs EIP-712 authorization       │
         │    (GASLESS - no blockchain tx)      │
         │                                      │
         │ 4. Returns signature                 │
         │─────────────────────────────────────>│
         │                                      │
         │                          5. Calls executePullPayment()
         │                             (Merchant pays ~137k gas)
         │                                      │
         │                                      ▼
         │                          ┌───────────────────┐
         │                          │  FastPayCore.sol  │
         │                          │  - Verify sig     │
         │                          │  - Check nonce    │
         │                          │  - transferFrom() │
         │                          └───────────────────┘
         │                                      │
         │ 6. USDC transferred                  │
         │    (via ERC-20 transferFrom)         │
         │<─────────────────────────────────────│
```

**Key Innovation:** Customer never needs ETH. Merchant absorbs gas cost (can be priced into service).

## Development Commands

### Smart Contracts (`contracts/`) - Primary Development
```bash
# Setup (requires Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup)
cd contracts
forge install && forge build

# Testing (11 comprehensive tests)
forge test                                         # All tests
forge test -vv                                     # Verbose output
forge test --gas-report                            # Gas cost analysis
forge test --match-test testExecutePullPayment -vvv  # Specific test with traces

# Deployment to Base Sepolia (testnet)
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base_sepolia --broadcast --verify

# Deployment to Base Mainnet (production)
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base --broadcast --verify

# Utilities
forge fmt              # Format Solidity code
forge clean            # Clean build artifacts
```

### Agent SDK (`agents/`) - Primary Development
```bash
cd agents
npm install
cp .env.example .env   # Configure FASTPAY_ADDRESS, MERCHANT_PRIVATE_KEY, etc.

# Run end-to-end demo (uses live contract on Sepolia)
npm run demo

# Required .env variables:
# FASTPAY_ADDRESS=0xa6Dde921ef709471C61a52c0faAf47a97D59c35a (Sepolia)
# MERCHANT_PRIVATE_KEY=0x... (needs ETH for gas)
# CUSTOMER_PRIVATE_KEY=0x... (needs USDC only)
# BASE_RPC_URL=https://sepolia.base.org
# USDC_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e (Sepolia)
```

### Terminal (`terminal/`) - Legacy POS System
```bash
# Setup (only needed for NFC POS development)
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
cd terminal && npm install
cp .env.example .env  # Configure COINBASE_API_KEY and NFC_PORT

# Run
npm run dev    # Development with auto-restart
npm start      # Production mode

# NFC Hardware Testing
python3 scripts/nfc_reader.py     # Standalone NFC test
python3 test/test-adafruit-pn532.py  # Hardware diagnostic
ls /dev/tty.usbserial*            # Find USB-UART port (Mac/Linux)
```

## Key Implementation Details

### Smart Contract (`contracts/src/FastPayCore.sol`)
**Core Function:** `executePullPayment(Payment calldata payment, bytes calldata signature)`

**Payment Struct:**
```solidity
struct Payment {
    address merchant;      // Who receives the funds
    address customer;      // Who authorized the payment
    address token;         // ERC-20 token address (USDC)
    uint256 amount;        // Amount in token's smallest unit (6 decimals for USDC)
    uint256 validUntil;    // Unix timestamp (payment expires after this)
    bytes32 nonce;         // Unique identifier (prevents replay)
}
```

**Security Mechanisms:**
- **EIP-712 Domain Separator:** Prevents signature reuse across chains/contracts
- **Nonce Tracking:** `mapping(bytes32 => bool) public usedNonces` prevents double-spending
- **Expiration Check:** `require(block.timestamp <= payment.validUntil, "Payment expired")`
- **Signature Recovery:** Uses ECDSA.recover() to verify customer authorized payment
- **ReentrancyGuard:** Prevents reentrancy attacks during token transfer
- **Merchant-Only Execution:** `require(msg.sender == payment.merchant, "Not merchant")`

**Gas Optimization:**
- Uses `calldata` instead of `memory` for parameters
- Minimal storage writes (only nonce mapping)
- Efficient EIP-712 hashing
- Actual cost: 137,691 gas (~$0.0006 on Base L2)

### Agent SDK (`agents/AgentWallet.js`)

**MerchantAgent Class:**
```javascript
createPayment(customerAddress, tokenAddress, amountUSD, validForSeconds)
  → Returns: { payment: {...}, nonce: bytes32 }

executePullPayment(payment, signature)
  → Calls: fastPayCore.executePullPayment() with merchant wallet
  → Returns: { success: bool, txHash: string, gasUsed: number }
```

**CustomerAgent Class:**
```javascript
evaluatePayment(payment, policy)
  → Checks: amount limits, merchant whitelist, token whitelist, daily limits
  → Returns: { approved: bool, reasons: string[] }

signPayment(payment)
  → Signs: EIP-712 typed data (completely off-chain, no gas)
  → Returns: signature (65 bytes: r, s, v)

handlePaymentRequest(payment, policy)
  → Combined: evaluate + sign if approved
  → Returns: { approved: bool, signature?: string, reasons?: string[] }
```

**Spending Policy Object:**
```javascript
{
  maxAmountUSD: 100,              // Per-payment limit
  maxPaymentsPerDay: 10,          // Daily transaction count limit
  allowedMerchants: ['0x...'],    // Whitelist (empty = allow all)
  allowedTokens: ['0x...']        // Whitelist (empty = allow all)
}
```

## Blockchain Configuration

### Base L2 Network Details
- **Mainnet Chain ID:** 8453
- **Testnet Chain ID:** 84532 (Base Sepolia)
- **RPC URLs:**
  - Mainnet: `https://mainnet.base.org`
  - Sepolia: `https://sepolia.base.org`
- **Block Time:** ~2 seconds
- **Gas Costs:** Very low (~$0.001 per transaction on L2)

### Token Addresses
- **USDC Mainnet:** `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **USDC Sepolia:** `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- **Decimals:** 6 (important for amount calculations!)

### Contract Deployment
- **FastPayCore Sepolia:** `0xa6Dde921ef709471C61a52c0faAf47a97D59c35a` (verified ✅)
- **Basescan Sepolia:** https://sepolia.basescan.org
- **Basescan Mainnet:** https://basescan.org

### Getting Test Tokens
- **Base Sepolia ETH:** https://www.alchemy.com/faucets/base-sepolia
- **Base Sepolia USDC:** Swap ETH for USDC on Uniswap testnet

### Key Dependencies
- **Contracts:** Foundry (forge, anvil), Solidity 0.8.24, OpenZeppelin (ReentrancyGuard, ECDSA, IERC20)
- **Agents:** Node.js 20+, ethers.js v6, dotenv
- **Terminal (legacy):** Node.js 20+, express, qrcode, axios | Python 3.11+, adafruit-circuitpython-pn532

## Common Issues & Solutions

### Smart Contract Issues

**"Insufficient allowance" error:**
```javascript
// Customer must first approve FastPay contract to spend USDC
await customer.approveToken(usdcAddress);
// Or manually:
const usdc = new ethers.Contract(usdcAddress, ERC20_ABI, customerWallet);
await usdc.approve(fastPayAddress, ethers.MaxUint256);
```

**"Payment expired" error:**
- Payment requests have expiration timestamps (`validUntil`)
- Default: 180 seconds (3 minutes)
- Create new payment request if expired

**"Nonce already used" error:**
- Each nonce can only be used once (replay protection)
- Generate new random nonce: `ethers.randomBytes(32)`

**"Invalid signature" error:**
- Customer must sign with correct EIP-712 domain and types
- Verify `chainId` matches network (8453 mainnet, 84532 sepolia)
- Verify `verifyingContract` is correct FastPay address

**"Insufficient balance" error:**
```javascript
// Check customer USDC balance before payment
const balance = await usdcContract.balanceOf(customerAddress);
console.log('USDC balance:', ethers.formatUnits(balance, 6));
```

**Foundry not installed:**
```bash
curl -L https://foundry.paradigm.xyz | bash && foundryup
```

### Agent SDK Issues

**"Cannot find module 'ethers'":**
```bash
cd agents && npm install
```

**Transaction fails with "insufficient funds for gas":**
- **Merchant wallet** needs ETH for gas (not USDC!)
- Customer wallet only needs USDC (no ETH required)
- Get testnet ETH: https://www.alchemy.com/faucets/base-sepolia

**"Network mismatch" errors:**
- Verify RPC URL matches intended network
- Sepolia: `https://sepolia.base.org`
- Mainnet: `https://mainnet.base.org`

### Terminal Issues (Legacy System)

**"No module named 'adafruit_pn532'":**
```bash
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
```

**PN532 not responding:**
1. Check wiring: TX/RX must crossover (PN532 TX → Converter RX, PN532 RX → Converter TX)
2. Verify port: `ls /dev/tty.usbserial*` (Mac/Linux)
3. Set `uart.dtr = False` and `uart.rts = False` in Python code
4. Run diagnostic: `python3 test/test-adafruit-pn532.py`

## Important Design Decisions

### Why Pull Payments vs Push Payments?

**Traditional Crypto (Push):**
- Customer constructs transaction
- Customer broadcasts to network
- Customer pays gas fees
- **Problem:** AI agents need ETH + gas monitoring + transaction construction skills

**FastPay Pull Payments:**
- Customer signs EIP-712 message (off-chain, gasless)
- Merchant broadcasts transaction
- Merchant pays gas fees
- **Benefit:** AI agents only need USDC, simple signing interface

### Why EIP-712 Signatures?

- **Human-readable:** Wallet displays structured payment details (not random hex)
- **Secure:** Domain separator prevents cross-chain/cross-contract replay
- **Standard:** Widely supported by wallets (MetaMask, Rainbow, etc.)
- **Gasless:** Signing is completely off-chain (no ETH needed)

### Why Nonce-Based Replay Protection?

Each payment has unique random nonce (not sequential like Ethereum transactions):
- **No race conditions:** Multiple payments can be prepared in parallel
- **Flexible execution:** Merchant can execute in any order
- **Simple revocation:** Just don't execute the signed payment
- **No state management:** Customer doesn't track nonces

### Comparison to EIP-3009 (USDC's transferWithAuthorization)

| Feature | FastPay | EIP-3009 |
|---------|---------|----------|
| **Token Support** | ANY ERC-20 | Only tokens implementing EIP-3009 |
| **Adoption Barrier** | Deploy one contract | Token must natively support it |
| **Flexibility** | Can add features (escrow, batch, etc.) | Limited to token's implementation |
| **Gas Payer** | Merchant (predictable) | Relayer (varies) |
| **Merchant Control** | Full control over execution timing | Must trust relayer |

**Key Advantage:** Works with existing USDC, USDT, DAI, any ERC-20 - no token changes needed!

### Future: NFC Integration with Pull Payments

**Challenge:** Terminal doesn't know customer address at tap time

**Solution (Two-Phase NFC Protocol):**
1. **Discovery Phase:** NFC read gets customer wallet address from phone
2. **Payment Phase:** Terminal creates pull payment for discovered address
3. **Authorization Phase:** Customer signs on phone (gasless)
4. **Execution Phase:** Terminal executes pull payment (pays gas)

See `NFC-PULL-PAYMENT-ARCHITECTURE.md` for detailed design.

## Documentation Index

### Hackathon Submission (Primary)
- `README.md` - Project overview, deployment info, metrics
- `contracts/README.md` - Smart contract documentation & testing
- `agents/README.md` - Agent SDK usage & API reference
- `DEPLOYMENT-SUCCESS.md` - Deployment details & live transaction
- `STATUS.md` - Hackathon progress tracker
- `EIP-ANALYSIS.md` - Analysis of related EIPs and standardization path

### Architecture & Design
- `NFC-PULL-PAYMENT-ARCHITECTURE.md` - Future NFC + pull payment integration
- `DEPLOYMENT-GUIDE.md` - Step-by-step deployment instructions
- `HACKATHON-SPRINT-PLAN.md` - 4-day development roadmap

### Legacy Terminal System
- `terminal/QUICKSTART.md` - Terminal setup (Coinbase Commerce push payments)
- `test/SETUP-SUCCESS.md` - NFC hardware wiring guide
- `test/CARD-EMULATION-FINDINGS.md` - Why card emulation failed
- `PAYMENT-INTENT-DECISION.md` - Phase 1 architecture rationale
