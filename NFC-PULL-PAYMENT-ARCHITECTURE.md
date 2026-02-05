# NFC Tap Payments with Pull Payment Architecture

## The Problem

**Current FastPay Smart Contract Requirement:**
```javascript
// Merchant must know customer address upfront
const payment = await merchantAgent.createPayment(
  customerAddress,  // ⚠️ Unknown at tap time!
  usdcAddress,
  "5.00"
);
```

**Physical POS Scenario:**
```
Customer walks into coffee shop
Customer taps phone on terminal
❓ Terminal doesn't know customer's wallet address yet
❓ How to create pull payment authorization?
```

---

## Solution 1: Two-Phase NFC Protocol (Recommended)

### **Phase 1: Discovery (NFC Read)**

Terminal reads customer's wallet address from NFC tag/app:

```
[Customer Phone NFC]  →  [Terminal NFC Reader]
      Transmits: { walletAddress: "0x123..." }
```

**NFC Data Format (NDEF record):**
```json
{
  "protocol": "fastpay-v1",
  "walletAddress": "0x44b85A0E6406601884621a894E0dDf16CFA6f308",
  "supportedTokens": ["USDC", "USDT"],
  "chainId": 8453
}
```

### **Phase 2: Payment Request (NFC Write or QR)**

Terminal creates payment for discovered address and transmits back:

**Option A: NFC Write-back**
```
[Terminal]  →  [Customer Phone]
Writes payment request to phone's NFC tag
Customer's wallet app auto-detects and prompts for signature
```

**Option B: QR Code Fallback**
```
Terminal displays QR code containing:
{
  payment: { merchant, customer: "0x123...", amount, ... },
  requestId: "uuid"
}

Customer scans QR → Wallet opens → Signs → Returns signature
```

### **Complete Flow:**

```
┌─────────────┐                           ┌──────────────┐
│   Customer  │                           │   Terminal   │
│    Phone    │                           │   (Merchant) │
└──────┬──────┘                           └──────┬───────┘
       │                                         │
       │  1. TAP (NFC Detect)                    │
       │────────────────────────────────────────>│
       │                                         │
       │  2. READ: { walletAddress: 0x... }     │
       │<────────────────────────────────────────│
       │                                         │
       │        Terminal creates payment for     │
       │        discovered wallet address        │
       │                                         │
       │  3. WRITE: Payment Request              │
       │<────────────────────────────────────────│
       │                                         │
       │     Phone detects payment request       │
       │     Wallet app prompts user             │
       │                                         │
       │  4. User approves signature             │
       │     (off-chain, gasless)                │
       │                                         │
       │  5. RETURN: Signature                   │
       │────────────────────────────────────────>│
       │                                         │
       │     Terminal executes pull payment      │
       │     (on-chain, merchant pays gas)       │
       │                                         │
       │  6. CONFIRM: Payment success            │
       │<────────────────────────────────────────│
       │                                         │
       │  Receipt displayed on both devices      │
       │                                         │
```

**Timing:** ~5-10 seconds total

### **Implementation:**

**Customer Wallet App (React Native):**
```javascript
import NfcManager, { NfcTech } from 'react-native-nfc-manager';

// When app is opened, start broadcasting wallet address
async function broadcastWalletAddress() {
  await NfcManager.start();
  await NfcManager.setNdefPushMessage({
    protocol: 'fastpay-v1',
    walletAddress: wallet.address,
    chainId: 8453
  });
}

// Listen for payment requests via NFC
NfcManager.setEventListener(NfcEvents.DiscoverTag, async (tag) => {
  const paymentRequest = parseNdefMessage(tag.ndefMessage);

  if (paymentRequest.protocol === 'fastpay-payment-request') {
    // Show payment approval UI
    const approved = await showPaymentApproval(paymentRequest.payment);

    if (approved) {
      // Sign payment (gasless!)
      const signature = await wallet.signTypedData(
        DOMAIN,
        PAYMENT_TYPES,
        paymentRequest.payment
      );

      // Write signature back to terminal
      await writeSignatureToNfc(signature);
    }
  }
});
```

**Terminal (Node.js + Python NFC):**
```javascript
// Python NFC reader detects tap
nfcReader.on('tag-detected', async (tag) => {
  // Read customer wallet address
  const customerData = parseNdef(tag);
  const customerAddress = customerData.walletAddress;

  // Create payment request for THIS customer
  const payment = await merchantAgent.createPayment(
    customerAddress,  // ✅ Now we know it!
    usdcAddress,
    currentSaleAmount
  );

  // Write payment request back to phone
  await nfcWriter.writeNdef({
    protocol: 'fastpay-payment-request',
    payment: payment,
    requestId: uuid()
  });

  // Wait for signature (via NFC or API callback)
  const signature = await waitForSignature(payment.nonce);

  // Execute payment
  const result = await merchantAgent.executePullPayment(payment, signature);

  console.log('Payment completed!', result.txHash);
});
```

---

## Solution 2: Generic Charge Contract (Alternative Architecture)

Modify smart contract to support **unclaimed charges** that any customer can pay:

### **Modified Contract:**

```solidity
// ALTERNATIVE: Two-contract system
contract FastPayCharges {
    struct GenericCharge {
        bytes32 chargeId;
        address merchant;
        address token;
        uint256 amount;
        uint256 createdAt;
        bool claimed;
    }

    mapping(bytes32 => GenericCharge) public charges;

    // Merchant creates charge WITHOUT knowing customer
    function createCharge(
        address token,
        uint256 amount
    ) external returns (bytes32 chargeId) {
        chargeId = keccak256(abi.encodePacked(
            msg.sender,
            token,
            amount,
            block.timestamp
        ));

        charges[chargeId] = GenericCharge({
            chargeId: chargeId,
            merchant: msg.sender,
            token: token,
            amount: amount,
            createdAt: block.timestamp,
            claimed: false
        });

        return chargeId;
    }

    // Customer claims and signs authorization
    function claimAndAuthorize(
        bytes32 chargeId,
        bytes calldata signature
    ) external returns (bool) {
        GenericCharge storage charge = charges[chargeId];
        require(!charge.claimed, "Already claimed");
        require(block.timestamp < charge.createdAt + 300, "Expired");

        // Create specific payment for msg.sender
        Payment memory payment = Payment({
            merchant: charge.merchant,
            customer: msg.sender,  // ✅ Customer is known NOW
            token: charge.token,
            amount: charge.amount,
            validUntil: block.timestamp + 60,
            nonce: chargeId
        });

        // Verify customer signed this specific payment
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(PAYMENT_TYPEHASH, payment))
        );
        address signer = digest.recover(signature);
        require(signer == msg.sender, "Invalid signature");

        // Execute payment
        IERC20(charge.token).transferFrom(msg.sender, charge.merchant, charge.amount);

        charge.claimed = true;
        emit PaymentExecuted(chargeId, charge.merchant, msg.sender, charge.token, charge.amount);

        return true;
    }
}
```

### **Flow with Generic Charges:**

```
1. Customer taps NFC
2. Terminal creates GENERIC charge (no customer address needed)
3. Terminal displays QR code with chargeId
4. Customer scans QR
5. Customer's wallet creates SPECIFIC payment (customer = wallet.address)
6. Customer signs payment
7. Customer broadcasts transaction (⚠️ CUSTOMER PAYS GAS!)
8. Payment completes
```

**Problem:** ❌ Customer pays gas (defeats main benefit of pull payments!)

---

## Solution 3: Hybrid - Discovery API + Pull Payment

Use NFC for discovery, API for payment relay:

```
1. Customer taps NFC → Terminal reads wallet address
2. Terminal creates pull payment for customer address
3. Terminal sends payment request to relay API
4. Customer's wallet polls relay API
5. Customer signs payment (gasless)
6. Customer sends signature to relay API
7. Terminal receives signature from relay
8. Terminal executes pull payment (pays gas)
```

**Benefits:**
- ✅ Customer still gasless
- ✅ Works with poor NFC write support
- ✅ Can work over internet (tap at store, sign at home)

**Downsides:**
- ❌ Requires internet connection
- ❌ Requires relay server infrastructure
- ❌ Privacy concerns (relay sees all payments)

---

## Solution 4: Keep Them Separate (Current Approach)

**Acknowledge that these are DIFFERENT use cases:**

### **FastPay Terminal (terminal/) - NFC POS**
- Use case: Physical retail, unknown customers
- Technology: Coinbase Commerce (PUSH payments)
- NFC role: Tap detection only (convenience)
- Payment flow: Customer scans QR → Opens Coinbase → Approves
- Gas: Customer pays (via Coinbase Commerce abstraction)

### **FastPay Contracts (contracts/) - Agent Commerce**
- Use case: Digital services, known counterparties
- Technology: Pull payment smart contract
- Customer: Known wallet addresses (API keys, registrations)
- Payment flow: Merchant creates → Customer signs → Merchant executes
- Gas: Merchant pays

**Why this makes sense:**
```
Physical POS needs:
✅ Work with walk-in customers (unknown)
✅ Work with any wallet (Coinbase, MetaMask, etc.)
✅ Familiar UX (QR scan)
✅ Coinbase handles compliance/KYC

Agent commerce needs:
✅ Gasless customer agents
✅ Programmatic approval (policies)
✅ Known counterparties (registered services)
✅ Merchant pays gas (can be factored into pricing)
```

---

## Recommended Architecture for NFC Pull Payments

**Best approach: Solution 1 (Two-Phase NFC)**

### **Phase 1 Implementation (MVP):**

1. **Customer Wallet App:**
   - Broadcasts wallet address via NFC (NDEF format)
   - Listens for payment requests
   - Prompts user to approve/sign
   - Returns signature via NFC or API

2. **Terminal Updates:**
   - Add NFC read capability (already have writer)
   - Read customer address on tap
   - Create pull payment for discovered address
   - Execute after receiving signature

3. **Smart Contract:**
   - Keep existing FastPayCore (no changes needed!)
   - Customer address is discovered before payment creation

### **Phase 2 Enhancement:**

4. **Relay Server (Optional):**
   - For customers without NFC write capability
   - Merchant uploads payment request
   - Customer polls for pending payments
   - Customer submits signature
   - Merchant retrieves signature

5. **Wallet Integration:**
   - WalletConnect support
   - Deep links for mobile wallets
   - Push notifications for payment requests

---

## Comparison Table

| Approach | Gasless Customer | NFC Simplicity | Unknown Customer | Complexity |
|----------|-----------------|----------------|------------------|------------|
| **Two-Phase NFC** | ✅ Yes | ⚠️ Medium (2 phases) | ✅ Yes | Medium |
| **Generic Charge** | ❌ No | ✅ Simple | ✅ Yes | Low |
| **Discovery API** | ✅ Yes | ✅ Simple | ✅ Yes | High |
| **Separate Systems** | ⚠️ Depends | ✅ Simple | ✅ Yes | Low |

---

## Implementation Roadmap

**Week 1-2: Proof of Concept**
- [x] FastPayCore smart contract deployed
- [x] Agent SDK working
- [x] Demo transaction successful
- [ ] NFC discovery protocol spec
- [ ] Mobile wallet prototype

**Week 3-4: NFC Integration**
- [ ] Update terminal to read NFC (customer address)
- [ ] Modify payment creation to use discovered address
- [ ] Test two-phase NFC flow
- [ ] Fallback to QR if NFC write fails

**Week 5-6: Mobile Wallet**
- [ ] React Native wallet app
- [ ] NFC address broadcasting
- [ ] Payment request detection
- [ ] Signature creation and transmission

**Week 7-8: Production**
- [ ] Relay API for non-NFC wallets
- [ ] WalletConnect integration
- [ ] Security audit
- [ ] Pilot with real merchant

---

## Conclusion

**For Hackathon:** Focus on agent-to-agent known counterparty model
**For Production NFC:** Implement two-phase NFC discovery protocol
**For Ecosystem:** Consider ERC proposal for pull payment standard

The key insight: **NFC tap provides customer discovery, then standard pull payment flow works!**
