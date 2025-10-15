import dotenv from 'dotenv';
import { existsSync } from 'fs';
import { platform } from 'os';

// Load environment variables
dotenv.config();

/**
 * Detect platform and default serial port
 */
function detectPlatform() {
  const os = platform();

  if (os === 'darwin') {
    // macOS - USB-to-UART converter
    return {
      platform: 'macOS',
      defaultPort: '/dev/tty.usbserial-ABSCDY4Z',
      needsDtrRtsFix: true,
    };
  } else if (existsSync('/dev/ttyAMA0')) {
    // Raspberry Pi - GPIO UART
    return {
      platform: 'Raspberry Pi',
      defaultPort: '/dev/ttyAMA0',
      needsDtrRtsFix: false,
    };
  } else if (existsSync('/dev/ttyUSB0')) {
    // Linux - USB-to-UART converter
    return {
      platform: 'Linux',
      defaultPort: '/dev/ttyUSB0',
      needsDtrRtsFix: true,
    };
  } else {
    return {
      platform: 'Unknown',
      defaultPort: null,
      needsDtrRtsFix: true,
    };
  }
}

/**
 * Validate required environment variables
 */
function validateEnv() {
  const required = [
    'COINBASE_COMMERCE_API_KEY',
    'COINBASE_WEBHOOK_SECRET',
    'MERCHANT_NAME',
    'TERMINAL_ID',
  ];

  const missing = [];

  for (const varName of required) {
    if (!process.env[varName]) {
      missing.push(varName);
    }
  }

  if (missing.length > 0) {
    console.error('❌ Missing required environment variables:');
    for (const varName of missing) {
      console.error(`   - ${varName}`);
    }
    console.error('\nPlease check your .env file. See .env.example for reference.');
    process.exit(1);
  }
}

// Detect platform
const platformInfo = detectPlatform();

// Validate environment
validateEnv();

// Export configuration
const config = {
  // Platform
  platform: platformInfo.platform,

  // NFC Hardware
  nfcPort: process.env.NFC_PORT || platformInfo.defaultPort,
  nfcBaudRate: parseInt(process.env.NFC_BAUD_RATE || '115200', 10),
  tapDebounceMs: parseInt(process.env.NFC_TAP_DEBOUNCE_MS || '1000', 10),
  needsDtrRtsFix: platformInfo.needsDtrRtsFix,

  // Coinbase Commerce
  coinbaseApiKey: process.env.COINBASE_COMMERCE_API_KEY,
  webhookSecret: process.env.COINBASE_WEBHOOK_SECRET,

  // Merchant
  merchantName: process.env.MERCHANT_NAME,
  terminalId: process.env.TERMINAL_ID,

  // Server
  port: parseInt(process.env.PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',

  // Optional: Blockchain (Phase 2)
  baseRpcUrl: process.env.BASE_RPC_URL,
  chainId: process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID, 10) : 8453,
  usdcAddress: process.env.USDC_ADDRESS || '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
};

// Warn if NFC port is not configured
if (!config.nfcPort) {
  console.warn('⚠️  NFC_PORT not configured in .env');
  console.warn('   Please set NFC_PORT to your serial device path');
  console.warn('   Example: NFC_PORT=/dev/tty.usbserial-ABSCDY4Z');
  process.exit(1);
}

// Log configuration (hide sensitive values)
if (config.nodeEnv === 'development') {
  console.log('\n📋 Configuration:');
  console.log(`   Platform: ${config.platform}`);
  console.log(`   NFC Port: ${config.nfcPort}`);
  console.log(`   Merchant: ${config.merchantName}`);
  console.log(`   Terminal ID: ${config.terminalId}`);
  console.log(`   Webhook Port: ${config.port}`);
  console.log(`   Coinbase API Key: ${config.coinbaseApiKey.substring(0, 8)}...`);
  console.log('');
}

export default config;
