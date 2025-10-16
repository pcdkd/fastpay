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

  switch (os) {
    case 'darwin':
      // macOS - USB-to-UART converter (no default, must be explicitly set)
      return {
        platform: 'macOS',
        defaultPort: null,
        needsDtrRtsFix: true,
      };

    case 'linux':
      if (existsSync('/dev/ttyAMA0')) {
        // Raspberry Pi - GPIO UART
        return {
          platform: 'Raspberry Pi',
          defaultPort: '/dev/ttyAMA0',
          needsDtrRtsFix: false,
        };
      }
      // Generic Linux - USB-to-UART or no port detected
      return {
        platform: 'Linux',
        defaultPort: existsSync('/dev/ttyUSB0') ? '/dev/ttyUSB0' : null,
        needsDtrRtsFix: true,
      };

    default:
      // Fallback for other unknown platforms
      return {
        platform: 'Unknown',
        defaultPort: null,
        needsDtrRtsFix: true,
      };
  }
}

/**
 * Validate integer is within acceptable range
 */
function validateInteger(value, name, min, max) {
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new Error(
      `Invalid ${name}: ${value}. Must be an integer between ${min} and ${max}.`
    );
  }
  return value;
}

/**
 * Parse and validate an integer environment variable
 */
function getValidatedIntEnv(name, defaultValue, min, max) {
  const valueStr = process.env[name] || String(defaultValue);
  const value = parseInt(valueStr, 10);
  return validateInteger(value, name, min, max);
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
const nfcBaudRate = getValidatedIntEnv('NFC_BAUD_RATE', 115200, 9600, 921600);
const tapDebounceMs = getValidatedIntEnv('NFC_TAP_DEBOUNCE_MS', 1000, 100, 10000);
const port = getValidatedIntEnv('PORT', 3000, 1, 65535);
const chainId = getValidatedIntEnv('CHAIN_ID', 8453, 1, 2147483647);

// Validate NFC port is configured
validateNfcPort(nfcPort, platformInfo.platform);

// Extract all configuration values
const coinbaseApiKey = process.env.COINBASE_COMMERCE_API_KEY;
const webhookSecret = process.env.COINBASE_WEBHOOK_SECRET;
const merchantName = process.env.MERCHANT_NAME;
const terminalId = process.env.TERMINAL_ID;
const nodeEnv = process.env.NODE_ENV || 'development';
const baseRpcUrl = process.env.BASE_RPC_URL;

// Constants for blockchain (Phase 2)
const DEFAULT_USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const usdcAddress = process.env.USDC_ADDRESS || DEFAULT_USDC_ADDRESS;

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
  coinbaseApiKey,
  webhookSecret,

  // Merchant
  merchantName,
  terminalId,

  // Server
  port,
  nodeEnv,

  // Optional: Blockchain (Phase 2)
  baseRpcUrl,
  chainId,
  usdcAddress,
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
  console.log(`   Webhook Secret: ********`);
  console.log('');
}

export default config;
