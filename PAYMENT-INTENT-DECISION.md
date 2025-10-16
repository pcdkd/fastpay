# FastPay Payment Intent Architecture - Phase 1 Decision

**Date:** October 14, 2025
**Status:** APPROVED
**Decision:** Use Coinbase Commerce hosted checkout (no custom payment intents needed)

---

## Executive Summary

**We do NOT need to develop a custom payment intent standard for Phase 1.**

Coinbase Commerce already provides:
- ✅ Universal hosted checkout page (`hosted_url`)
- ✅ Deep links for major wallets (MetaMask, Coinbase Wallet, Rainbow)
- ✅ WalletConnect fallback for other wallets
- ✅ Transaction pre-population (amount, recipient, token)
- ✅ Payment verification and webhook confirmations

**NFC role:** Tap detection for UX + optional URL delivery via physical tag

---

## Architecture Options Evaluated

### Option A: Coinbase Commerce Hosted Checkout (SELECTED ✅)

**How it works:**
```
1. Terminal creates charge via Coinbase Commerce API
   → Returns: hosted_url (https://commerce.coinbase.com/charges/ABC123)

2. Terminal displays QR code with hosted_url

3. Customer either:
   a) Scans QR code → Opens Coinbase checkout in browser
   b) Taps phone → PN532 detects tap, customer scans QR
   c) (Optional) Taps NFC tag → Phone reads URL, auto-opens checkout

4. Coinbase Commerce checkout page:
   - Shows merchant name, amount, deadline
   - Provides "Pay with [Wallet]" buttons
   - Deep links to customer's preferred wallet
   - Pre-fills transaction parameters

5. Customer approves in wallet → Transaction broadcasts to Base L2

6. Coinbase webhook fires → Terminal receives confirmation
```

**Pros:**
- ✅ **No custom standards needed** - Coinbase handles everything
- ✅ **Works with all major wallets** - MetaMask, CB Wallet, Rainbow, Trust, etc.
- ✅ **Professional UI** - Coinbase's checkout page is polished
- ✅ **Reliable** - Proven infrastructure (used by thousands of merchants)
- ✅ **Webhook confirmations** - Real-time payment notifications
- ✅ **Fast implementation** - Just integrate API (Week 2)

**Cons:**
- ❌ Depends on Coinbase Commerce service (vendor lock-in)
- ❌ Less customization of checkout UI
- ❌ Customer sees "Coinbase Commerce" branding

**Verdict:** **Perfect for Phase 1 POC.** Gets us to market fast with proven infrastructure.

---

### Option B: Custom Payment Intent + WalletConnect

**How it would work:**
```
1. Terminal creates custom payment request:
   {
     "merchant": "Alice's Coffee",
     "amount": "5.00 USDC",
     "address": "0xMERCHANT",
     "chainId": 8453,
     "deadline": 1728000180
   }

2. Terminal writes JSON to NFC tag

3. Customer taps → FastPay companion app opens

4. Companion app displays payment details

5. Customer taps "Pay" → WalletConnect initiates

6. Customer's wallet opens (MetaMask, CB Wallet, etc.)

7. Wallet shows pre-filled transaction

8. Customer approves → Broadcasts to Base L2

9. Terminal monitors blockchain for payment
```

**Pros:**
- ✅ Full control over UX (custom payment UI)
- ✅ No vendor dependency (self-hosted)
- ✅ Works with any WalletConnect-compatible wallet

**Cons:**
- ❌ **Requires custom companion app** (iOS + Android development)
- ❌ **More complex** (WalletConnect session management)
- ❌ **Slower to market** (2-3 weeks extra development)
- ❌ **Customer friction** (need to install FastPay app)
- ❌ **Blockchain monitoring required** (no webhooks)

**Verdict:** **Better for Phase 2+** when we want full control and custom features.

---

### Option C: EIP-681 Deep Links (Direct to Wallet)

**How it would work:**
```
1. Terminal creates EIP-681 URL:
   ethereum:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913@8453/transfer?
     address=0xMERCHANT&
     uint256=5000000

2. Write URL to NFC tag

3. Customer taps → Phone reads URL

4. Android/iOS attempts to open URL

5. IF customer has compatible wallet installed:
   → Wallet opens with transaction pre-filled
   ELSE:
   → Browser opens (broken experience)

6. Customer approves → Broadcasts to Base L2

7. Terminal monitors blockchain for payment
```

**Pros:**
- ✅ No companion app needed
- ✅ Direct to wallet (one less step)
- ✅ Standard format (EIP-681)

**Cons:**
- ❌ **Limited wallet support** (MetaMask partial, CB Wallet inconsistent)
- ❌ **No merchant context** (wallet doesn't show "Alice's Coffee")
- ❌ **Fragile** (depends on OS URL handling)
- ❌ **No payment verification** (need to monitor blockchain)
- ❌ **Poor fallback** (if wallet not installed, customer confused)

**Verdict:** **Not reliable enough for Phase 1.** Could add as enhancement in Phase 2.

---

## Phase 1 Decision: Coinbase Commerce

### Implementation Details

**Charge Creation:**
```javascript
// terminal/src/commerce.js
const charge = await commerceClient.createCharge({
  amount: 5.00,
  currency: 'USD',
  description: 'Coffee purchase',
  metadata: {
    terminal_id: 'terminal_001',
    tap_uid: null  // Filled when customer taps
  }
});

// Returns:
{
  id: 'ABC123',
  hosted_url: 'https://commerce.coinbase.com/charges/ABC123',
  addresses: {
    base: '0xDEPOSIT_ADDRESS'
  },
  pricing: {
    local: { amount: '5.00', currency: 'USD' },
    usdc: { amount: '5.000000', currency: 'USDC' }
  },
  expires_at: '2025-10-14T12:30:00Z'
}
```

**QR Code Display:**
```javascript
// terminal/src/payment.js
const qr = await QRCode.toString(charge.hosted_url, {
  type: 'terminal',
  small: true
});

console.log('\n📱 Scan QR code to pay:');
console.log(qr);
console.log(`\n🔗 ${charge.hosted_url}`);
```

**NFC Reader (Tap Detection):**
```python
# terminal/scripts/nfc_reader.py
# Detects when customer taps phone on PN532 module
uid = pn532.read_passive_target(timeout=0.5)
if uid:
    uid_hex = ''.join([f'{b:02X}' for b in uid])
    emit_event('tap', uid=uid_hex)
```

**Webhook Handling:**
```javascript
// terminal/src/webhook.js
app.post('/webhooks/coinbase', (req, res) => {
  const event = Webhook.verifyEventBody(
    req.rawBody,
    req.headers['x-cc-webhook-signature'],
    process.env.COINBASE_WEBHOOK_SECRET
  );

  if (event.type === 'charge:confirmed') {
    console.log('✅ Payment confirmed!');
    paymentManager.completePurchase(event.data.id);
  }

  res.sendStatus(200);
});
```

**Payment Flow:**
```
Merchant enters amount
      ↓
Terminal creates charge via Coinbase API (2s)
      ↓
Display QR code + "Tap or Scan to Pay"
      ↓
Customer action (choose one):
  a) Scan QR → Opens Coinbase checkout
  b) Tap phone → PN532 detects, customer scans QR
      ↓
Coinbase Commerce checkout page opens
      ↓
Customer selects wallet (MetaMask, CB Wallet, etc.)
      ↓
Wallet deep link fires, transaction pre-filled
      ↓
Customer approves → Broadcasts to Base L2
      ↓
Webhook fires → Terminal shows "Payment Confirmed!" (<10s total)
```

---

## Optional Enhancement: NFC Tag Auto-Open

**Problem:** Customer still needs to scan QR after tapping (two actions)

**Solution:** Add physical NTAG215 tag to terminal that contains payment URL

**How it works:**
```
1. Terminal creates Coinbase charge (gets hosted_url)

2. Terminal writes hosted_url to physical NTAG215 tag (2s)
   → Tag is mounted on terminal surface

3. Customer taps phone on terminal

4. TWO things happen simultaneously:
   a) PN532 reader (underneath tag) detects tap via reader mode
   b) Phone NFC reads URL from tag, auto-opens in browser

5. Browser loads Coinbase Commerce checkout

6. Customer selects wallet, completes payment

7. Webhook confirms → Terminal shows success
```

**Implementation:**
```python
# terminal/scripts/nfc_writer.py (NEW - optional enhancement)
import ndef

def write_payment_url(hosted_url):
    """Write Coinbase Commerce URL to NTAG215 tag"""
    # Create NDEF URL record
    record = ndef.UriRecord(hosted_url)
    message = ndef.Message(record)

    # Write to tag
    pn532.SAM_configuration()  # Writer mode
    uid = pn532.read_passive_target(timeout=5)

    if uid:
        # Write NDEF message to tag pages
        ndef_data = bytes(message)
        for page in range(4, 40):  # NTAG215 user pages
            pn532.ntag2xx_write_block(page, ndef_data[offset:offset+4])

        print(f"✅ Payment URL written to tag")
```

**Hardware needed:**
- NTAG215 NFC tag stickers (~$1 each, rewritable)
- Mount tag on terminal surface (above PN532 module)
- PN532 can both read (detect tap) and write (update URL)

**Benefits:**
- ✅ True "tap to pay" UX (customer only taps once)
- ✅ No QR scan needed (phone auto-opens payment page)
- ✅ Feels exactly like credit card tap-to-pay

**Trade-offs:**
- Adds 2 seconds to payment prep (writing URL to tag)
- Requires physical tags (~$10 for 10-pack)
- Tag must be rewritten for each new charge

**Decision:** **Add in Week 3 as enhancement** (after core flow works with QR)

---

## Phase 2+ Considerations

### Custom Payment Intent Standard (Months 3-6)

**When to build:**
- After proving Phase 1 POC works
- When we want to reduce Coinbase Commerce dependency
- When we need custom checkout UI/branding

**What to propose:**
```json
{
  "version": "1.0",
  "type": "fastpay_payment_request",
  "chainId": 8453,
  "merchant": {
    "address": "0xMERCHANT",
    "name": "Alice's Coffee Shop",
    "logo": "https://coffeeshop.com/logo.png",
    "signature": "0x..."  // EIP-712 signature
  },
  "payment": {
    "token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "amount": "5000000",
    "currency": "USDC",
    "fiatAmount": "5.00",
    "fiatCurrency": "USD",
    "description": "Grande Latte",
    "deadline": 1728000180,
    "nonce": "abc123"
  },
  "paymaster": {
    "address": "0xPAYMASTER",
    "sponsorGas": true
  }
}
```

**Deep link format:**
```
fastpay://pay?request=<base64EncodedJSON>

OR (for broader compatibility):

https://pay.fastpay.xyz/?request=<base64EncodedJSON>
```

**Companion app responsibilities:**
1. Read payment request from NFC or URL parameter
2. Verify merchant signature (EIP-712)
3. Display payment details (merchant name, amount, item)
4. Initiate WalletConnect to customer's preferred wallet
5. Monitor blockchain for payment confirmation
6. Store receipt/transaction history

**Path to adoption:**
- Build companion app (iOS + Android)
- Propose EIP for payment request standard
- Engage with wallet vendors (MetaMask, CB Wallet, Rainbow)
- Gradually reduce Coinbase Commerce dependency

---

## Summary

### Phase 1 (Weeks 2-4): Coinbase Commerce
- ✅ Use Coinbase hosted checkout
- ✅ QR code primary, NFC tap = UX enhancement
- ✅ Optional: NFC tag auto-open (Week 3)
- ✅ Fast to market, proven infrastructure

### Phase 2 (Months 3-6): Hybrid Approach
- Add companion app (WalletConnect support)
- Keep Coinbase Commerce as fallback
- Propose FastPay payment request standard

### Phase 3 (Months 6-12): Native Wallet Support
- Wallet vendors adopt FastPay payment request format
- Direct deep links (no companion app needed)
- Self-hosted payment verification

---

## Action Items

**Week 2:**
- [x] Document payment intent decision (this file)
- [ ] Implement Coinbase Commerce integration (`terminal/src/commerce.js`)
- [ ] QR code generation for hosted URLs
- [ ] Webhook handler for payment confirmations

**Week 3:**
- [ ] Test end-to-end with real Coinbase Commerce account
- [ ] Optional: Add NFC tag writing for auto-open UX
- [ ] Measure payment completion time (<10s target)

**Phase 2 Planning:**
- [ ] Research companion app frameworks (React Native + Expo)
- [ ] Draft FastPay payment request EIP
- [ ] Engage with wallet vendor developer relations

---

**Status:** No custom payment intent development needed for Phase 1.
**Next:** Proceed with terminal implementation (Coinbase Commerce API integration).
