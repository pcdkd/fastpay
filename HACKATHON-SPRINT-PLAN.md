# FastPay Hackathon MVP: 4-Day Sprint Plan

**Deadline:** February 8, 2025 - 12 PM PST
**Track:** Most Novel Smart Contract (OpenClaw USDC Hackathon)
**Goal:** Submit working pull payment smart contract with agent-to-agent demo

---

## 🎉 **CURRENT STATUS: Day 3 Complete!**

✅ **Day 1 (Feb 5):** Smart Contract Development - COMPLETE
✅ **Day 2 (Feb 6):** Agent SDK Development - COMPLETE
✅ **Day 3 (Feb 4):** Deployment & Testing - COMPLETE ⭐
⏳ **Day 4 (Feb 5-7):** Documentation & Submission - IN PROGRESS

**Live Contract:** `0xa6Dde921ef709471C61a52c0faAf47a97D59c35a` (Base Sepolia)
**Demo Transaction:** [View on Basescan](https://sepolia.basescan.org/tx/0xb6f03b7d263c151e3e47c2de3e0c0fbb5fdbb97f99aa4d190a60c071a8d093b4)

**See [STATUS.md](STATUS.md) and [DEPLOYMENT-SUCCESS.md](DEPLOYMENT-SUCCESS.md) for full details.**

---

## 🎯 Core Innovation

**Merchant agents execute payments, customer agents just sign (gasless for customers)**

### What We're Building

**ONE smart contract:**
- `FastPayCore.sol` (~250 lines)
- Pull payment execution
- EIP-712 signatures
- Nonce management
- Basic events

**ONE demo:**
- Two JavaScript agent scripts
- Agent-to-agent payment on Base mainnet
- Shows full flow with real transactions

**ONE submission:**
- 2-minute video
- GitHub repo
- Submission post to m/usdc

### What We're NOT Building (Future Work)

❌ Escrow contract
❌ Spending policy contract
❌ Reputation system
❌ NFC hardware integration
❌ Complex SDK
❌ UI/frontend
❌ Multiple payment tokens

---

## 📅 Day-by-Day Implementation Plan

### **Day 1 (Feb 5): Smart Contract** ⏰ 8-10 hours

#### Morning: Core Contract (4 hours)

**File: `contracts/FastPayCore.sol`**

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title FastPayCore
 * @notice Merchant-initiated pull payments for agent commerce
 * @dev Customer signs authorization, merchant executes and pays gas
 */
contract FastPayCore is EIP712, ReentrancyGuard {
    using ECDSA for bytes32;

    // ============ Types ============

    struct Payment {
        address merchant;
        address customer;
        address token;
        uint256 amount;
        uint256 validUntil;
        bytes32 nonce;
    }

    bytes32 private constant PAYMENT_TYPEHASH = keccak256(
        "Payment(address merchant,address customer,address token,uint256 amount,uint256 validUntil,bytes32 nonce)"
    );

    // ============ State ============

    mapping(bytes32 => bool) public usedNonces;
    mapping(address => uint256) public paymentCount;

    // ============ Events ============

    event PaymentExecuted(
        bytes32 indexed nonce,
        address indexed merchant,
        address indexed customer,
        address token,
        uint256 amount
    );

    // ============ Constructor ============

    constructor() EIP712("FastPay", "1") {}

    // ============ Core Function ============

    /**
     * @notice Execute pull payment (merchant calls this)
     * @param payment Payment details
     * @param signature Customer's EIP-712 signature
     */
    function executePullPayment(
        Payment calldata payment,
        bytes calldata signature
    ) external nonReentrant returns (bool) {
        // Validation
        require(msg.sender == payment.merchant, "Only merchant");
        require(block.timestamp <= payment.validUntil, "Expired");
        require(!usedNonces[payment.nonce], "Nonce used");

        // Verify signature
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(
                PAYMENT_TYPEHASH,
                payment.merchant,
                payment.customer,
                payment.token,
                payment.amount,
                payment.validUntil,
                payment.nonce
            ))
        );

        address signer = digest.recover(signature);
        require(signer == payment.customer, "Invalid signature");

        // Mark nonce as used
        usedNonces[payment.nonce] = true;

        // Execute transfer
        IERC20 token = IERC20(payment.token);
        require(
            token.transferFrom(payment.customer, payment.merchant, payment.amount),
            "Transfer failed"
        );

        // Update stats
        paymentCount[payment.merchant]++;
        paymentCount[payment.customer]++;

        emit PaymentExecuted(
            payment.nonce,
            payment.merchant,
            payment.customer,
            payment.token,
            payment.amount
        );

        return true;
    }

    // ============ View Functions ============

    function getPaymentHash(Payment calldata payment)
        external
        view
        returns (bytes32)
    {
        return _hashTypedDataV4(
            keccak256(abi.encode(
                PAYMENT_TYPEHASH,
                payment.merchant,
                payment.customer,
                payment.token,
                payment.amount,
                payment.validUntil,
                payment.nonce
            ))
        );
    }

    function verifySignature(
        Payment calldata payment,
        bytes calldata signature
    ) external view returns (bool, address) {
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(
                PAYMENT_TYPEHASH,
                payment.merchant,
                payment.customer,
                payment.token,
                payment.amount,
                payment.validUntil,
                payment.nonce
            ))
        );

        address signer = digest.recover(signature);
        return (signer == payment.customer, signer);
    }
}
```

**Deliverable:** ✅ Working Solidity contract (250 lines)

#### Afternoon: Tests (4 hours)

**File: `test/FastPayCore.t.sol`**

Tests to implement:
- testExecutePullPayment (happy path)
- testRejectExpiredPayment
- testRejectReusedNonce
- testRejectInvalidSignature
- testRejectUnauthorizedMerchant

#### Setup Files

**foundry.toml, .env.example, installation commands**

**End of Day 1 Deliverables:**
- ✅ FastPayCore.sol contract
- ✅ Test suite passing
- ✅ Foundry project configured

---

### **Day 2 (Feb 6): Agent Integration** ⏰ 6-8 hours

#### Morning: JavaScript Agent SDK (3 hours)

**File: `agents/AgentWallet.js`**

Core functions:
- createPayment() - merchant creates payment request
- executePullPayment() - merchant executes
- evaluatePayment() - customer evaluates against policy
- signPayment() - customer signs EIP-712
- handlePaymentRequest() - customer full flow

**Deliverable:** ✅ Agent SDK with merchant + customer functions

#### Afternoon: Agent Demo Script (3 hours)

**File: `agents/demo.js`**

Demo flow:
1. Initialize merchant and customer agents
2. Show initial balances
3. Merchant creates $5 payment request
4. Customer evaluates and signs (gasless)
5. Merchant executes (pays gas)
6. Show transaction on Basescan
7. Show final balances

**Deliverable:** ✅ Working agent demo script

**End of Day 2 Deliverables:**
- ✅ Agent SDK (JavaScript)
- ✅ Demo script
- ✅ Ready to test on Base mainnet

---

### **Day 3 (Feb 7): Deploy & Test** ⏰ 6 hours

#### Morning: Deploy to Base Mainnet (2 hours)

**File: `script/Deploy.s.sol`**

Deploy commands:
```bash
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url $BASE_RPC_URL \
  --broadcast \
  --verify
```

**Deliverable:** ✅ Contract deployed and verified on Base

#### Afternoon: Test & Debug (4 hours)

**Setup test wallets:**
- Merchant wallet (needs ETH for gas)
- Customer wallet (needs USDC only, NO ETH!)

**Run demo:**
```bash
cd agents
npm install
npm run demo
```

**Debug checklist:**
- [ ] Customer has USDC approval for FastPay contract
- [ ] Merchant has ETH for gas
- [ ] Payment signature is valid
- [ ] Transaction broadcasts successfully
- [ ] Balances update correctly

**Deliverable:** ✅ Working end-to-end demo on Base mainnet

---

### **Day 4 (Feb 8 - DEADLINE DAY): Document & Submit** ⏰ 8 hours

#### Morning: Documentation (3 hours)

**File: `README.md`**

Sections:
- The Problem (agent commerce overhead)
- The Solution (pull payments)
- Why This Matters for Agents
- Smart Contract Architecture
- Live Demo
- Quick Start
- Use Cases
- Gas Cost Analysis
- Comparison to Existing Standards
- Future Roadmap

**Deliverable:** ✅ Professional README with clear value prop

#### Late Morning: Video Demo (2 hours)

**Demo Script (2 minutes):**

```
[0:00-0:15] Problem Statement
[0:15-0:30] Solution
[0:30-1:15] Live Demo (run agents/demo.js)
[1:15-1:45] Key Innovation (show contract code)
[1:45-2:00] Call to Action
```

**Recording setup:**
- Use Loom or OBS
- Terminal with large, readable font
- Basescan transaction in browser

**Deliverable:** ✅ 2-minute demo video

#### Afternoon: Submission (3 hours)

**File: `SUBMISSION.md`**

Complete submission with:
- Track selection
- Summary
- Smart contract innovation
- Deployed contract details
- Demo video link
- Use cases
- Comparison table
- Future work
- Team info
- All links

**Submission Post to m/usdc:**

```
🤖 FastPay Pull Payment Protocol - Agent Commerce Infrastructure

The first merchant-initiated payment system optimized for AI agents on Base.

🎯 The Problem
Current crypto payments force customer agents to pay gas fees and construct
transactions. This operational overhead makes autonomous commerce impractical.

💡 The Solution
FastPay inverts the flow. Customer agents sign authorization (gasless).
Merchant agents execute and pay gas. Simple. Fast. Autonomous.

[Continue with contract details, demo link, use cases...]

#AgenticCommerce #USDC #Base #OpenClaw
```

**Deliverable:** ✅ Complete submission document + published post

---

## 📦 Final Deliverables Checklist

### Smart Contract
- [ ] FastPayCore.sol deployed to Base mainnet
- [ ] Contract verified on Basescan
- [ ] Test suite passing (3+ tests)
- [ ] Gas-optimized (<100k gas per payment)

### Agent Integration
- [ ] AgentWallet.js SDK
- [ ] Demo script (agents/demo.js)
- [ ] Successful test transaction on Base
- [ ] Clear console output showing flow

### Documentation
- [ ] README.md with clear value prop
- [ ] Code comments explaining innovation
- [ ] SUBMISSION.md with all details
- [ ] .env.example for easy setup

### Demo
- [ ] 2-minute video showing live demo
- [ ] Screen recording of actual Base transaction
- [ ] Clear explanation of innovation
- [ ] Professional audio/video quality

### Submission
- [ ] Submission post to m/usdc
- [ ] GitHub repo public
- [ ] All links working
- [ ] Submitted before Feb 8 12 PM PST

---

## 🎯 Success Criteria

**Minimum (Must Have):**
- ✅ Working smart contract on Base mainnet
- ✅ One successful demo transaction
- ✅ Clear explanation of pull payment innovation
- ✅ 2-minute video demo
- ✅ Submitted on time

**Good (Should Have):**
- ✅ Clean, well-commented code
- ✅ Professional documentation
- ✅ Multiple demo transactions showing reliability
- ✅ Clear agent SDK examples

**Excellent (Nice to Have):**
- ✅ Gas analysis showing efficiency
- ✅ Comparison to EIP-3009 and other standards
- ✅ Multiple use case examples
- ✅ Community engagement on submission post

---

## 💬 Positioning Strategy

### "What's novel?"

"Three things make FastPay novel for agent commerce:

1. **Inverted payment flow** - Customer just signs, merchant executes. Traditional crypto requires customer to execute and pay gas.

2. **Gasless customer agents** - Agents only need USDC. No ETH for gas. No gas price monitoring. No transaction construction complexity.

3. **Agent-native design** - Built specifically for programmatic spending policies and autonomous approval. Not a general payment system retrofitted for agents."

### "Why not use EIP-3009?"

"EIP-3009 is token-specific - only works if the token contract implements it. FastPay works with ANY ERC-20. Also, EIP-3009 doesn't have agent-specific features like spending policies or programmatic approval. It's infrastructure for humans, not agents."

### "Who would use this?"

"Three immediate use cases:

1. **API providers** doing micropayments with agent customers
2. **SaaS platforms** billing agent subscribers
3. **Agent marketplaces** for autonomous commerce

As the agent economy grows, this becomes fundamental infrastructure."

---

## Timeline Summary

| Day | Hours | Focus | Deliverable |
|-----|-------|-------|------------|
| Day 1 | 8-10 | Smart contract + tests | Working FastPayCore.sol |
| Day 2 | 6-8 | Agent SDK + demo | Working agent scripts |
| Day 3 | 6 | Deploy + test | Live on Base mainnet |
| Day 4 | 8 | Document + submit | Complete submission |

**Total: ~30 hours over 4 days**

---

## Key Constraints

**RESIST SCOPE CREEP:**
- No escrow contract
- No spending policy contract
- No reputation system
- No NFC hardware integration
- No complex UI

**FOCUS ON:**
- One working smart contract
- Clear demonstration of pull payment innovation
- Professional documentation
- Compelling agent commerce narrative

---

**The key to success: Stay focused on the core innovation (pull payments for gasless agent commerce) and execute cleanly.**
