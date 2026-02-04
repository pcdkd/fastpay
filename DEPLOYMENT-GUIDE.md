# FastPay Deployment Guide - Base Sepolia

Quick reference for deploying and testing FastPay on Base Sepolia testnet.

---

## Prerequisites

### 1. Get Wallets Ready

You need 3 wallets:

1. **Deployer Wallet** - Deploys smart contract (needs Sepolia ETH)
2. **Merchant Wallet** - Executes payments (needs Sepolia ETH)
3. **Customer Wallet** - Signs payments (needs Sepolia USDC only)

### 2. Get Test Tokens

**Sepolia ETH** (for deployer and merchant):
- Faucet: https://www.alchemy.com/faucets/base-sepolia
- Bridge: https://bridge.base.org/ (from Sepolia testnet)
- Amount needed: ~0.01 ETH total

**Sepolia USDC** (for customer):
- Address: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- Get via Uniswap on Base Sepolia (swap ETH for USDC)
- Amount needed: ~10 USDC for testing

### 3. Get API Keys

**Basescan API Key** (for contract verification):
- Sign up: https://basescan.org/myapikey
- Free tier is sufficient

---

## Step 1: Deploy Smart Contract

### Configure Environment

```bash
cd contracts
cp .env.example .env
nano .env
```

Edit `.env`:
```bash
BASE_RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
PRIVATE_KEY=<your_deployer_wallet_private_key>
BASESCAN_API_KEY=<your_basescan_api_key>
USDC_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
```

### Deploy Contract

```bash
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base_sepolia \
  --broadcast \
  --verify
```

**Expected output:**
```
====================================
FastPayCore deployed to: 0x...
====================================

Deployment Summary:
  Contract: FastPayCore
  Network: Base Sepolia (Testnet)
  Chain ID: 84532
  Address: 0x...

Explorer:
  https://sepolia.basescan.org/address/0x...

Next Steps:
  1. Verify contract on Basescan (if --verify flag used)
  2. Update agents/.env with FASTPAY_ADDRESS=0x...
  3. Fund test wallets with ETH (merchant) and USDC (customer)
  4. Run agent demo: cd agents && npm run demo
```

**Save the deployed address!** You'll need it for the agent demo.

### Verify Deployment

Visit the Basescan link from the output. You should see:
- ✅ Contract deployed successfully
- ✅ Contract source code verified (green checkmark)
- ✅ All functions visible in "Contract" tab

---

## Step 2: Configure Agent Demo

### Set Environment Variables

```bash
cd agents
cp .env.example .env
nano .env
```

Edit `.env`:
```bash
BASE_RPC_URL=https://sepolia.base.org
CHAIN_ID=84532

FASTPAY_ADDRESS=<deployed_contract_address_from_step_1>
USDC_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e

MERCHANT_PRIVATE_KEY=<your_merchant_wallet_private_key>
CUSTOMER_PRIVATE_KEY=<your_customer_wallet_private_key>

PAYMENT_AMOUNT=5.00
```

### Install Dependencies

```bash
npm install
```

---

## Step 3: Fund Test Wallets

### Check Balances

```bash
# Check merchant ETH balance
cast balance <merchant_address> --rpc-url https://sepolia.base.org

# Check customer USDC balance
cast call 0x036CbD53842c5426634e7929541eC2318f3dCF7e \
  "balanceOf(address)(uint256)" <customer_address> \
  --rpc-url https://sepolia.base.org
```

### Required Balances

- **Merchant:** At least 0.001 ETH (~10-20 payments worth of gas)
- **Customer:** At least 10 USDC (6 decimals = 10000000)

---

## Step 4: Run Agent Demo

### First Run (Will Approve USDC)

```bash
npm run demo
```

**Expected flow:**

1. **Initialize Agents**
   ```
   Step 1: Initialize Agents
   Merchant Agent: 0x...
   Customer Agent: 0x...
   FastPay Contract: 0x...
   ```

2. **Check Balances**
   ```
   Step 2: Initial Balances
   Merchant:
     ETH Balance: 0.01 ETH (for gas)
     Total Payments: 0
   Customer:
     USDC Balance: 10.0 USDC
     FastPay Allowance: 0.0 USDC
     Total Payments: 0
   ```

3. **Approve USDC (first time only)**
   ```
   Step 2.5: Approve USDC Spending
   Customer agent needs to approve FastPay contract to spend USDC...
   ✅ Approval transaction: 0x...
      View on Basescan: https://sepolia.basescan.org/tx/0x...
   ```

4. **Create Payment Request**
   ```
   Step 3: Merchant Creates Payment Request
   Merchant agent creates a payment request for $5.00...
   Payment Request:
     Amount: 5.00 USD
     Merchant: 0x...
     Customer: 0x...
     Expires At: ...
   ```

5. **Customer Signs (GASLESS)**
   ```
   Step 4: Customer Evaluates & Signs (GASLESS)
   Customer agent evaluating payment against spending policy...
   ✅ Payment approved by customer policy
   Customer agent signing payment authorization...
      (This is GASLESS - customer needs NO ETH!)
   Signature: 0x...
   💡 Key Innovation: Customer only signed a message (no gas, no transaction)
   ```

6. **Merchant Executes**
   ```
   Step 5: Merchant Executes Payment (PAYS GAS)
   Merchant agent executing pull payment on-chain...
      (Merchant broadcasts transaction and pays gas fees)
   ✅ Payment executed successfully!
   Transaction Hash: 0x...
   Block Number: 12345
   Gas Used: 100000
   🔗 View on Basescan: https://sepolia.basescan.org/tx/0x...
   ```

7. **Final Balances**
   ```
   Step 6: Final Balances
   Merchant:
     ETH Balance: 0.0099 ETH
     Total Payments: 1
     Change: +5.00 USDC
   Customer:
     USDC Balance: 5.0 USDC
     Total Payments: 1
     Change: -5.00 USDC
   ```

8. **Success Summary**
   ```
   ✅ Demo Complete - Pull Payment Success!
   Summary:
     1. Customer agent signed authorization (GASLESS)
     2. Merchant agent executed payment (PAID GAS)
     3. 5.00 USDC transferred from customer to merchant
     4. Total time: < 10 seconds
   ```

### Subsequent Runs

On subsequent runs, the USDC approval step will be skipped (already approved).

---

## Troubleshooting

### "Insufficient funds for gas"

**Problem:** Merchant wallet doesn't have enough ETH

**Solution:**
```bash
# Get more Sepolia ETH from faucet
# https://www.alchemy.com/faucets/base-sepolia
```

### "Insufficient balance"

**Problem:** Customer wallet doesn't have enough USDC

**Solution:**
```bash
# Get Sepolia USDC by swapping on Uniswap (Base Sepolia)
# USDC Address: 0x036CbD53842c5426634e7929541eC2318f3dCF7e
```

### "FASTPAY_ADDRESS not set"

**Problem:** Forgot to update `.env` with deployed contract address

**Solution:**
```bash
cd agents
nano .env
# Add: FASTPAY_ADDRESS=0x...
```

### "Payment expired"

**Problem:** Payment request expired (default: 3 minutes)

**Solution:** Just run the demo again. Each run creates a new payment request.

### "Nonce already used"

**Problem:** Trying to execute the same payment twice

**Solution:** This is expected - replay protection working! Run demo again for a new payment.

### "Invalid signature"

**Problem:** Wrong customer wallet signed, or wrong chain ID

**Solution:**
- Verify `CUSTOMER_PRIVATE_KEY` matches expected customer address
- Verify `CHAIN_ID=84532` in `.env`
- Verify deployed contract is on Base Sepolia

---

## Verification Checklist

After successful demo run:

- [ ] Contract deployed to Base Sepolia
- [ ] Contract verified on Basescan
- [ ] Merchant wallet has ETH for gas
- [ ] Customer wallet has USDC
- [ ] Customer approved FastPay to spend USDC
- [ ] Payment executed successfully
- [ ] Transaction visible on Basescan
- [ ] Balances updated correctly
- [ ] Demo runs in < 10 seconds

---

## Next Steps

### For Production (Base Mainnet)

1. Test thoroughly on Sepolia first
2. Update `.env` files to use mainnet:
   ```bash
   BASE_RPC_URL=https://mainnet.base.org
   CHAIN_ID=8453
   USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
   ```
3. Deploy to mainnet:
   ```bash
   forge script script/Deploy.s.sol:DeployScript \
     --rpc-url base \
     --broadcast \
     --verify
   ```

### For Hackathon Submission

1. ✅ Deploy to Sepolia (this guide)
2. 📹 Record demo video showing the agent-to-agent payment
3. 📝 Write README.md and SUBMISSION.md
4. 🚀 Submit to OpenClaw hackathon

---

## Quick Reference

**Network:** Base Sepolia
**Chain ID:** 84532
**RPC:** https://sepolia.base.org
**Explorer:** https://sepolia.basescan.org
**USDC:** 0x036CbD53842c5426634e7929541eC2318f3dCF7e

**Faucets:**
- ETH: https://www.alchemy.com/faucets/base-sepolia
- USDC: Swap on Uniswap Base Sepolia

**Gas Costs:**
- Deploy contract: ~1,500,000 gas (~0.0015 ETH)
- USDC approval: ~46,000 gas (~0.00005 ETH)
- Execute payment: ~100,000 gas (~0.0001 ETH)

---

**Ready to deploy!** 🚀

Start with Step 1: Deploy the smart contract.
