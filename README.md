# FastPay ⚡

**Tap-to-pay crypto payments in under 10 seconds.**

## Problem

Current crypto point-of-sale systems are broken:
- Customer scans QR code
- Manually enters payment amount
- Calculates gas fees
- Merchant typically reconciles offline

**Result:** Nobody uses crypto for coffee.

## Solution

Make crypto payments work like Google/Apple Pay:

1. **Merchant enters amount** on terminal
2. **Terminal creates charge** via Coinbase Commerce
3. **Customer scans QR OR taps phone** (both work)
4. **Wallet opens** with payment details pre-filled
5. **Customer approves** with one tap
6. **Confirmed on-chain** in <10 seconds

**Result:** Feels like Google/Apple Pay. Costs like crypto.

### How NFC Improves UX

The NFC tap is a **convenience feature** that provides the same UX as credit card terminals:
- Customer taps phone → Terminal detects tap → Associates with pending charge
- Customer's wallet app opens payment page (same as QR scan)
- Both paths lead to same Coinbase Commerce hosted checkout
- No data transferred via NFC - just tap detection for UX

## Tech Stack

- **NFC Hardware:** PN532 module in reader mode (tap detection)
- **Payment Processing:** Coinbase Commerce (charge creation, hosted checkout, webhooks)
- **Blockchain:** Base L2 (fast, cheap settlement)
- **Token:** USDC (stable, no volatility)
- **Terminal:** Node.js (business logic) + Python (NFC hardware bridge)
- **Customer App:** Any wallet with Base L2 support (MetaMask, Coinbase Wallet, etc.)

## Status

🚧 **In Development** (Week 2 of 12)

Phase 1 progress - Building terminal software:
- [x] Hardware setup (PN532 NFC module + USB-UART converter)
- [x] NFC communication working (Adafruit library, firmware v1.6 detected)
- [x] Phone tap detection tested (reader mode validated)
- [x] Architecture finalized (reader mode + Coinbase Commerce)
- [ ] Terminal software (Node.js + Python bridge)
- [ ] First payment completed on Base testnet
- [ ] Merchant pilot (3 locations)

Follow the build: @pxaxm.base.eth or [@pcdkd](https://twitter.com/pcdkd)

## Why This Matters

**For Merchants:**
- 0.01% fees (vs 3% for credit cards)
- Instant settlement (vs 2-7 days)
- No chargebacks
- Global payments (no forex fees)

**For Customers:**
- Fast end-to-end process (10 seconds vs 60+ seconds)
- Familiar UX (tap like a credit card)
- Self-custodial (no middleman)
- Works with existing wallets (MetaMask, Coinbase Wallet)

## Roadmap

- **Phase 1 (Weeks 1-4):** Desktop terminal POC
- **Phase 2 (Weeks 5-8):** Merchant pilots + POS integration
- **Phase 3 (Months 3-6):** Phone dongle ($25 plug-in device)
- **Phase 4 (Months 6-12):** Custom hardware at scale

## Get Involved

This is an open-source project. Contributions welcome.

- **Merchants:** Want to pilot? [DM me](https://twitter.com/pcdkd)
- **Developers:** Star the repo, issues coming soon
- **Investors:** Not happening

## License

## License

MIT. Fork it, improve it, deploy it.

If you're building something similar, I'd love to collaborate.

Commercial partnerships available for:
- White-label terminal deployments
- POS system integrations
- Custom hardware manufacturing

---

*Making crypto payments work IRL. Built on [Base](https://base.org).*
