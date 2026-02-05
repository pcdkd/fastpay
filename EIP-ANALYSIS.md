# FastPay & Ethereum Improvement Proposals (EIPs)

## Should FastPay Submit an EIP?

### Related Existing EIPs

**EIP-3009: Transfer With Authorization**
- Status: Final (widely adopted)
- What: Allows gasless token transfers via meta-transactions
- How: Token contract has `transferWithAuthorization()` function
- Limitation: **Token-specific** - only works if token implements EIP-3009
- Used by: Circle's USDC, other stablecoins
- Gas paid by: Relayer (could be merchant)

**EIP-2612: Permit**
- Status: Final
- What: Gasless ERC-20 approvals via signature
- How: `permit()` function sets allowance without gas
- Used by: Many modern ERC-20 tokens (Uniswap, Aave)
- Gas paid by: Whoever calls contract after permit

**EIP-4337: Account Abstraction**
- Status: Final
- What: Smart contract wallets, gasless transactions via bundlers
- How: UserOperations submitted to bundlers who pay gas
- Scope: Broader than just payments
- Gas paid by: Bundlers (can be sponsored)

**EIP-712: Typed Data Signing**
- Status: Final (widely adopted)
- What: Human-readable signature format
- How: Domain separator + typed struct hashing
- Used by: FastPay, most modern dApps
- Not payment-specific

### FastPay's Position in This Ecosystem

**What FastPay Is:**
- Application-level protocol using EIP-712
- Generic pull payment pattern
- Works with **any ERC-20 token** (not token-specific)
- Merchant-initiated, customer-authorized flow

**What FastPay Is NOT:**
- Core protocol change (doesn't need hard fork)
- Token standard (doesn't define new token behavior)
- Wallet standard (doesn't define wallet interface)

### EIP Submission Criteria

**Should FastPay be an EIP?** Let's evaluate:

| Criterion | FastPay Status | EIP Needed? |
|-----------|---------------|-------------|
| **Novel primitive?** | Uses existing EIP-712, no new cryptographic primitive | ❌ No |
| **Multiple implementations needed?** | Yes - any merchant/agent system could use this pattern | ✅ Yes |
| **Interface standardization?** | Having a standard `executePullPayment()` interface would help interop | ✅ Yes |
| **Cross-chain applicability?** | Yes - works on any EVM chain | ✅ Yes |
| **Competing approaches exist?** | Yes - EIP-3009, custom solutions | ✅ Yes (coordination value) |
| **Core protocol change?** | No - smart contract only | ❌ No |

### Recommendation: **ERC (Application-Level Standard)**

FastPay should be proposed as an **ERC (Ethereum Request for Comment)** rather than core EIP:

**Proposed: ERC-XXXX - Pull Payment Authorization**

```solidity
// IERC-XXXX: Pull Payment Standard
interface IPullPayment {
    struct Payment {
        address merchant;
        address customer;
        address token;
        uint256 amount;
        uint256 validUntil;
        bytes32 nonce;
    }

    event PaymentExecuted(
        bytes32 indexed nonce,
        address indexed merchant,
        address indexed customer,
        address token,
        uint256 amount
    );

    function executePullPayment(
        Payment calldata payment,
        bytes calldata signature
    ) external returns (bool);

    function verifySignature(
        Payment calldata payment,
        bytes calldata signature
    ) external view returns (bool valid, address signer);

    function usedNonces(bytes32 nonce) external view returns (bool);
}
```

### Benefits of Standardization

**For the Ecosystem:**
1. **Interoperability** - Wallets can recognize pull payment requests
2. **Security** - Audited reference implementation
3. **Tooling** - Libraries, UI components for pull payments
4. **Discovery** - Standard way for merchants to signal support

**For FastPay:**
1. **Legitimacy** - ERC number gives credibility
2. **Adoption** - Other projects might implement
3. **Feedback** - Community review improves design
4. **Documentation** - Forces clear specification

### Comparison to EIP-3009

| Feature | EIP-3009 | FastPay (Proposed ERC) |
|---------|----------|------------------------|
| **Scope** | Token-level (USDC implements it) | Contract-level (any ERC-20) |
| **Adoption barrier** | High (token must implement) | Low (deploy one contract) |
| **Flexibility** | Limited to transfer | Can add escrow, policies, etc. |
| **Gas model** | Relayer pays | Merchant pays |
| **Customer binding** | Yes (via authorization) | Yes (via payment struct) |
| **Nonce management** | Token contract | Payment contract |

**Key Advantage:** FastPay works with **existing USDC**, **existing USDT**, any ERC-20 - no token changes needed!

### Next Steps for EIP Submission

If you want to pursue this:

**1. Draft EIP (EIP-1 format)**
```markdown
---
eip: TBD
title: Pull Payment Authorization for Gasless Transactions
author: Your Name (@github)
discussions-to: https://ethereum-magicians.org/t/...
status: Draft
type: Standards Track
category: ERC
created: 2026-02-04
requires: 712
---

## Abstract
A standard interface for merchant-initiated pull payments where customers
authorize payments via EIP-712 signatures and merchants execute transactions,
enabling gasless customer experiences.

## Motivation
AI agents and automated systems need a way to make payments without holding
ETH for gas fees. Current solutions either require token-specific implementations
(EIP-3009) or complex wallet infrastructure (EIP-4337).

## Specification
[Interface definition]

## Rationale
[Design decisions]

## Backwards Compatibility
Compatible with all existing ERC-20 tokens via standard transferFrom.

## Security Considerations
[Replay protection, signature verification, etc.]

## Reference Implementation
[Link to FastPayCore.sol]
```

**2. Community Feedback**
- Post to ethereum-magicians.org
- Discuss in AllCoreDevs calls (if relevant)
- Get security audits
- Gather implementer feedback

**3. Adoption Path**
- Deploy reference implementation (✅ done - Base Sepolia)
- Get 2-3 projects to implement
- Wallet integration (MetaMask, Rainbow, etc.)
- Move from Draft → Review → Final

### Alternative: Keep as FastPay Protocol

You could also:
- ❌ Not submit as EIP
- ✅ Document as "FastPay Protocol Specification"
- ✅ Open source reference implementation (✅ done)
- ✅ Let ecosystem decide to adopt or not
- ✅ Faster iteration without EIP process

**Pros:** Flexibility, speed, control
**Cons:** Less legitimacy, harder adoption, reinvention by others

---

## Recommendation for Hackathon

**Short term (Hackathon submission):**
- Focus on "FastPay Protocol" narrative
- Mention EIP-712 compliance
- Compare to EIP-3009 in documentation
- Don't claim to be a new EIP (too early)

**Medium term (Post-hackathon):**
- Gather feedback from judges/community
- Get security audit
- Write formal specification
- Submit as ERC draft if there's interest

**Long term (If adoption grows):**
- Push ERC through to Final status
- Get wallet integrations
- Become standard for agent commerce

