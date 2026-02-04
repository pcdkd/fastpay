import { ethers } from 'ethers';

/**
 * FastPay Agent Wallet SDK
 *
 * Provides merchant and customer agent functionality for pull payments
 */

// EIP-712 Domain and Types for FastPay
// Note: chainId will be set dynamically based on network
const DOMAIN = {
  name: 'FastPay',
  version: '1',
  chainId: 84532, // Base Sepolia (default for testing)
  verifyingContract: '' // Will be set dynamically
};

const PAYMENT_TYPES = {
  Payment: [
    { name: 'merchant', type: 'address' },
    { name: 'customer', type: 'address' },
    { name: 'token', type: 'address' },
    { name: 'amount', type: 'uint256' },
    { name: 'validUntil', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' }
  ]
};

// FastPayCore ABI (minimal - only what we need)
const FASTPAY_ABI = [
  'function executePullPayment((address merchant, address customer, address token, uint256 amount, uint256 validUntil, bytes32 nonce) payment, bytes signature) external returns (bool)',
  'function getPaymentHash((address merchant, address customer, address token, uint256 amount, uint256 validUntil, bytes32 nonce) payment) external view returns (bytes32)',
  'function verifySignature((address merchant, address customer, address token, uint256 amount, uint256 validUntil, bytes32 nonce) payment, bytes signature) external view returns (bool valid, address signer)',
  'function usedNonces(bytes32) external view returns (bool)',
  'function paymentCount(address) external view returns (uint256)',
  'event PaymentExecuted(bytes32 indexed nonce, address indexed merchant, address indexed customer, address token, uint256 amount)'
];

// ERC20 ABI (minimal - only what we need)
const ERC20_ABI = [
  'function balanceOf(address) external view returns (uint256)',
  'function approve(address spender, uint256 amount) external returns (bool)',
  'function allowance(address owner, address spender) external view returns (uint256)',
  'function decimals() external view returns (uint8)',
  'function symbol() external view returns (string)'
];

/**
 * MerchantAgent - Handles merchant-side payment operations
 */
export class MerchantAgent {
  constructor(wallet, fastPayAddress, provider) {
    this.wallet = wallet;
    this.address = wallet.address;
    this.provider = provider;
    this.fastPayAddress = fastPayAddress;
    this.fastPay = new ethers.Contract(fastPayAddress, FASTPAY_ABI, wallet);
  }

  /**
   * Create a payment request
   * @param {string} customerAddress - Customer's wallet address
   * @param {string} tokenAddress - Payment token address (e.g., USDC)
   * @param {string} amountUSD - Amount in USD (e.g., "5.00")
   * @param {number} validForSeconds - How long the payment is valid (default: 180s)
   * @returns {Object} Payment request object
   */
  async createPayment(customerAddress, tokenAddress, amountUSD, validForSeconds = 180) {
    // Get token decimals
    const token = new ethers.Contract(tokenAddress, ERC20_ABI, this.provider);
    const decimals = await token.decimals();

    // Convert USD amount to token units
    const amount = ethers.parseUnits(amountUSD, decimals);

    // Generate unique nonce
    const nonce = ethers.randomBytes(32);

    // Calculate expiration
    const validUntil = Math.floor(Date.now() / 1000) + validForSeconds;

    const payment = {
      merchant: this.address,
      customer: customerAddress,
      token: tokenAddress,
      amount: amount,
      validUntil: validUntil,
      nonce: nonce
    };

    return {
      payment,
      amountUSD,
      expiresAt: new Date(validUntil * 1000)
    };
  }

  /**
   * Execute a pull payment (after customer has signed)
   * @param {Object} payment - Payment object
   * @param {string} signature - Customer's EIP-712 signature
   * @returns {Object} Transaction receipt
   */
  async executePullPayment(payment, signature) {
    // Verify signature before executing
    const [valid, signer] = await this.fastPay.verifySignature(payment, signature);

    if (!valid) {
      throw new Error(`Invalid signature: signed by ${signer}, expected ${payment.customer}`);
    }

    if (signer !== payment.customer) {
      throw new Error(`Signature mismatch: signed by ${signer}, expected ${payment.customer}`);
    }

    // Execute payment (merchant pays gas)
    const tx = await this.fastPay.executePullPayment(payment, signature);
    const receipt = await tx.wait();

    return {
      success: true,
      txHash: receipt.hash,
      blockNumber: receipt.blockNumber,
      gasUsed: receipt.gasUsed.toString()
    };
  }

  /**
   * Get merchant payment stats
   * @returns {Object} Payment statistics
   */
  async getStats() {
    const count = await this.fastPay.paymentCount(this.address);
    const balance = await this.provider.getBalance(this.address);

    return {
      totalPayments: count.toString(),
      ethBalance: ethers.formatEther(balance)
    };
  }
}

/**
 * CustomerAgent - Handles customer-side payment operations
 */
export class CustomerAgent {
  constructor(wallet, fastPayAddress, provider) {
    this.wallet = wallet;
    this.address = wallet.address;
    this.provider = provider;
    this.fastPayAddress = fastPayAddress;
    this.fastPay = new ethers.Contract(fastPayAddress, FASTPAY_ABI, provider);
  }

  /**
   * Evaluate payment request against spending policy
   * @param {Object} payment - Payment request to evaluate
   * @param {Object} policy - Spending policy rules
   * @returns {Object} Evaluation result
   */
  async evaluatePayment(payment, policy = {}) {
    const {
      maxAmountUSD = 100,
      maxPaymentsPerDay = 10,
      allowedMerchants = [],
      allowedTokens = []
    } = policy;

    const reasons = [];

    // Check if payment is expired
    const now = Math.floor(Date.now() / 1000);
    if (now > payment.validUntil) {
      reasons.push('Payment request expired');
      return { approved: false, reasons };
    }

    // Check if customer address matches
    if (payment.customer !== this.address) {
      reasons.push(`Payment not for this customer (expected ${this.address}, got ${payment.customer})`);
      return { approved: false, reasons };
    }

    // Get token info
    const token = new ethers.Contract(payment.token, ERC20_ABI, this.provider);
    const decimals = await token.decimals();
    const symbol = await token.symbol();
    const balance = await token.balanceOf(this.address);

    // Check balance
    if (balance < payment.amount) {
      const balanceFormatted = ethers.formatUnits(balance, decimals);
      const amountFormatted = ethers.formatUnits(payment.amount, decimals);
      reasons.push(`Insufficient balance: have ${balanceFormatted} ${symbol}, need ${amountFormatted} ${symbol}`);
      return { approved: false, reasons };
    }

    // Check allowance
    const allowance = await token.allowance(this.address, this.fastPayAddress);
    if (allowance < payment.amount) {
      reasons.push(`Insufficient allowance: need to approve FastPay contract for ${symbol}`);
      return { approved: false, reasons };
    }

    // Check amount limit (assuming USDC with 6 decimals)
    const amountUSD = parseFloat(ethers.formatUnits(payment.amount, decimals));
    if (amountUSD > maxAmountUSD) {
      reasons.push(`Amount ${amountUSD} USD exceeds limit of ${maxAmountUSD} USD`);
      return { approved: false, reasons };
    }

    // Check allowed merchants (if whitelist is set)
    if (allowedMerchants.length > 0 && !allowedMerchants.includes(payment.merchant)) {
      reasons.push(`Merchant ${payment.merchant} not in whitelist`);
      return { approved: false, reasons };
    }

    // Check allowed tokens (if whitelist is set)
    if (allowedTokens.length > 0 && !allowedTokens.includes(payment.token)) {
      reasons.push(`Token ${payment.token} not in whitelist`);
      return { approved: false, reasons };
    }

    // All checks passed
    return {
      approved: true,
      reasons: ['Payment approved by policy'],
      details: {
        amount: ethers.formatUnits(payment.amount, decimals),
        symbol,
        merchant: payment.merchant,
        expiresAt: new Date(payment.validUntil * 1000)
      }
    };
  }

  /**
   * Sign a payment authorization (EIP-712)
   * @param {Object} payment - Payment to sign
   * @returns {string} Signature
   */
  async signPayment(payment) {
    // Set verifying contract in domain
    const domain = { ...DOMAIN, verifyingContract: this.fastPayAddress };

    // Sign EIP-712 typed data
    const signature = await this.wallet.signTypedData(domain, PAYMENT_TYPES, payment);

    return signature;
  }

  /**
   * Handle payment request (evaluate + sign)
   * @param {Object} payment - Payment request
   * @param {Object} policy - Spending policy
   * @returns {Object} Result with signature if approved
   */
  async handlePaymentRequest(payment, policy = {}) {
    // Evaluate against policy
    const evaluation = await this.evaluatePayment(payment, policy);

    if (!evaluation.approved) {
      return {
        approved: false,
        reasons: evaluation.reasons,
        signature: null
      };
    }

    // Sign if approved
    const signature = await this.signPayment(payment);

    return {
      approved: true,
      reasons: evaluation.reasons,
      signature,
      details: evaluation.details
    };
  }

  /**
   * Approve token spending for FastPay contract
   * @param {string} tokenAddress - Token to approve
   * @param {string} amount - Amount to approve (defaults to max)
   * @returns {Object} Transaction receipt
   */
  async approveToken(tokenAddress, amount = ethers.MaxUint256) {
    const token = new ethers.Contract(tokenAddress, ERC20_ABI, this.wallet);
    const tx = await token.approve(this.fastPayAddress, amount);
    const receipt = await tx.wait();

    return {
      success: true,
      txHash: receipt.hash,
      approved: true
    };
  }

  /**
   * Get customer payment stats and balances
   * @param {string} tokenAddress - Token to check balance
   * @returns {Object} Stats
   */
  async getStats(tokenAddress) {
    const count = await this.fastPay.paymentCount(this.address);
    const token = new ethers.Contract(tokenAddress, ERC20_ABI, this.provider);
    const balance = await token.balanceOf(this.address);
    const decimals = await token.decimals();
    const symbol = await token.symbol();
    const allowance = await token.allowance(this.address, this.fastPayAddress);

    return {
      totalPayments: count.toString(),
      tokenBalance: ethers.formatUnits(balance, decimals),
      tokenSymbol: symbol,
      allowance: ethers.formatUnits(allowance, decimals),
      needsApproval: allowance === 0n
    };
  }
}

/**
 * Utility function to format payment details for display
 */
export function formatPayment(payment, decimals = 6) {
  return {
    merchant: payment.merchant,
    customer: payment.customer,
    token: payment.token,
    amount: ethers.formatUnits(payment.amount, decimals),
    validUntil: new Date(payment.validUntil * 1000).toISOString(),
    nonce: ethers.hexlify(payment.nonce)
  };
}

/**
 * Utility function to parse payment from transaction logs
 */
export function parsePaymentEvent(receipt) {
  const iface = new ethers.Interface(FASTPAY_ABI);

  for (const log of receipt.logs) {
    try {
      const parsed = iface.parseLog(log);
      if (parsed.name === 'PaymentExecuted') {
        return {
          nonce: parsed.args.nonce,
          merchant: parsed.args.merchant,
          customer: parsed.args.customer,
          token: parsed.args.token,
          amount: parsed.args.amount
        };
      }
    } catch (e) {
      // Not a PaymentExecuted event, continue
    }
  }

  return null;
}
