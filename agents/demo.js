#!/usr/bin/env node
import { ethers } from 'ethers';
import { MerchantAgent, CustomerAgent, formatPayment } from './AgentWallet.js';
import dotenv from 'dotenv';

dotenv.config();

// Configuration
const CONFIG = {
  // Base Sepolia Testnet (for development)
  rpcUrl: process.env.BASE_RPC_URL || 'https://sepolia.base.org',
  chainId: parseInt(process.env.CHAIN_ID) || 84532,

  // Contract addresses (will be set after deployment)
  fastPayAddress: process.env.FASTPAY_ADDRESS || '0x0000000000000000000000000000000000000000',
  usdcAddress: process.env.USDC_ADDRESS || '0x036CbD53842c5426634e7929541eC2318f3dCF7e',

  // Wallet private keys
  merchantKey: process.env.MERCHANT_PRIVATE_KEY,
  customerKey: process.env.CUSTOMER_PRIVATE_KEY,

  // Demo settings
  paymentAmount: process.env.PAYMENT_AMOUNT || '0.50' // $0.50 USD
};

// Validate configuration
function validateConfig() {
  if (!CONFIG.merchantKey) {
    throw new Error('MERCHANT_PRIVATE_KEY not set in .env');
  }
  if (!CONFIG.customerKey) {
    throw new Error('CUSTOMER_PRIVATE_KEY not set in .env');
  }
  if (CONFIG.fastPayAddress === '0x0000000000000000000000000000000000000000') {
    console.warn('⚠️  FASTPAY_ADDRESS not set - using placeholder. Deploy contract first!');
  }
}

// Pretty print utilities
function printHeader(title) {
  console.log('\n' + '='.repeat(80));
  console.log(`  ${title}`);
  console.log('='.repeat(80) + '\n');
}

function printSection(title) {
  console.log('\n' + '-'.repeat(80));
  console.log(`  ${title}`);
  console.log('-'.repeat(80) + '\n');
}

function printKeyValue(key, value, indent = 2) {
  const spacing = ' '.repeat(indent);
  console.log(`${spacing}${key}: ${value}`);
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Main demo flow
async function runDemo() {
  try {
    validateConfig();

    printHeader('🤖 FastPay Agent-to-Agent Payment Demo');
    console.log('This demo shows how AI agents can transact using pull payments.\n');
    console.log('Key Innovation: Customer agent signs (gasless), merchant agent executes (pays gas).\n');

    // Step 1: Initialize
    printSection('Step 1: Initialize Agents');

    const provider = new ethers.JsonRpcProvider(CONFIG.rpcUrl);
    const merchantWallet = new ethers.Wallet(CONFIG.merchantKey, provider);
    const customerWallet = new ethers.Wallet(CONFIG.customerKey, provider);

    const merchantAgent = new MerchantAgent(merchantWallet, CONFIG.fastPayAddress, provider);
    const customerAgent = new CustomerAgent(customerWallet, CONFIG.fastPayAddress, provider);

    printKeyValue('Merchant Agent', merchantAgent.address);
    printKeyValue('Customer Agent', customerAgent.address);
    printKeyValue('FastPay Contract', CONFIG.fastPayAddress);
    printKeyValue('USDC Token', CONFIG.usdcAddress);
    printKeyValue('Network', CONFIG.chainId === 84532 ? `Base Sepolia Testnet (Chain ID: ${CONFIG.chainId})` : `Base Mainnet (Chain ID: ${CONFIG.chainId})`);

    // Step 2: Check initial balances
    printSection('Step 2: Initial Balances');

    const merchantStats = await merchantAgent.getStats();
    const customerStats = await customerAgent.getStats(CONFIG.usdcAddress);

    console.log('Merchant:');
    printKeyValue('ETH Balance', `${merchantStats.ethBalance} ETH (for gas)`);
    printKeyValue('Total Payments', merchantStats.totalPayments);

    console.log('\nCustomer:');
    printKeyValue('USDC Balance', `${customerStats.tokenBalance} ${customerStats.tokenSymbol}`);
    printKeyValue('FastPay Allowance', `${customerStats.allowance} ${customerStats.tokenSymbol}`);
    printKeyValue('Total Payments', customerStats.totalPayments);

    // Step 2.5: Approve if needed
    if (customerStats.needsApproval) {
      printSection('Step 2.5: Approve USDC Spending');
      console.log('Customer agent needs to approve FastPay contract to spend USDC...\n');

      const approval = await customerAgent.approveToken(CONFIG.usdcAddress);
      console.log(`✅ Approval transaction: ${approval.txHash}`);
      console.log(`   View on Basescan: https://basescan.org/tx/${approval.txHash}\n`);

      await sleep(2000); // Wait for confirmation
    }

    // Step 3: Merchant creates payment request
    printSection('Step 3: Merchant Creates Payment Request');

    console.log(`Merchant agent creates a payment request for $${CONFIG.paymentAmount}...\n`);

    const paymentRequest = await merchantAgent.createPayment(
      customerAgent.address,
      CONFIG.usdcAddress,
      CONFIG.paymentAmount,
      180 // Valid for 3 minutes
    );

    const formatted = formatPayment(paymentRequest.payment);
    console.log('Payment Request:');
    printKeyValue('Amount', `${paymentRequest.amountUSD} USD`);
    printKeyValue('Merchant', formatted.merchant);
    printKeyValue('Customer', formatted.customer);
    printKeyValue('Token', formatted.token);
    printKeyValue('Expires At', paymentRequest.expiresAt.toISOString());
    printKeyValue('Nonce', formatted.nonce);

    // Step 4: Customer evaluates and signs
    printSection('Step 4: Customer Evaluates & Signs (GASLESS)');

    console.log('Customer agent evaluating payment against spending policy...\n');

    // Customer policy: max $100 per payment
    const policy = {
      maxAmountUSD: 100,
      maxPaymentsPerDay: 10,
      allowedMerchants: [], // Empty = allow all
      allowedTokens: [] // Empty = allow all
    };

    const result = await customerAgent.handlePaymentRequest(paymentRequest.payment, policy);

    if (!result.approved) {
      console.error('❌ Payment rejected by customer policy:');
      result.reasons.forEach(reason => console.log(`   - ${reason}`));
      process.exit(1);
    }

    console.log('✅ Payment approved by customer policy\n');
    console.log('Customer agent signing payment authorization...');
    console.log('   (This is GASLESS - customer needs NO ETH!)\n');
    printKeyValue('Signature', result.signature.slice(0, 20) + '...' + result.signature.slice(-10));
    console.log('\n💡 Key Innovation: Customer only signed a message (no gas, no transaction)');

    await sleep(1000);

    // Step 5: Merchant executes payment
    printSection('Step 5: Merchant Executes Payment (PAYS GAS)');

    console.log('Merchant agent executing pull payment on-chain...');
    console.log('   (Merchant broadcasts transaction and pays gas fees)\n');

    const execution = await merchantAgent.executePullPayment(
      paymentRequest.payment,
      result.signature
    );

    console.log('✅ Payment executed successfully!\n');
    printKeyValue('Transaction Hash', execution.txHash);
    printKeyValue('Block Number', execution.blockNumber);
    printKeyValue('Gas Used', execution.gasUsed);
    console.log(`\n🔗 View on Basescan: https://basescan.org/tx/${execution.txHash}`);

    await sleep(2000);

    // Step 6: Show final balances
    printSection('Step 6: Final Balances');

    const merchantStatsFinal = await merchantAgent.getStats();
    const customerStatsFinal = await customerAgent.getStats(CONFIG.usdcAddress);

    console.log('Merchant:');
    printKeyValue('ETH Balance', `${merchantStatsFinal.ethBalance} ETH`);
    printKeyValue('Total Payments', merchantStatsFinal.totalPayments);
    printKeyValue('Change', `+${CONFIG.paymentAmount} USDC`);

    console.log('\nCustomer:');
    printKeyValue('USDC Balance', `${customerStatsFinal.tokenBalance} ${customerStatsFinal.tokenSymbol}`);
    printKeyValue('Total Payments', customerStatsFinal.totalPayments);
    printKeyValue('Change', `-${CONFIG.paymentAmount} USDC`);

    // Summary
    printHeader('✅ Demo Complete - Pull Payment Success!');

    console.log('Summary:\n');
    console.log('  1. Customer agent signed authorization (GASLESS)');
    console.log('  2. Merchant agent executed payment (PAID GAS)');
    console.log(`  3. ${CONFIG.paymentAmount} USDC transferred from customer to merchant`);
    console.log('  4. Total time: < 10 seconds\n');

    console.log('Why This Matters for AI Agents:\n');
    console.log('  ✅ Customer agents need ONLY USDC (no ETH for gas)');
    console.log('  ✅ Simple signing interface (no transaction construction)');
    console.log('  ✅ No gas price monitoring or estimation');
    console.log('  ✅ Merchant absorbs gas cost (can factor into pricing)');
    console.log('  ✅ Familiar pull payment model (like credit cards)\n');

    console.log('🎉 FastPay enables true autonomous agent commerce!\n');

  } catch (error) {
    console.error('\n❌ Demo failed:', error.message);

    if (error.message.includes('insufficient funds')) {
      console.error('\n💡 Tip: Ensure wallets have sufficient ETH (merchant) and USDC (customer)');
    }

    if (error.message.includes('nonce')) {
      console.error('\n💡 Tip: Check that the payment hasn\'t already been executed');
    }

    process.exit(1);
  }
}

// Run the demo
console.log('Starting FastPay Agent Demo...\n');
runDemo().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
