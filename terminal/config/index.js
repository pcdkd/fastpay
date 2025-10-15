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
    // macOS - USB-to-UART converter (no default, must be explicitly set)
    return {
      platform: 'macOS',
      defaultPort: null,
      needsDtrRtsFix: true,
    };
  }

  if (os === 'linux') {
    if (existsSync('/dev/ttyAMA0')) {
      // Raspberry Pi - GPIO UART
      return {
        platform: 'Raspberry Pi',
        defaultPort: '/dev/ttyAMA0',
        needsDtrRtsFix: false,
      };
    }
    if (existsSync('/dev/ttyUSB0')) {
      // Linux - USB-to-UART converter
      return {
        platform: 'Linux',
        defaultPort: '/dev/ttyUSB0',
        needsDtrRtsFix: true,
      };
    }
  }

  // Fallback for unknown platforms or Linux without a detected port
  return {
    platform: 'Unknown',
    defaultPort: null,
    needsDtrRtsFix: true,
  };
}

/**
 * Validate integer is within acceptable range
 */
function validateInteger(value, name, min, max) {
  if (isNaN(value) || value < min || value > max) {
    throw new Error(
      `Invalid ${name}: ${value}. Must be between ${min} and ${max}.`
    );
  }
  return value;
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

  const missing = required.filter((varName) => !process.env[varName]);

  if (missing.length > 0) {
    const errorLines = [
      '❌ Missing required environment variables:',
      ...missing.map((varName) => `   - ${varName}`),
      '\nPlease check your .env file. See .env.example for reference.',
    ];
    throw new Error(errorLines.join('\n'));
  }
}

/**
 * Validate NFC port is configured
 */
function validateNfcPort(port, platformName) {
  if (!port) {
    const errorLines = [
      '⚠️  NFC_PORT not configured in .env',
      '   Please set NFC_PORT to your serial device path',
      '',
      '   Examples:',
      '   - macOS: NFC_PORT=/dev/tty.usbserial-ABSCDY4Z',
      '   - Raspberry Pi: NFC_PORT=/dev/ttyAMA0',
      '   - Linux: NFC_PORT=/dev/ttyUSB0',
      '',
      `   Detected platform: ${platformName}`,
    ];
    throw new Error(errorLines.join('\n'));
  }
}

// Detect platform
const platformInfo = detectPlatform();

// Validate environment
validateEnv();

// Parse and validate configuration values
const nfcPort = process.env.NFC_PORT || platformInfo.defaultPort;
const nfcBaudRate = validateInteger(
  parseInt(process.env.NFC_BAUD_RATE || '115200', 10),
  'NFC_BAUD_RATE',
  9600,
  921600
);
const tapDebounceMs = validateInteger(
  parseInt(process.env.NFC_TAP_DEBOUNCE_MS || '1000', 10),
  'NFC_TAP_DEBOUNCE_MS',
  100,
  10000
);
const port = validateInteger(
  parseInt(process.env.PORT || '3000', 10),
  'PORT',
  1,
  65535
);

// Validate NFC port is configured
validateNfcPort(nfcPort, platformInfo.platform);

// Export configuration
const config = {
  // Platform
  platform: platformInfo.platform,

  // NFC Hardware
  nfcPort,
  nfcBaudRate,
  tapDebounceMs,
  needsDtrRtsFix: platformInfo.needsDtrRtsFix,

  // Coinbase Commerce
  coinbaseApiKey: process.env.COINBASE_COMMERCE_API_KEY,
  webhookSecret: process.env.COINBASE_WEBHOOK_SECRET,

  // Merchant
  merchantName: process.env.MERCHANT_NAME,
  terminalId: process.env.TERMINAL_ID,

  // Server
  port,
  nodeEnv: process.env.NODE_ENV || 'development',

  // Optional: Blockchain (Phase 2)
  baseRpcUrl: process.env.BASE_RPC_URL,
  chainId: process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID, 10) : 8453,
  usdcAddress: process.env.USDC_ADDRESS || '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
};

// Log configuration (hide sensitive values)
if (config.nodeEnv === 'development') {
  console.log('\n📋 Configuration:');
  console.log(`   Platform: ${config.platform}`);
  console.log(`   NFC Port: ${config.nfcPort}`);
  console.log(`   NFC Baud Rate: ${config.nfcBaudRate}`);
  console.log(`   Tap Debounce: ${config.tapDebounceMs}ms`);
  console.log(`   Merchant: ${config.merchantName}`);
  console.log(`   Terminal ID: ${config.terminalId}`);
  console.log(`   Webhook Port: ${config.port}`);
  console.log(`   Coinbase API Key: ********`);
  console.log('');
}

export default config;
