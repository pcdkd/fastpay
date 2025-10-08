# FastPay ⚡

**Tap-to-pay crypto payments in under 10 seconds.**

## Problem

Current crypto point-of-sale systems are broken:
- Customer scans QR code
- Manually enters payment amount
- Calculates gas fees
- Merchant typically reconciles offline

**Result:** Nobody uses crypto for coffee.

## Hypothesis

Invert the flow. Make crypto payments work like Google/Apple Pay:

1. **Merchant creates** payment request (amount, merchant address, signed)
2. **Customer taps** phone on NFC terminal
3. **Wallet pre-fills** transaction (no manual entry)
4. **Customer approves** with one tap
5. **Confirmed on-chain** in <10 seconds

**Result:** Feels like Google/Apple Pay. Costs like crypto.

## Tech Stack

- **NFC Hardware:** PN532 module for tap-to-pay
- **Blockchain:** Base L2 (fast, cheap settlement)
- **Token:** USDC (stable, no volatility)
- **Protocol:** Coinbase Commerce Payments (escrow + refunds)
- **Signing:** EIP-712 (cryptographic payment requests)

## Status

🚧 **In Development** (Week 1 of 12)

Currently building Phase 1 proof-of-concept:
- [x] Hardware setup (PN532 NFC module + USB-UART converter)
- [x] NFC communication working (Adafruit library, firmware v1.6 detected)
- [x] Phone tap detection tested
- [ ] Card emulation implementation (in progress)
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
