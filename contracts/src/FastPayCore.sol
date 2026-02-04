// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title FastPayCore
 * @notice Merchant-initiated pull payments for agent commerce
 * @dev Customer signs authorization, merchant executes and pays gas
 *
 * Key Innovation: Inverts traditional crypto payment flow
 * - Traditional: Customer constructs tx → Customer broadcasts → Customer pays gas
 * - FastPay: Customer signs message → Merchant broadcasts → Merchant pays gas
 *
 * This enables gasless customer agents who only need USDC (no ETH for gas).
 */
contract FastPayCore is EIP712, ReentrancyGuard {
    using ECDSA for bytes32;

    // ============ Types ============

    /**
     * @dev Payment authorization signed by customer
     * @param merchant Address receiving funds
     * @param customer Address paying funds
     * @param token Payment token address (typically USDC)
     * @param amount Payment amount in token's smallest unit
     * @param validUntil Unix timestamp when authorization expires
     * @param nonce Unique identifier to prevent replay attacks
     */
    struct Payment {
        address merchant;
        address customer;
        address token;
        uint256 amount;
        uint256 validUntil;
        bytes32 nonce;
    }

    // EIP-712 type hash for Payment struct
    bytes32 private constant PAYMENT_TYPEHASH = keccak256(
        "Payment(address merchant,address customer,address token,uint256 amount,uint256 validUntil,bytes32 nonce)"
    );

    // ============ State ============

    /// @notice Tracks used nonces to prevent replay attacks
    mapping(bytes32 => bool) public usedNonces;

    /// @notice Counts payments per address (for stats/reputation)
    mapping(address => uint256) public paymentCount;

    // ============ Events ============

    /**
     * @notice Emitted when a payment is successfully executed
     * @param nonce Unique payment identifier
     * @param merchant Address that received funds
     * @param customer Address that paid funds
     * @param token Payment token address
     * @param amount Payment amount
     */
    event PaymentExecuted(
        bytes32 indexed nonce,
        address indexed merchant,
        address indexed customer,
        address token,
        uint256 amount
    );

    // ============ Constructor ============

    /**
     * @notice Initializes EIP-712 domain separator
     */
    constructor() EIP712("FastPay", "1") {}

    // ============ Core Functions ============

    /**
     * @notice Execute a pull payment (called by merchant)
     * @dev Verifies customer's EIP-712 signature and executes token transfer
     * @param payment Payment details struct
     * @param signature Customer's signature authorizing the payment
     * @return success True if payment executed successfully
     *
     * Requirements:
     * - msg.sender must be the merchant specified in payment
     * - Current time must be before validUntil
     * - Nonce must not have been used before
     * - Signature must be valid and from customer
     * - Customer must have approved this contract for token transfers
     * - Customer must have sufficient token balance
     */
    function executePullPayment(
        Payment calldata payment,
        bytes calldata signature
    ) external nonReentrant returns (bool success) {
        // Validate merchant
        require(msg.sender == payment.merchant, "Only merchant can execute");

        // Validate timing
        require(block.timestamp <= payment.validUntil, "Payment expired");

        // Validate nonce
        require(!usedNonces[payment.nonce], "Nonce already used");

        // Verify customer's signature
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

        // Mark nonce as used (prevents replay attacks)
        usedNonces[payment.nonce] = true;

        // Execute token transfer from customer to merchant
        IERC20 token = IERC20(payment.token);
        require(
            token.transferFrom(payment.customer, payment.merchant, payment.amount),
            "Transfer failed"
        );

        // Update statistics
        paymentCount[payment.merchant]++;
        paymentCount[payment.customer]++;

        // Emit event
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

    /**
     * @notice Get the EIP-712 hash for a payment (used for signing)
     * @param payment Payment details struct
     * @return Hash that customer should sign
     */
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

    /**
     * @notice Verify a payment signature
     * @param payment Payment details struct
     * @param signature Signature to verify
     * @return valid True if signature is valid
     * @return signer Address that signed the message
     */
    function verifySignature(
        Payment calldata payment,
        bytes calldata signature
    ) external view returns (bool valid, address signer) {
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

        signer = digest.recover(signature);
        valid = (signer == payment.customer);
    }
}
