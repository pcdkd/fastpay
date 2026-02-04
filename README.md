# FastPay ⚡

**Pull Payment Protocol for AI Agent Commerce on Base L2**

[![Deployed on Base](https://img.shields.io/badge/Deployed-Base%20Sepolia-blue)](https://sepolia.basescan.org/address/0xa6Dde921ef709471C61a52c0faAf47a97D59c35a)
[![Hackathon](https://img.shields.io/badge/OpenClaw-USDC%20Hackathon-green)](https://openclaw.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🎯 **Hackathon Track:** Most Novel Smart Contract
🚀 **Status:** ✅ Deployed & Tested on Base Sepolia
📅 **Deadline:** February 8, 2026 - 12 PM PST

---

## 🎯 The Problem

**AI agents can't easily make payments in crypto.**

Current crypto payment flow:
- ❌ Customer must have ETH for gas fees
- ❌ Customer constructs and broadcasts transaction
- ❌ Customer monitors gas prices and manages nonces
- ❌ Complex transaction building interface

**Result:** AI agents need operational overhead (ETH, gas monitoring, transaction construction) just to spend USDC.

---

## 💡 The Solution

**FastPay inverts the payment flow: Customer signs, merchant executes.**

```
Traditional Crypto:           FastPay Pull Payments:
Customer → Constructs TX      Customer → Signs Message (gasless)
Customer → Pays Gas          Merchant → Broadcasts TX
Customer → Broadcasts        Merchant → Pays Gas
                             ✅ Customer needs ONLY USDC!
```

### Key Innovation

1. **Customer Agent:** Signs EIP-712 authorization (off-chain, gasless)
2. **Merchant Agent:** Executes pull payment (on-chain, pays gas)
3. **Smart Contract:** Verifies signature, transfers USDC

**Perfect for autonomous agents:** Simple signing interface, no ETH required, no gas monitoring.

---

## 🚀 Live Deployment

### **Deployed Contract**
- **Address:** `0xa6Dde921ef709471C61a52c0faAf47a97D59c35a`
- **Network:** Base Sepolia Testnet (Chain ID: 84532)
- **Status:** ✅ Verified on Basescan
- **Explorer:** [View on Basescan](https://sepolia.basescan.org/address/0xa6Dde921ef709471C61a52c0faAf47a97D59c35a)

### **Live Demo Transaction**
- **Transaction:** [View on Basescan](https://sepolia.basescan.org/tx/0xb6f03b7d263c151e3e47c2de3e0c0fbb5fdbb97f99aa4d190a60c071a8d093b4)
- **Amount:** 0.50 USDC transferred
- **Gas Used:** 137,691 gas (~$0.0006)
- **Customer Cost:** $0.00 (gasless!)
- **Time:** < 10 seconds

---

## 🏗️ Architecture

### Three-Component System

```
┌─────────────────────────────────────────────────────────────┐
│                    FastPay Ecosystem                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Smart Contract (contracts/)                             │
│     ├─ FastPayCore.sol - Pull payment execution            │
│     ├─ EIP-712 signature verification                       │
│     ├─ Nonce-based replay protection                        │
│     └─ Gas optimized (~137k gas per payment)                │
│                                                              │
│  2. Agent SDK (agents/)                                     │
│     ├─ MerchantAgent - Creates & executes payments          │
│     ├─ CustomerAgent - Signs authorizations (gasless)       │
│     └─ Policy engine for autonomous approval                │
│                                                              │
│  3. Terminal (terminal/) - Legacy NFC POS System            │
│     └─ Separate push payment system (not part of hackathon) │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Smart Contract:** Solidity 0.8.24, OpenZeppelin, Foundry
- **Agent SDK:** JavaScript, ethers.js v6, EIP-712
- **Blockchain:** Base L2 (fast, cheap, EVM-compatible)
- **Token:** USDC (works with any ERC-20)

---

## 📊 Hackathon Progress

- ✅ **Day 1 (Feb 5):** Smart Contract - FastPayCore.sol deployed
- ✅ **Day 2 (Feb 6):** Agent SDK - MerchantAgent & CustomerAgent classes
- ✅ **Day 3 (Feb 4):** Deployment & Testing - Live on Base Sepolia ⭐
- ⏳ **Day 4 (Feb 5-7):** Documentation & Submission

**See:** [STATUS.md](STATUS.md) for detailed progress
**See:** [DEPLOYMENT-SUCCESS.md](DEPLOYMENT-SUCCESS.md) for deployment details

---

## 🚀 Quick Start

### Run the Demo

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd fastpay

# 2. Set up contracts (optional - already deployed)
cd contracts
forge build
forge test

# 3. Run agent demo
cd ../agents
npm install
cp .env.example .env
# Edit .env with your wallet keys
npm run demo
```

### Deploy Your Own

```bash
cd contracts
cp .env.example .env
# Add your PRIVATE_KEY and ETHERSCAN_API_KEY
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url base_sepolia \
  --broadcast \
  --verify
```

**See:** [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) for full deployment instructions

---

## 📈 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Gas per Payment** | 137,691 | ~$0.0006 on Base L2 |
| **Customer Cost** | $0.00 | Completely gasless after approval |
| **Settlement Time** | < 10 seconds | End-to-end |
| **Token Support** | Any ERC-20 | USDC, USDT, DAI, etc. |
| **Security** | EIP-712 + Nonces | Replay protection |

---

## 🎯 Use Cases for AI Agents

1. **API Micropayments:** Agent pays for API calls with USDC (no ETH needed)
2. **SaaS Subscriptions:** Agent-to-agent recurring payments
3. **Agent Marketplaces:** Autonomous commerce between AI services
4. **Data Purchases:** Agents buy datasets with simple signatures
5. **Compute Resources:** Pay for cloud compute without gas overhead

---

## 🔐 Security Features

- ✅ **EIP-712 Typed Signatures:** Human-readable payment details
- ✅ **Nonce-Based Replay Protection:** Each payment uses unique nonce
- ✅ **ReentrancyGuard:** Prevents reentrancy attacks
- ✅ **Expiration Times:** Payments have validity windows
- ✅ **Signature Verification:** Customer must authorize every payment
- ✅ **Audited Patterns:** Uses OpenZeppelin contracts

---

## 📚 Documentation

- [STATUS.md](STATUS.md) - Current hackathon progress
- [DEPLOYMENT-SUCCESS.md](DEPLOYMENT-SUCCESS.md) - Deployment details & metrics
- [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) - Step-by-step deployment
- [HACKATHON-SPRINT-PLAN.md](HACKATHON-SPRINT-PLAN.md) - 4-day roadmap
- [contracts/README.md](contracts/README.md) - Smart contract documentation
- [agents/README.md](agents/README.md) - Agent SDK documentation
- [CLAUDE.md](CLAUDE.md) - AI assistant instructions (architecture reference)

---

## 🤝 Contributing

This is an open-source project built for the OpenClaw USDC Hackathon.

**Areas for contribution:**
- Additional ERC-20 token support
- Gas optimization
- Additional security features
- Frontend integrations
- Documentation improvements

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- Built for [OpenClaw USDC Hackathon](https://openclaw.com)
- Deployed on [Base L2](https://base.org)
- Uses [OpenZeppelin](https://openzeppelin.com) security patterns
- Powered by [Foundry](https://getfoundry.sh) for smart contract development

---

## 📞 Contact

- Twitter: [@pcdkd](https://twitter.com/pcdkd)
- Base: @pxaxm.base.eth

---

**🎉 FastPay: Enabling true autonomous agent commerce with pull payments on Base L2**
