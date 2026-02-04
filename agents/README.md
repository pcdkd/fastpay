# FastPay Agent SDK

JavaScript SDK for building AI agents that can send and receive pull payments.

## Overview

This SDK provides merchant and customer agent classes that handle:
- EIP-712 signature creation and verification
- Spending policy evaluation
- Pull payment execution
- Balance and allowance management

## Installation

```bash
npm install
```

## Configuration

```bash
cp .env.example .env
nano .env  # Add your configuration
```

Required environment variables:
- `FASTPAY_ADDRESS` - Deployed FastPayCore contract address
- `MERCHANT_PRIVATE_KEY` - Merchant wallet private key (needs ETH for gas)
- `CUSTOMER_PRIVATE_KEY` - Customer wallet private key (needs USDC only!)
- `BASE_RPC_URL` - RPC endpoint (default: Base Sepolia testnet)
- `CHAIN_ID` - Chain ID (84532 for Sepolia, 8453 for mainnet)
- `USDC_ADDRESS` - USDC token address (default: Base Sepolia USDC)

**Get test tokens:**
- Base Sepolia ETH: https://www.alchemy.com/faucets/base-sepolia
- Base Sepolia USDC: 0x036CbD53842c5426634e7929541eC2318f3dCF7e (swap on Uniswap)

## Running the Demo

```bash
npm run demo
```

This will execute an agent-to-agent payment demonstrating:
1. Merchant creates $5 payment request
2. Customer evaluates against policy
3. Customer signs authorization (GASLESS)
4. Merchant executes payment (pays gas)
5. Payment completes in <10 seconds

## Agent SDK Usage

### Merchant Agent

```javascript
import { MerchantAgent } from './AgentWallet.js';
import { ethers } from 'ethers';

// Initialize merchant agent
const provider = new ethers.JsonRpcProvider('https://mainnet.base.org');
const wallet = new ethers.Wallet(privateKey, provider);
const merchant = new MerchantAgent(wallet, fastPayAddress, provider);

// Create payment request
const paymentRequest = await merchant.createPayment(
  customerAddress,
  usdcAddress,
  '5.00', // $5 USD
  180 // Valid for 3 minutes
);

// After customer signs...
const result = await merchant.executePullPayment(
  paymentRequest.payment,
  customerSignature
);

console.log('Payment executed:', result.txHash);
```

### Customer Agent

```javascript
import { CustomerAgent } from './AgentWallet.js';
import { ethers } from 'ethers';

// Initialize customer agent
const provider = new ethers.JsonRpcProvider('https://mainnet.base.org');
const wallet = new ethers.Wallet(privateKey, provider);
const customer = new CustomerAgent(wallet, fastPayAddress, provider);

// Approve USDC spending (one-time)
await customer.approveToken(usdcAddress);

// Define spending policy
const policy = {
  maxAmountUSD: 100,          // Max $100 per payment
  maxPaymentsPerDay: 10,      // Max 10 payments per day
  allowedMerchants: [],       // Empty = allow all
  allowedTokens: []           // Empty = allow all
};

// Handle payment request
const result = await customer.handlePaymentRequest(payment, policy);

if (result.approved) {
  console.log('Payment approved, signature:', result.signature);
  // Send signature back to merchant
} else {
  console.log('Payment rejected:', result.reasons);
}
```

## Spending Policy

Customer agents can enforce spending policies:

```javascript
const policy = {
  // Maximum amount per payment (USD)
  maxAmountUSD: 100,

  // Maximum payments per day
  maxPaymentsPerDay: 10,

  // Whitelist of allowed merchant addresses (empty = allow all)
  allowedMerchants: [
    '0x1234...', // Coffee shop
    '0x5678...', // API provider
  ],

  // Whitelist of allowed tokens (empty = allow all)
  allowedTokens: [
    '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' // USDC only
  ]
};
```

## Key Features

### Gasless Customer Signing

Customer agents only sign EIP-712 messages - they **never pay gas**:

```javascript
// Customer signs (no gas, no transaction)
const signature = await customer.signPayment(payment);

// Merchant executes (pays gas)
const tx = await merchant.executePullPayment(payment, signature);
```

### Policy-Based Approval

Customer agents automatically evaluate payments against policy:

```javascript
const evaluation = await customer.evaluatePayment(payment, policy);

if (!evaluation.approved) {
  console.log('Rejected:', evaluation.reasons);
  // e.g., "Amount 150 USD exceeds limit of 100 USD"
}
```

### Balance and Allowance Management

```javascript
// Check stats before payment
const stats = await customer.getStats(usdcAddress);

console.log('USDC Balance:', stats.tokenBalance);
console.log('FastPay Allowance:', stats.allowance);
console.log('Needs Approval:', stats.needsApproval);
```

## Architecture

```
┌─────────────────────┐           ┌─────────────────────┐
│   Merchant Agent    │           │   Customer Agent    │
│                     │           │                     │
│ - Creates payment   │           │ - Evaluates policy  │
│ - Executes on-chain │           │ - Signs EIP-712     │
│ - Pays gas fees     │           │ - NO gas needed!    │
└──────────┬──────────┘           └──────────┬──────────┘
           │                                  │
           │  1. Payment Request              │
           │─────────────────────────────────>│
           │                                  │
           │  2. Signature (GASLESS)          │
           │<─────────────────────────────────│
           │                                  │
           ▼                                  │
    ┌─────────────┐                          │
    │  FastPayCore │                          │
    │   Contract   │                          │
    │              │                          │
    │ - Verifies   │                          │
    │ - Transfers  │                          │
    └──────┬───────┘                          │
           │                                  │
           │  3. USDC Transfer                │
           │─────────────────────────────────>│
           │                                  │
           ▼                                  ▼
    Merchant receives USDC          Customer's USDC spent
```

## API Reference

### MerchantAgent

- `createPayment(customerAddress, tokenAddress, amountUSD, validForSeconds)` - Create payment request
- `executePullPayment(payment, signature)` - Execute signed payment
- `getStats()` - Get merchant payment stats

### CustomerAgent

- `evaluatePayment(payment, policy)` - Evaluate against spending policy
- `signPayment(payment)` - Sign EIP-712 authorization (gasless)
- `handlePaymentRequest(payment, policy)` - Evaluate + sign in one call
- `approveToken(tokenAddress, amount)` - Approve token spending
- `getStats(tokenAddress)` - Get customer stats and balances

### Utility Functions

- `formatPayment(payment, decimals)` - Format payment for display
- `parsePaymentEvent(receipt)` - Parse PaymentExecuted event from receipt

## Example: Simple Merchant Agent

```javascript
import { MerchantAgent } from './AgentWallet.js';

class CoffeeShopAgent {
  constructor(wallet, fastPayAddress, provider) {
    this.merchant = new MerchantAgent(wallet, fastPayAddress, provider);
  }

  async chargeCoffee(customerAddress, size) {
    const prices = { small: '3.00', medium: '4.00', large: '5.00' };
    const amount = prices[size];

    // Create payment request
    const request = await this.merchant.createPayment(
      customerAddress,
      usdcAddress,
      amount
    );

    // Display QR code or send to customer agent
    return request;
  }

  async completePayment(payment, signature) {
    // Execute payment
    const result = await this.merchant.executePullPayment(payment, signature);
    console.log('Coffee paid! ☕️', result.txHash);
  }
}
```

## Example: Simple Customer Agent

```javascript
import { CustomerAgent } from './AgentWallet.js';

class PersonalAssistantAgent {
  constructor(wallet, fastPayAddress, provider) {
    this.customer = new CustomerAgent(wallet, fastPayAddress, provider);

    // Define spending limits
    this.policy = {
      maxAmountUSD: 50,
      maxPaymentsPerDay: 20,
      allowedMerchants: [] // Trust all merchants
    };
  }

  async handlePaymentRequest(payment) {
    // Automatically evaluate and sign if approved
    const result = await this.customer.handlePaymentRequest(
      payment,
      this.policy
    );

    if (result.approved) {
      console.log('Payment approved:', result.details);
      return result.signature;
    } else {
      console.log('Payment rejected:', result.reasons);
      return null;
    }
  }
}
```

## Gas Costs

On Base L2:
- **Customer signing:** $0.00 (gasless!)
- **Merchant execution:** ~100k gas (~$0.001-0.005 per payment)
- **Token approval:** ~46k gas (one-time per customer)

## Security

- ✅ Customer agents only sign messages (never expose to gas risk)
- ✅ EIP-712 typed signatures prevent phishing
- ✅ Nonce system prevents replay attacks
- ✅ Expiration timestamps prevent stale payments
- ✅ Policy evaluation happens before signing
- ✅ All token transfers require prior approval

## Troubleshooting

**"Insufficient allowance" error:**
```javascript
await customer.approveToken(usdcAddress);
```

**"Payment expired" error:**
- Payment requests expire after `validForSeconds` (default: 180s)
- Create a new payment request

**"Nonce already used" error:**
- Each payment can only be executed once
- Create a new payment with a new nonce

**"Invalid signature" error:**
- Ensure customer wallet signed the payment
- Verify FastPay contract address matches

## License

MIT
