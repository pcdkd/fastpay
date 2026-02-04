// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/FastPayCore.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockUSDC
 * @dev Mock USDC token for testing
 */
contract MockUSDC is ERC20 {
    constructor() ERC20("USD Coin", "USDC") {
        _mint(msg.sender, 1000000 * 10**decimals());
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/**
 * @title FastPayCoreTest
 * @dev Comprehensive test suite for FastPayCore pull payment contract
 */
contract FastPayCoreTest is Test {
    FastPayCore public fastPay;
    MockUSDC public usdc;

    address public merchant;
    uint256 public merchantKey;

    address public customer;
    uint256 public customerKey;

    // Test constants
    uint256 constant PAYMENT_AMOUNT = 5 * 10**6; // $5 USDC (6 decimals)
    uint256 constant VALID_DURATION = 3 minutes;

    event PaymentExecuted(
        bytes32 indexed nonce,
        address indexed merchant,
        address indexed customer,
        address token,
        uint256 amount
    );

    function setUp() public {
        // Deploy contracts
        fastPay = new FastPayCore();
        usdc = new MockUSDC();

        // Create test accounts with private keys for signing
        merchantKey = 0xA11CE;
        merchant = vm.addr(merchantKey);

        customerKey = 0xB0B;
        customer = vm.addr(customerKey);

        // Fund customer with USDC
        usdc.mint(customer, 100 * 10**6); // $100 USDC

        // Customer approves FastPay contract to spend USDC
        vm.prank(customer);
        usdc.approve(address(fastPay), type(uint256).max);
    }

    /**
     * @dev Helper function to create a payment struct
     */
    function createPayment(bytes32 nonce) internal view returns (FastPayCore.Payment memory) {
        return FastPayCore.Payment({
            merchant: merchant,
            customer: customer,
            token: address(usdc),
            amount: PAYMENT_AMOUNT,
            validUntil: block.timestamp + VALID_DURATION,
            nonce: nonce
        });
    }

    /**
     * @dev Helper function to sign a payment (EIP-712)
     */
    function signPayment(FastPayCore.Payment memory payment, uint256 privateKey)
        internal
        view
        returns (bytes memory)
    {
        bytes32 digest = fastPay.getPaymentHash(payment);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(privateKey, digest);
        return abi.encodePacked(r, s, v);
    }

    /**
     * @dev Test 1: Happy path - successful payment execution
     */
    function testExecutePullPayment() public {
        bytes32 nonce = keccak256("payment-1");
        FastPayCore.Payment memory payment = createPayment(nonce);
        bytes memory signature = signPayment(payment, customerKey);

        uint256 merchantBalanceBefore = usdc.balanceOf(merchant);
        uint256 customerBalanceBefore = usdc.balanceOf(customer);

        // Expect PaymentExecuted event
        vm.expectEmit(true, true, true, true);
        emit PaymentExecuted(
            nonce,
            merchant,
            customer,
            address(usdc),
            PAYMENT_AMOUNT
        );

        // Merchant executes the payment
        vm.prank(merchant);
        bool success = fastPay.executePullPayment(payment, signature);

        // Assertions
        assertTrue(success, "Payment should succeed");
        assertTrue(fastPay.usedNonces(nonce), "Nonce should be marked as used");
        assertEq(
            usdc.balanceOf(merchant),
            merchantBalanceBefore + PAYMENT_AMOUNT,
            "Merchant should receive payment"
        );
        assertEq(
            usdc.balanceOf(customer),
            customerBalanceBefore - PAYMENT_AMOUNT,
            "Customer balance should decrease"
        );
        assertEq(fastPay.paymentCount(merchant), 1, "Merchant payment count should be 1");
        assertEq(fastPay.paymentCount(customer), 1, "Customer payment count should be 1");
    }

    /**
     * @dev Test 2: Reject expired payment
     */
    function testRejectExpiredPayment() public {
        bytes32 nonce = keccak256("payment-expired");
        FastPayCore.Payment memory payment = createPayment(nonce);
        bytes memory signature = signPayment(payment, customerKey);

        // Warp time forward past expiration
        vm.warp(block.timestamp + VALID_DURATION + 1);

        // Attempt to execute expired payment
        vm.prank(merchant);
        vm.expectRevert("Payment expired");
        fastPay.executePullPayment(payment, signature);
    }

    /**
     * @dev Test 3: Reject reused nonce (replay protection)
     */
    function testRejectReusedNonce() public {
        bytes32 nonce = keccak256("payment-replay");
        FastPayCore.Payment memory payment = createPayment(nonce);
        bytes memory signature = signPayment(payment, customerKey);

        // First payment succeeds
        vm.prank(merchant);
        bool success = fastPay.executePullPayment(payment, signature);
        assertTrue(success, "First payment should succeed");

        // Fund customer again for second attempt
        usdc.mint(customer, PAYMENT_AMOUNT);

        // Second payment with same nonce should fail
        vm.prank(merchant);
        vm.expectRevert("Nonce already used");
        fastPay.executePullPayment(payment, signature);
    }

    /**
     * @dev Test 4: Reject invalid signature
     */
    function testRejectInvalidSignature() public {
        bytes32 nonce = keccak256("payment-invalid-sig");
        FastPayCore.Payment memory payment = createPayment(nonce);

        // Sign with wrong private key (merchant instead of customer)
        bytes memory invalidSignature = signPayment(payment, merchantKey);

        // Attempt to execute with invalid signature
        vm.prank(merchant);
        vm.expectRevert("Invalid signature");
        fastPay.executePullPayment(payment, invalidSignature);
    }

    /**
     * @dev Test 5: Reject unauthorized merchant
     */
    function testRejectUnauthorizedMerchant() public {
        bytes32 nonce = keccak256("payment-unauthorized");
        FastPayCore.Payment memory payment = createPayment(nonce);
        bytes memory signature = signPayment(payment, customerKey);

        // Create attacker account
        address attacker = address(0xBAD);

        // Attacker tries to execute payment (not the merchant)
        vm.prank(attacker);
        vm.expectRevert("Only merchant can execute");
        fastPay.executePullPayment(payment, signature);
    }

    /**
     * @dev Test 6: Verify signature view function
     */
    function testVerifySignature() public view {
        bytes32 nonce = keccak256("payment-verify");
        FastPayCore.Payment memory payment = createPayment(nonce);
        bytes memory signature = signPayment(payment, customerKey);

        (bool valid, address signer) = fastPay.verifySignature(payment, signature);

        assertTrue(valid, "Signature should be valid");
        assertEq(signer, customer, "Signer should be customer");
    }

    /**
     * @dev Test 7: Verify signature with invalid signature
     */
    function testVerifyInvalidSignature() public view {
        bytes32 nonce = keccak256("payment-verify-invalid");
        FastPayCore.Payment memory payment = createPayment(nonce);
        bytes memory invalidSignature = signPayment(payment, merchantKey);

        (bool valid, address signer) = fastPay.verifySignature(payment, invalidSignature);

        assertFalse(valid, "Signature should be invalid");
        assertEq(signer, merchant, "Signer should be merchant, not customer");
    }

    /**
     * @dev Test 8: Test payment hash consistency
     */
    function testGetPaymentHash() public view {
        bytes32 nonce = keccak256("payment-hash");
        FastPayCore.Payment memory payment = createPayment(nonce);

        bytes32 hash1 = fastPay.getPaymentHash(payment);
        bytes32 hash2 = fastPay.getPaymentHash(payment);

        assertEq(hash1, hash2, "Payment hash should be deterministic");
        assertTrue(hash1 != bytes32(0), "Payment hash should not be zero");
    }

    /**
     * @dev Test 9: Insufficient balance handling
     */
    function testInsufficientBalance() public {
        bytes32 nonce = keccak256("payment-insufficient");

        // Create payment for more than customer has
        FastPayCore.Payment memory payment = FastPayCore.Payment({
            merchant: merchant,
            customer: customer,
            token: address(usdc),
            amount: 200 * 10**6, // $200 USDC (customer only has $100)
            validUntil: block.timestamp + VALID_DURATION,
            nonce: nonce
        });

        bytes memory signature = signPayment(payment, customerKey);

        // Attempt to execute payment with insufficient balance
        // OpenZeppelin v5 throws ERC20InsufficientBalance custom error
        vm.prank(merchant);
        vm.expectRevert(); // Expect any revert (ERC20InsufficientBalance)
        fastPay.executePullPayment(payment, signature);
    }

    /**
     * @dev Test 10: Multiple sequential payments
     */
    function testMultiplePayments() public {
        // First payment
        bytes32 nonce1 = keccak256("payment-multi-1");
        FastPayCore.Payment memory payment1 = createPayment(nonce1);
        bytes memory signature1 = signPayment(payment1, customerKey);

        vm.prank(merchant);
        bool success1 = fastPay.executePullPayment(payment1, signature1);
        assertTrue(success1, "First payment should succeed");

        // Second payment with different nonce
        bytes32 nonce2 = keccak256("payment-multi-2");
        FastPayCore.Payment memory payment2 = createPayment(nonce2);
        bytes memory signature2 = signPayment(payment2, customerKey);

        vm.prank(merchant);
        bool success2 = fastPay.executePullPayment(payment2, signature2);
        assertTrue(success2, "Second payment should succeed");

        // Verify counts
        assertEq(fastPay.paymentCount(merchant), 2, "Merchant should have 2 payments");
        assertEq(fastPay.paymentCount(customer), 2, "Customer should have 2 payments");
        assertEq(
            usdc.balanceOf(merchant),
            PAYMENT_AMOUNT * 2,
            "Merchant should have received 2 payments"
        );
    }

    /**
     * @dev Test 11: Payment with no approval should fail
     */
    function testNoApproval() public {
        // Create new customer without approval
        uint256 newCustomerKey = 0xC0C;
        address newCustomer = vm.addr(newCustomerKey);

        usdc.mint(newCustomer, 100 * 10**6); // Fund but don't approve

        bytes32 nonce = keccak256("payment-no-approval");
        FastPayCore.Payment memory payment = FastPayCore.Payment({
            merchant: merchant,
            customer: newCustomer,
            token: address(usdc),
            amount: PAYMENT_AMOUNT,
            validUntil: block.timestamp + VALID_DURATION,
            nonce: nonce
        });

        bytes memory signature = signPayment(payment, newCustomerKey);

        // Attempt to execute without approval
        // OpenZeppelin v5 throws ERC20InsufficientAllowance custom error
        vm.prank(merchant);
        vm.expectRevert(); // Expect any revert (ERC20InsufficientAllowance)
        fastPay.executePullPayment(payment, signature);
    }
}
