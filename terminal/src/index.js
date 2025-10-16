#!/usr/bin/env node
import 'dotenv/config';
import readline from 'readline';
import config from '../config/index.js';
import { NFCBridge } from './nfc.js';
import { CommerceClient } from './commerce.js';
import { PaymentManager } from './payment.js';
import { createWebhookServer } from './webhook.js';

console.log(`
┌───────────────────────────────────────────────────────────────┐
│                                                                 │
│                    💳 FastPay Terminal                          │
│                  Tap-to-Pay Crypto Payments                     │
│                                                                 │
└───────────────────────────────────────────────────────────────┘
`);

// Initialize services
console.log('🚀 Initializing services...\n');

const commerceClient = new CommerceClient(config.coinbaseApiKey);
const paymentManager = new PaymentManager(commerceClient, config.terminalId);
const nfcBridge = new NFCBridge(config);

// Start webhook server
const webhookApp = createWebhookServer(config, paymentManager);
const server = webhookApp.listen(config.port, () => {
  console.log(`✅ Webhook server listening on port ${config.port}`);
  console.log(`   Endpoint: http://localhost:${config.port}/webhooks/coinbase`);
  console.log(`   Health check: http://localhost:${config.port}/health\n`);
});

// Terminal UI state
let currentState = 'IDLE';  // IDLE, WAITING_FOR_PAYMENT, COMPLETED
let currentCharge = null;
let isPrompting = false;  // Re-entry guard for promptForAmount

// NFC event handlers
nfcBridge.on('ready', (event) => {
  console.log(`✅ NFC reader ready (firmware ${event.firmware})`);
  console.log(`   Port: ${event.port}\n`);
  console.log('─'.repeat(70));
  console.log('💳 FastPay Terminal Ready');
  console.log('─'.repeat(70));
  promptForAmount();
});

nfcBridge.on('tap', async (event) => {
  console.log(`\n📱 Phone tapped! UID: ${event.uid}`);

  if (currentState === 'WAITING_FOR_PAYMENT') {
    const charge = await paymentManager.associateTap(event.uid);
    if (charge) {
      console.log('✅ Tap associated with charge');
      console.log('💡 Customer can now complete payment on their phone');
      console.log(`   (Charge ID: ${charge.id})`);
    }
  } else {
    console.log('⚠️  No pending payment request');
    console.log('   Please create a charge first by entering an amount\n');
  }
});

nfcBridge.on('error', async (event) => {
  console.error(`\n❌ NFC Error: ${event.message}`);
  if (event.fatal) {
    console.error('   Fatal error - exiting...');
    await cleanup();
    process.exit(1);
  }
});

nfcBridge.on('shutdown', (event) => {
  console.log(`\n🛑 NFC shutdown: ${event.reason}`);
});

// Webhook event handlers
webhookApp.on('payment:confirmed', (event) => {
  console.log('\n');
  console.log('═'.repeat(70));
  console.log('🎉 PAYMENT CONFIRMED!');
  console.log('═'.repeat(70));
  console.log(`   Amount: $${event.amount} ${event.currency}`);
  console.log(`   Charge ID: ${event.chargeId}`);
  console.log(`   Confirmed: ${event.confirmedAt}`);
  console.log('═'.repeat(70));

  currentState = 'COMPLETED';
  currentCharge = null;

  // Return to idle after 3 seconds
  setTimeout(() => {
    currentState = 'IDLE';
    console.log('\n');
    promptForAmount();
  }, 3000);
});

// Terminal UI
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

/**
 * Prompt merchant for sale amount
 */
function promptForAmount() {
  if (currentState !== 'IDLE' || isPrompting) {
    return;
  }

  isPrompting = true;  // Set guard before async callback

  rl.question('\n💵 Enter sale amount (USD) or "q" to quit: $', async (input) => {
    // Handle quit
    if (input.toLowerCase() === 'q' || input.toLowerCase() === 'quit') {
      console.log('\n👋 Shutting down...');
      await cleanup();
      process.exit(0);
      return;
    }

    // Parse amount
    const amount = parseFloat(input);

    if (isNaN(amount) || amount <= 0) {
      console.log('❌ Invalid amount. Please enter a positive number.');
      isPrompting = false;  // Clear guard before re-prompting
      promptForAmount();
      return;
    }

    try {
      currentState = 'WAITING_FOR_PAYMENT';

      // Create charge
      console.log(`\n⏳ Creating charge for $${amount.toFixed(2)}...`);

      const charge = await paymentManager.createPaymentRequest(
        amount,
        `${config.merchantName} - Terminal ${config.terminalId}`
      );

      currentCharge = charge;

      console.log(`\n✅ Charge created successfully`);
      console.log(`   Charge ID: ${charge.id}`);
      console.log(`   Amount: $${amount.toFixed(2)}`);

      // Generate and display QR code
      console.log('\n📱 Customer: Scan QR code OR tap your phone');
      console.log('─'.repeat(70));

      const qr = await paymentManager.generateQR(charge.hostedUrl);
      if (qr) {
        console.log(qr);
      } else {
        console.log('   (QR code generation failed)');
      }

      console.log('─'.repeat(70));
      console.log(`🔗 Payment URL: ${charge.hostedUrl}`);
      console.log('─'.repeat(70));
      console.log('\n⏳ Waiting for payment...');
      console.log('   (Charge expires in 3 minutes)\n');

    } catch (error) {
      console.error(`\n❌ Failed to create charge: ${error.message}`);
      currentState = 'IDLE';
      currentCharge = null;
      isPrompting = false;  // Clear guard before re-prompting
      promptForAmount();
    }
  });
}

/**
 * Graceful shutdown
 */
async function cleanup() {
  console.log('\n🧹 Cleaning up...');

  // Stop NFC reader
  if (nfcBridge) {
    nfcBridge.stop();
  }

  // Close webhook server (await to ensure it finishes before process exits)
  if (server) {
    await new Promise((resolve) => {
      server.close(() => {
        console.log('✅ Webhook server closed');
        resolve();
      });
    });
  }

  // Close readline interface
  if (rl) {
    rl.close();
  }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n\n👋 Received SIGINT (Ctrl+C)');
  await cleanup();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n\n👋 Received SIGTERM');
  await cleanup();
  process.exit(0);
});

// Handle uncaught errors
process.on('uncaughtException', async (error) => {
  console.error('\n❌ Uncaught Exception:', error);
  await cleanup();
  process.exit(1);
});

process.on('unhandledRejection', async (reason, promise) => {
  console.error('\n❌ Unhandled Rejection:', reason);
  await cleanup();
  process.exit(1);
});

// Start NFC bridge
console.log('🔌 Starting NFC reader...\n');
nfcBridge.start();
