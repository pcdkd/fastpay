# FastPayCore Smart Contract

Pull payment protocol for agent commerce on Base L2.

## ✅ Live Deployment

**FastPayCore is deployed and verified on Base Sepolia!**

- **Contract Address:** `0xa6Dde921ef709471C61a52c0faAf47a97D59c35a`
- **Network:** Base Sepolia Testnet (Chain ID: 84532)
- **Explorer:** [View on Basescan](https://sepolia.basescan.org/address/0xa6Dde921ef709471C61a52c0faAf47a97D59c35a)
- **Status:** ✅ Verified source code
- **Demo Transaction:** [View on Basescan](https://sepolia.basescan.org/tx/0xb6f03b7d263c151e3e47c2de3e0c0fbb5fdbb97f99aa4d190a60c071a8d093b4)

**Performance:**
- Gas Used: 137,691 per payment (~$0.0006)
- Customer Cost: $0.00 (gasless!)
- Settlement Time: < 10 seconds

---

## Overview

FastPayCore enables **gasless customer payments** by inverting the traditional crypto payment flow:

- **Traditional:** Customer constructs tx → Customer broadcasts → Customer pays gas
- **FastPay:** Customer signs message → Merchant broadcasts → Merchant pays gas

This is critical for AI agents who only need USDC (no ETH for gas).

## Smart Contract

**Contract:** `src/FastPayCore.sol`

Key features:
- EIP-712 typed signature authorization
- Nonce-based replay protection
- ReentrancyGuard for security
- Gas-optimized (~100k gas per payment)
- Works with ANY ERC-20 token (USDC, USDT, etc.)

## Installation

```bash
# Install Foundry (if not already installed)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install dependencies
forge install

# Build contracts
forge build

# Run tests
forge test -vv
```

## Testing

```bash
# Run all tests
forge test

# Run with gas reporting
forge test --gas-report

# Run specific test
forge test --match-test testExecutePullPayment -vvv
```

**Test coverage:** 11 tests covering:
- ✅ Happy path payment execution
- ✅ Expired payment rejection
- ✅ Nonce replay protection
- ✅ Invalid signature rejection
- ✅ Unauthorized merchant rejection
- ✅ Signature verification
- ✅ Insufficient balance handling
- ✅ Missing approval handling
- ✅ Multiple sequential payments

## Deployment

### 1. Configure Environment

```bash
cp .env.example .env
nano .env  # Add your PRIVATE_KEY and ETHERSCAN_API_KEY
```

**Get test tokens:**
- Base Sepolia ETH: https://www.alchemy.com/faucets/base-sepolia
- Base Sepolia USDC: 0x036CbD53842c5426634e7929541eC2318f3dCF7e

### 2. Deploy to Base Sepolia (Testnet) - Recommended First

```bash
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base_sepolia \
  --broadcast \
  --verify
```

### 3. Deploy to Base Mainnet (Production)

After testing on Sepolia:

```bash
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base \
  --broadcast \
  --verify
```

## Usage

### Customer Flow (JavaScript Agent)

```javascript
import { ethers } from 'ethers';

// 1. Merchant creates payment request
const payment = {
  merchant: merchantAddress,
  customer: customerAddress,
  token: usdcAddress,
  amount: ethers.parseUnits('5.00', 6), // $5 USDC
  validUntil: Math.floor(Date.now() / 1000) + 180, // 3 minutes
  nonce: ethers.randomBytes(32)
};

// 2. Customer signs payment (gasless)
const domain = {
  name: 'FastPay',
  version: '1',
  chainId: 8453,
  verifyingContract: fastPayAddress
};

const types = {
  Payment: [
    { name: 'merchant', type: 'address' },
    { name: 'customer', type: 'address' },
    { name: 'token', type: 'address' },
    { name: 'amount', type: 'uint256' },
    { name: 'validUntil', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' }
  ]
};

const signature = await customerWallet.signTypedData(domain, types, payment);

// 3. Merchant executes payment (pays gas)
const tx = await fastPay.connect(merchantWallet).executePullPayment(
  payment,
  signature
);

console.log('✅ Payment executed:', tx.hash);
```

### Merchant Flow (JavaScript Agent)

See `../agents/demo.js` for complete agent implementation.

## Contract Addresses

### Base Sepolia Testnet (Chain ID: 84532) - Development
- **FastPayCore:** *Deploy with script above*
- **USDC:** `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- **Explorer:** https://sepolia.basescan.org

### Base Mainnet (Chain ID: 8453) - Production
- **FastPayCore:** *Deploy after Sepolia testing*
- **USDC:** `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Explorer:** https://basescan.org

## Gas Costs

Typical gas usage on Base L2:
- **executePullPayment:** ~100k gas (~$0.001-0.005 per payment)
- **First-time approval:** ~46k gas (one-time per customer)

## Security

- ✅ ReentrancyGuard prevents reentrancy attacks
- ✅ EIP-712 signatures prevent signature malleability
- ✅ Nonce system prevents replay attacks
- ✅ Expiration timestamps prevent stale payments
- ✅ Merchant-only execution prevents unauthorized pulls

## Architecture

```
Customer Agent                    Merchant Agent
     |                                  |
     | 1. Receives payment request      |
     | 2. Evaluates against policy      |
     | 3. Signs EIP-712 message         |
     |    (GASLESS - no ETH needed)     |
     |                                  |
     |--------------------------------->|
     |        Signature                 |
     |                                  |
     |                                  | 4. Calls executePullPayment()
     |                                  |    (Merchant pays gas)
     |                                  |
     |<---------------------------------|
     |    USDC transferred              |
     |    (via transferFrom)            |
```

## Why Pull Payments?

**For AI Agents:**
- ✅ Customer agents need **only USDC**, no ETH for gas
- ✅ No transaction construction complexity
- ✅ No gas price monitoring
- ✅ Simple signing interface (just EIP-712)
- ✅ Merchant absorbs gas cost (can be factored into pricing)

**For Merchants:**
- ✅ Familiar credit card-style flow (merchant initiates)
- ✅ Can batch multiple payments for gas efficiency
- ✅ No waiting for customer to broadcast transaction
- ✅ Better UX for automated recurring payments

## Comparison to EIP-3009

| Feature | FastPay | EIP-3009 |
|---------|---------|----------|
| Token Support | ANY ERC-20 | Only tokens that implement it |
| Gas Payment | Merchant | Recipient |
| Use Case | Agent commerce | General meta-transactions |
| Nonce Management | Contract-level | Per-token |
| Expiration | Built-in | Optional |

## Development

```bash
# Format code
forge fmt

# Run linter
forge fmt --check

# Clean build artifacts
forge clean

# Update dependencies
forge update
```

## License

MIT
