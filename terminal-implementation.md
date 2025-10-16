# FastPay Terminal Implementation Plan

**Status:** Planning Phase
**Goal:** Build Node.js terminal software with Python NFC bridge for reader mode architecture
**Timeline:** Week 2-3 of Phase 1

---

## Important: Payment Model Clarification

**Phase 1 (Current Implementation): PUSH MODEL via Coinbase Commerce**

This implementation uses the standard Coinbase Commerce API flow:
- Merchant creates charge (off-chain via API)
- Customer PUSHES payment to Commerce deposit address
- Commerce monitors blockchain and sends webhook confirmation
- **This is NOT a "hanging transaction" or pull payment model**
- **The "pull" refers to merchant-initiated UX, not on-chain payment mechanics**

**Phase 2 (Future Enhancement): PULL MODEL via Smart Contracts**

Future architecture will add true pull payments:
- Merchant creates on-chain payment request (hanging transaction)
- Customer becomes counterparty by signing/completing request
- Smart contract executes atomic transfer
- Bypasses Commerce API for payment (may use for accounting)
- **This IS a true pull payment model with on-chain requests**

**Why Hybrid Approach:**
- Phase 1 de-risks with proven Commerce infrastructure
- Gets to market fast (2-3 weeks vs 2-3 months)
- Proves NFC demand before building complex contracts
- Phase 2 shows Coinbase the future of Commerce (pull payments)
- Positions for acquisition: "Built on your stack, here's v2"

---

## Architecture Overview (Phase 1: Commerce API Push Model)

```
┌─────────────────────────────────────────────────────────────┐
│                    FastPay Terminal                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Node.js Layer (Business Logic)              │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  • Coinbase Commerce API (charge creation)           │   │
│  │  • QR code generation (hosted checkout URL)          │   │
│  │  • Webhook server (payment confirmations)            │   │
│  │  • Tap association (UID → charge mapping)            │   │
│  │  • Terminal UI (console output)                      │   │
│  └─────────────────┬────────────────────────────────────┘   │
│                    │ IPC (stdin/stdout JSON)                 │
│  ┌─────────────────▼────────────────────────────────────┐   │
│  │         Python NFC Bridge (Hardware Layer)            │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  • PN532 reader mode initialization                  │   │
│  │  • Continuous tap scanning                           │   │
│  │  • UID extraction                                    │   │
│  │  • Tap event emission (JSON to stdout)              │   │
│  └─────────────────┬────────────────────────────────────┘   │
│                    │ UART (115200 baud)                      │
│  ┌─────────────────▼────────────────────────────────────┐   │
│  │              PN532 NFC Module                         │   │
│  │          (Reader Mode - Tap Detection)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘

External Services:
├── Coinbase Commerce API (charge creation, hosted checkout)
├── Base L2 RPC (optional on-chain monitoring)
└── Customer Wallet App (payment completion)
```

---

## Implementation Workflow (Graphite-Style Stacks)

### Stack 1: Foundation & Project Setup
**Goal:** Create terminal directory structure, dependencies, basic configuration

#### PR 1.1: Project Structure
- [ ] Create `terminal/` directory
- [ ] Create subdirectories: `src/`, `scripts/`, `config/`
- [ ] Initialize `package.json` with Node.js v20 target
- [ ] Add `.gitignore` for `node_modules/`, `.env`
- [ ] Create `terminal/README.md` with quick start

**Files Created:**
```
terminal/
├── package.json
├── .gitignore
├── .env.example
├── README.md
├── src/
├── scripts/
└── config/
```

**Dependencies (package.json):**
```json
{
  "name": "fastpay-terminal",
  "version": "0.1.0",
  "type": "module",
  "engines": {
    "node": ">=20.0.0"
  },
  "dependencies": {
    "coinbase-commerce-node": "^1.0.4",
    "dotenv": "^16.4.5",
    "express": "^4.18.2",
    "qrcode": "^1.5.3"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  },
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "test": "echo 'Tests coming in Week 3'"
  }
}
```

**Acceptance Criteria:**
- [ ] `npm install` completes without errors
- [ ] Directory structure matches planned layout
- [ ] `.env.example` documents all required environment variables

---

#### PR 1.2: Environment Configuration
- [ ] Create `.env.example` with all required variables
- [ ] Create `config/index.js` to load and validate environment
- [ ] Add validation for required vars (NFC_PORT, COINBASE_API_KEY)
- [ ] Add platform detection (macOS vs Raspberry Pi)

**Files Created:**
- `terminal/.env.example`
- `terminal/config/index.js`

**Environment Variables:**
```bash
# NFC Hardware
NFC_PORT=/dev/tty.usbserial-ABSCDY4Z  # macOS: USB-UART, Pi: /dev/ttyAMA0
NFC_BAUD_RATE=115200
NFC_TAP_DEBOUNCE_MS=1000

# Coinbase Commerce
COINBASE_COMMERCE_API_KEY=
COINBASE_WEBHOOK_SECRET=

# Merchant
MERCHANT_NAME="FastPay Test Terminal"
TERMINAL_ID=terminal_001

# Server
PORT=3000
NODE_ENV=development

# Optional: Direct blockchain monitoring (Week 3)
BASE_RPC_URL=https://mainnet.base.org
CHAIN_ID=8453
USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
```

**Config Validation Logic:**
```javascript
// config/index.js
const requiredVars = ['NFC_PORT', 'COINBASE_COMMERCE_API_KEY', 'MERCHANT_NAME'];
for (const varName of requiredVars) {
  if (!process.env[varName]) {
    throw new Error(`Missing required environment variable: ${varName}`);
  }
}
```

**Acceptance Criteria:**
- [ ] Missing required vars throw clear error messages
- [ ] Platform detection works (macOS vs Pi)
- [ ] Config exports clean interface for other modules

---

### Stack 2: Python NFC Bridge (Hardware Layer)
**Goal:** Port `test/detect-phone-tap.py` to production-ready NFC reader with JSON IPC

#### PR 2.1: NFC Reader Base Implementation
- [ ] Copy `test/detect-phone-tap.py` → `scripts/nfc_reader.py`
- [ ] Add JSON output via stdout (structured tap events)
- [ ] Add stderr logging (diagnostics, separate from IPC)
- [ ] Implement graceful shutdown on SIGINT/SIGTERM
- [ ] Add UID deduplication (ignore rapid re-taps)

**Files Created:**
- `terminal/scripts/nfc_reader.py`

**IPC Protocol (stdout JSON):**
```json
{"event": "ready", "firmware": "1.6", "port": "/dev/tty.usbserial-ABSCDY4Z"}
{"event": "tap", "uid": "086AF124", "timestamp": 1728404791}
{"event": "error", "message": "PN532 not responding", "fatal": true}
{"event": "shutdown", "reason": "SIGTERM received"}
```

**Key Enhancements:**
```python
import json
import sys
import time
from collections import deque

# UID deduplication (ignore re-taps within debounce window)
recent_taps = deque(maxlen=10)
DEBOUNCE_MS = int(os.getenv('NFC_TAP_DEBOUNCE_MS', '1000'))

def emit_event(event_type, **data):
    """Output JSON event to stdout (Node.js reads this)"""
    event = {"event": event_type, "timestamp": int(time.time()), **data}
    print(json.dumps(event), flush=True)

def log_debug(message):
    """Output debug info to stderr (doesn't interfere with IPC)"""
    print(f"[NFC] {message}", file=sys.stderr, flush=True)

# Continuous scanning loop
while True:
    uid = pn532.read_passive_target(timeout=0.5)

    if uid:
        uid_hex = ''.join([f'{b:02X}' for b in uid])

        # Check debounce
        now = time.time()
        if not any(tap['uid'] == uid_hex and (now - tap['time']) < DEBOUNCE_MS/1000
                   for tap in recent_taps):
            recent_taps.append({'uid': uid_hex, 'time': now})
            emit_event('tap', uid=uid_hex)
        else:
            log_debug(f"Debounced re-tap: {uid_hex}")
```

**Acceptance Criteria:**
- [ ] Outputs valid JSON to stdout (parseable by Node.js)
- [ ] Debug logs go to stderr (don't break IPC)
- [ ] Debouncing prevents rapid re-tap spam
- [ ] Graceful shutdown on Ctrl+C
- [ ] Can run standalone: `python3 scripts/nfc_reader.py`

---

#### PR 2.2: NFC Reader Error Handling & Reconnection
- [ ] Add PN532 reconnection logic (handle USB disconnect)
- [ ] Add timeout configuration from environment
- [ ] Add "heartbeat" events (prove process is alive)
- [ ] Handle missing Adafruit library gracefully

**Enhanced Error Handling:**
```python
MAX_RETRIES = 5
retry_count = 0

while retry_count < MAX_RETRIES:
    try:
        # Initialize PN532
        uart = serial.Serial(PORT, BAUD_RATE, timeout=1)
        uart.dtr = False
        uart.rts = False
        time.sleep(0.2)

        pn532 = PN532_UART(uart, debug=False)
        pn532.SAM_configuration()

        firmware = pn532.firmware_version
        emit_event('ready', firmware=f"{firmware[1]}.{firmware[2]}", port=PORT)
        retry_count = 0  # Reset on success

        # Main scanning loop
        while True:
            # ... tap detection ...

    except serial.SerialException as e:
        log_debug(f"Serial error: {e}")
        emit_event('error', message=str(e), fatal=False)
        retry_count += 1
        time.sleep(2 ** retry_count)  # Exponential backoff

    except KeyboardInterrupt:
        emit_event('shutdown', reason='SIGINT')
        break

    except Exception as e:
        log_debug(f"Unexpected error: {e}")
        emit_event('error', message=str(e), fatal=True)
        break

sys.exit(1 if retry_count >= MAX_RETRIES else 0)
```

**Acceptance Criteria:**
- [ ] Reconnects automatically if USB unplugged/replugged
- [ ] Exponential backoff prevents CPU spin on persistent errors
- [ ] Fatal errors exit with code 1 (Node.js can detect)
- [ ] Heartbeat events every 30s (prove not hung)

---

### Stack 3: Node.js Core Modules (Business Logic)
**Goal:** Implement charge creation, tap association, payment monitoring

#### PR 3.1: NFC Bridge Wrapper (Node.js ↔ Python IPC)
- [ ] Create `src/nfc.js` - Spawn Python process, parse JSON events
- [ ] Implement event emitter pattern (tap, error, ready)
- [ ] Handle Python process crashes (respawn)
- [ ] Add graceful shutdown (kill Python on Node exit)

**Files Created:**
- `terminal/src/nfc.js`

**Implementation:**
```javascript
// src/nfc.js
import { spawn } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export class NFCBridge extends EventEmitter {
  constructor(config) {
    super();
    this.config = config;
    this.process = null;
    this.isShuttingDown = false;
  }

  start() {
    const scriptPath = path.join(__dirname, '../scripts/nfc_reader.py');

    this.process = spawn('python3', [scriptPath], {
      env: {
        ...process.env,
        NFC_PORT: this.config.nfcPort,
        NFC_BAUD_RATE: this.config.nfcBaudRate,
        NFC_TAP_DEBOUNCE_MS: this.config.tapDebounceMs,
      },
      stdio: ['ignore', 'pipe', 'pipe'],  // stdin, stdout, stderr
    });

    // Parse JSON events from stdout
    this.process.stdout.on('data', (data) => {
      const lines = data.toString().split('\n').filter(line => line.trim());

      for (const line of lines) {
        try {
          const event = JSON.parse(line);
          this.emit(event.event, event);
        } catch (err) {
          console.error('[NFC] Invalid JSON from Python:', line);
        }
      }
    });

    // Log stderr (debug output)
    this.process.stderr.on('data', (data) => {
      console.error('[NFC Debug]', data.toString().trim());
    });

    // Handle process exit
    this.process.on('exit', (code) => {
      if (!this.isShuttingDown) {
        console.error(`[NFC] Python process exited with code ${code}, restarting...`);
        setTimeout(() => this.start(), 2000);
      }
    });

    console.log('[NFC] Bridge started, waiting for PN532...');
  }

  stop() {
    this.isShuttingDown = true;
    if (this.process) {
      this.process.kill('SIGTERM');
      this.process = null;
    }
  }
}
```

**Acceptance Criteria:**
- [ ] Spawns Python process successfully
- [ ] Parses JSON events from stdout
- [ ] Emits 'tap', 'ready', 'error' events
- [ ] Restarts Python if it crashes
- [ ] Cleans up process on shutdown

---

#### PR 3.2: Coinbase Commerce Integration
- [ ] Create `src/commerce.js` - Charge creation wrapper
- [ ] Implement charge creation with metadata
- [ ] Add charge retrieval by ID
- [ ] Add error handling for API failures

**Files Created:**
- `terminal/src/commerce.js`

**Implementation:**
```javascript
// src/commerce.js
import coinbaseCommerce from 'coinbase-commerce-node';

const { Client, resources } = coinbaseCommerce;
const { Charge } = resources;

export class CommerceClient {
  constructor(apiKey) {
    Client.init(apiKey);
    this.apiKey = apiKey;
  }

  async createCharge({ amount, currency = 'USD', description, terminalId }) {
    try {
      const chargeData = {
        name: 'FastPay Purchase',
        description,
        local_price: {
          amount: amount.toFixed(2),
          currency,
        },
        pricing_type: 'fixed_price',
        metadata: {
          terminal_id: terminalId,
          tap_uid: null,  // Will be updated when customer taps
          created_at: new Date().toISOString(),
        },
      };

      const charge = await Charge.create(chargeData);

      return {
        id: charge.id,
        hostedUrl: charge.hosted_url,
        addresses: charge.addresses,
        pricing: charge.pricing,
        expiresAt: charge.expires_at,
      };
    } catch (error) {
      console.error('[Commerce] Charge creation failed:', error.message);
      throw error;
    }
  }

  async getCharge(chargeId) {
    try {
      const charge = await Charge.retrieve(chargeId);
      return {
        id: charge.id,
        status: charge.timeline[charge.timeline.length - 1].status,
        payments: charge.payments,
      };
    } catch (error) {
      console.error('[Commerce] Charge retrieval failed:', error.message);
      throw error;
    }
  }
}
```

**Acceptance Criteria:**
- [ ] Creates charges via Coinbase Commerce API
- [ ] Returns hosted URL for customer payment
- [ ] Includes terminal metadata
- [ ] Handles API errors gracefully

---

#### PR 3.3: Payment Request Manager
- [ ] Create `src/payment.js` - Charge lifecycle management
- [ ] Implement pending charge tracking (chargeId → tap UID mapping)
- [ ] Add charge expiration handling (3-minute timeout)
- [ ] Add tap association logic

**Files Created:**
- `terminal/src/payment.js`

**Implementation:**
```javascript
// src/payment.js
import QRCode from 'qrcode';

export class PaymentManager {
  constructor(commerceClient, terminalId) {
    this.commerce = commerceClient;
    this.terminalId = terminalId;
    this.pendingCharges = new Map();  // chargeId → charge data
    this.tapMap = new Map();  // tapUid → chargeId
  }

  async createPaymentRequest(amount, description) {
    const charge = await this.commerce.createCharge({
      amount,
      description,
      terminalId: this.terminalId,
    });

    // Track pending charge
    this.pendingCharges.set(charge.id, {
      ...charge,
      createdAt: Date.now(),
      tapUid: null,
    });

    // Auto-expire after 3 minutes
    setTimeout(() => {
      if (this.pendingCharges.has(charge.id)) {
        console.log(`[Payment] Charge ${charge.id} expired`);
        this.pendingCharges.delete(charge.id);
      }
    }, 180_000);

    return charge;
  }

  async associateTap(tapUid) {
    // Find most recent pending charge
    const charges = Array.from(this.pendingCharges.values())
      .sort((a, b) => b.createdAt - a.createdAt);

    if (charges.length === 0) {
      console.warn('[Payment] Tap received but no pending charges');
      return null;
    }

    const charge = charges[0];

    if (charge.tapUid) {
      console.warn('[Payment] Charge already associated with tap');
      return null;
    }

    // Associate tap with charge
    charge.tapUid = tapUid;
    this.tapMap.set(tapUid, charge.id);

    console.log(`[Payment] Tap ${tapUid} associated with charge ${charge.id}`);
    return charge;
  }

  async generateQR(hostedUrl) {
    try {
      const qr = await QRCode.toString(hostedUrl, { type: 'terminal', small: true });
      return qr;
    } catch (error) {
      console.error('[Payment] QR generation failed:', error.message);
      return null;
    }
  }

  getPendingCharge(chargeId) {
    return this.pendingCharges.get(chargeId);
  }

  completePurchase(chargeId) {
    const charge = this.pendingCharges.get(chargeId);
    if (charge && charge.tapUid) {
      this.tapMap.delete(charge.tapUid);
    }
    this.pendingCharges.delete(chargeId);
  }
}
```

**Acceptance Criteria:**
- [ ] Creates payment requests with expiration
- [ ] Associates taps with most recent pending charge
- [ ] Generates QR codes for hosted URLs
- [ ] Cleans up expired charges

---

#### PR 3.4: Webhook Server (Payment Confirmations)
- [ ] Create `src/webhook.js` - Express server for Coinbase webhooks
- [ ] Implement signature verification
- [ ] Handle `charge:confirmed` events
- [ ] Emit payment completion events

**Files Created:**
- `terminal/src/webhook.js`

**Implementation:**
```javascript
// src/webhook.js
import express from 'express';
import coinbaseCommerce from 'coinbase-commerce-node';

const { Webhook } = coinbaseCommerce;

export function createWebhookServer(config, paymentManager) {
  const app = express();

  // Raw body needed for signature verification
  app.use(express.json({
    verify: (req, res, buf) => {
      req.rawBody = buf.toString();
    },
  }));

  app.post('/webhooks/coinbase', (req, res) => {
    const signature = req.headers['x-cc-webhook-signature'];

    try {
      // Verify webhook signature
      const event = Webhook.verifyEventBody(
        req.rawBody,
        signature,
        config.webhookSecret
      );

      console.log(`[Webhook] Received: ${event.type}`);

      if (event.type === 'charge:confirmed') {
        const charge = event.data;
        console.log(`✅ Payment confirmed for charge: ${charge.id}`);

        // Emit event (main app listens for this)
        app.emit('payment:confirmed', {
          chargeId: charge.id,
          amount: charge.pricing.local.amount,
          payments: charge.payments,
        });

        paymentManager.completePurchase(charge.id);
      }

      res.sendStatus(200);
    } catch (error) {
      console.error('[Webhook] Verification failed:', error.message);
      res.sendStatus(400);
    }
  });

  return app;
}
```

**Acceptance Criteria:**
- [ ] Verifies Coinbase webhook signatures
- [ ] Handles `charge:confirmed` events
- [ ] Emits events for main app to consume
- [ ] Returns 200 for valid webhooks

---

### Stack 4: Terminal Application (Main Loop)
**Goal:** Wire everything together, implement merchant-facing UI

#### PR 4.1: Main Terminal Application
- [ ] Create `src/index.js` - Main application entry point
- [ ] Wire up NFC bridge, Commerce client, Payment manager
- [ ] Implement terminal UI (console-based)
- [ ] Add payment flow state machine

**Files Created:**
- `terminal/src/index.js`

**Implementation:**
```javascript
// src/index.js
import 'dotenv/config';
import readline from 'readline';
import config from '../config/index.js';
import { NFCBridge } from './nfc.js';
import { CommerceClient } from './commerce.js';
import { PaymentManager } from './payment.js';
import { createWebhookServer } from './webhook.js';

// Initialize services
const commerceClient = new CommerceClient(config.coinbaseApiKey);
const paymentManager = new PaymentManager(commerceClient, config.terminalId);
const nfcBridge = new NFCBridge(config);

// Start webhook server
const webhookApp = createWebhookServer(config, paymentManager);
const server = webhookApp.listen(config.port, () => {
  console.log(`[Server] Webhook endpoint: http://localhost:${config.port}/webhooks/coinbase`);
});

// Terminal UI state
let currentState = 'IDLE';  // IDLE, WAITING_FOR_PAYMENT, COMPLETED

// NFC event handlers
nfcBridge.on('ready', (event) => {
  console.log(`✅ NFC reader ready (firmware ${event.firmware})`);
  console.log('\n💳 FastPay Terminal Ready');
  console.log('─'.repeat(50));
  promptForAmount();
});

nfcBridge.on('tap', async (event) => {
  console.log(`\n📱 Phone tapped! UID: ${event.uid}`);

  if (currentState === 'WAITING_FOR_PAYMENT') {
    const charge = await paymentManager.associateTap(event.uid);
    if (charge) {
      console.log('✅ Tap associated with charge');
      console.log('💡 Customer can now complete payment on their phone');
    }
  } else {
    console.log('⚠️  No pending payment request');
  }
});

nfcBridge.on('error', (event) => {
  console.error(`❌ NFC Error: ${event.message}`);
  if (event.fatal) {
    process.exit(1);
  }
});

// Webhook event handlers
webhookApp.on('payment:confirmed', (event) => {
  console.log('\n🎉 PAYMENT CONFIRMED!');
  console.log(`Amount: $${event.amount}`);
  console.log(`Charge ID: ${event.chargeId}`);
  console.log('─'.repeat(50));

  currentState = 'COMPLETED';
  setTimeout(() => {
    currentState = 'IDLE';
    promptForAmount();
  }, 3000);
});

// Terminal UI
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function promptForAmount() {
  if (currentState !== 'IDLE') return;

  rl.question('\n💵 Enter sale amount (USD): $', async (input) => {
    const amount = parseFloat(input);

    if (isNaN(amount) || amount <= 0) {
      console.log('❌ Invalid amount');
      promptForAmount();
      return;
    }

    try {
      currentState = 'WAITING_FOR_PAYMENT';

      const charge = await paymentManager.createPaymentRequest(
        amount,
        `${config.merchantName} - Terminal ${config.terminalId}`
      );

      console.log(`\n✅ Charge created: ${charge.id}`);
      console.log(`Amount: $${amount.toFixed(2)}`);
      console.log('\n📱 Customer: Scan QR code OR tap your phone');

      const qr = await paymentManager.generateQR(charge.hostedUrl);
      if (qr) {
        console.log(qr);
      }

      console.log(`\n🔗 Payment URL: ${charge.hostedUrl}`);
      console.log('\n⏳ Waiting for payment...');

    } catch (error) {
      console.error('❌ Failed to create charge:', error.message);
      currentState = 'IDLE';
      promptForAmount();
    }
  });
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n👋 Shutting down...');
  nfcBridge.stop();
  server.close();
  rl.close();
  process.exit(0);
});

// Start NFC bridge
nfcBridge.start();
```

**Acceptance Criteria:**
- [ ] Terminal starts and initializes NFC reader
- [ ] Prompts merchant for sale amount
- [ ] Creates charge and displays QR code
- [ ] Detects phone taps and associates with charge
- [ ] Shows payment confirmation from webhook
- [ ] Handles graceful shutdown (Ctrl+C)

---

#### PR 4.2: Terminal UI Enhancements
- [ ] Add colored output (success=green, error=red, info=blue)
- [ ] Add charge expiration countdown
- [ ] Add payment status polling (fallback if webhook fails)
- [ ] Add transaction history log

**Enhanced UI Features:**
```javascript
import chalk from 'chalk';  // Add to package.json

// Colored output
console.log(chalk.green('✅ Payment confirmed!'));
console.log(chalk.red('❌ Charge creation failed'));
console.log(chalk.blue('💡 Waiting for tap...'));

// Countdown timer
let expiresAt = Date.now() + 180_000;
const countdown = setInterval(() => {
  const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
  process.stdout.write(`\r⏳ Expires in: ${remaining}s `);
  if (remaining === 0) clearInterval(countdown);
}, 1000);

// Transaction log (append to file)
import fs from 'fs';
fs.appendFileSync('transactions.log', JSON.stringify({
  timestamp: new Date().toISOString(),
  chargeId: charge.id,
  amount,
  tapUid,
  status: 'confirmed',
}) + '\n');
```

**Acceptance Criteria:**
- [ ] Terminal output is color-coded and easy to read
- [ ] Expiration countdown updates in real-time
- [ ] Transactions logged to file
- [ ] Fallback polling if webhook delivery delayed

---

### Stack 5: Testing & Documentation
**Goal:** Validate end-to-end flow, document setup for merchants

#### PR 5.1: End-to-End Testing
- [ ] Create `test-flow.md` - Manual testing checklist
- [ ] Test with Coinbase Commerce sandbox
- [ ] Test with real phone NFC tap
- [ ] Test edge cases (expired charge, double-tap, etc.)

**Testing Checklist:**
```markdown
## Terminal Software E2E Test

### Prerequisites
- [ ] Coinbase Commerce API key configured
- [ ] PN532 module connected and responding
- [ ] Webhook endpoint accessible (use ngrok for local testing)

### Test Cases

**Happy Path:**
1. [ ] Start terminal: `npm run dev`
2. [ ] NFC reader initializes successfully
3. [ ] Enter sale amount: $5.00
4. [ ] Charge created, QR code displayed
5. [ ] Tap phone on PN532 module
6. [ ] Tap UID logged and associated with charge
7. [ ] Open hosted URL on phone, complete payment
8. [ ] Webhook fires, terminal shows confirmation
9. [ ] Terminal returns to idle state

**Edge Cases:**
- [ ] Tap phone with no pending charge → Warning displayed
- [ ] Create charge, wait 3 minutes → Charge expires
- [ ] Tap same phone twice within 1 second → Second tap ignored (debounced)
- [ ] Unplug PN532 during operation → Error logged, reconnects automatically
- [ ] Webhook signature invalid → Rejected with 400 status

**Error Handling:**
- [ ] Missing .env variables → Clear error message, exits
- [ ] Coinbase API key invalid → Charge creation fails gracefully
- [ ] Python script crashes → Node.js restarts it automatically
```

**Acceptance Criteria:**
- [ ] All happy path tests pass
- [ ] Edge cases handled gracefully
- [ ] No uncaught exceptions

---

#### PR 5.2: Deployment Documentation
- [ ] Create `terminal/DEPLOYMENT.md` - Production setup guide
- [ ] Document Raspberry Pi migration steps
- [ ] Add systemd service configuration
- [ ] Add troubleshooting guide

**Deployment Guide Structure:**
```markdown
# FastPay Terminal Deployment

## Hardware Setup
- Raspberry Pi 4 (2GB+ RAM)
- PN532 NFC module
- Wiring diagram (GPIO UART)

## Software Installation
1. Install Node.js v20
2. Install Python 3.11+
3. Install system dependencies
4. Clone repository
5. Configure environment variables
6. Test hardware

## Systemd Service
- Auto-start on boot
- Restart on crash
- Log to journalctl

## Monitoring
- Check logs: journalctl -u fastpay-terminal
- Health check endpoint
- NFC reader status

## Troubleshooting
- PN532 not responding
- Webhook delivery issues
- Serial port permissions
```

**Acceptance Criteria:**
- [ ] Deployment guide is complete and tested
- [ ] Raspberry Pi systemd service works
- [ ] Includes rollback procedure

---

## Implementation Timeline

### Week 2 (Current)
- **Days 1-2:** Stack 1 (Foundation) + Stack 2 (NFC Bridge)
  - PR 1.1, 1.2: Project setup, configuration
  - PR 2.1, 2.2: Python NFC reader production version

- **Days 3-4:** Stack 3 (Node.js Core)
  - PR 3.1: NFC bridge wrapper (IPC)
  - PR 3.2: Coinbase Commerce integration
  - PR 3.3: Payment manager
  - PR 3.4: Webhook server

- **Days 5-7:** Stack 4 (Terminal App)
  - PR 4.1: Main application loop
  - PR 4.2: UI enhancements

### Week 3
- **Days 1-2:** Stack 5 (Testing)
  - PR 5.1: E2E testing
  - PR 5.2: Deployment docs

- **Days 3-5:** Raspberry Pi Migration
  - Test on actual Pi hardware
  - Deploy to pilot merchant

- **Days 6-7:** Polish & Demo
  - Record video demo
  - Prepare stakeholder presentation

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Merchant enters amount, charge created
- [ ] QR code displayed in terminal
- [ ] Phone tap detected and associated with charge
- [ ] Customer completes payment via hosted checkout
- [ ] Webhook confirms payment (<10 seconds total)
- [ ] Terminal shows success, returns to idle

### Performance Targets:
- [ ] End-to-end payment: <10 seconds
- [ ] Tap detection latency: <100ms
- [ ] Charge creation: <2 seconds
- [ ] Webhook confirmation: <5 seconds
- [ ] NFC reader uptime: >99% (auto-reconnect)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Coinbase Commerce API downtime | High | Add retry logic, fallback to QR-only mode |
| PN532 USB disconnect | Medium | Auto-reconnection with exponential backoff |
| Webhook delivery failure | Medium | Implement polling fallback, manual check endpoint |
| Python process crash | Low | Auto-restart via Node.js supervisor |
| Serial port permissions (Pi) | Low | Document dialout group requirement |

---

## Dependencies

### External Services
- **Coinbase Commerce:** Charge creation, hosted checkout, webhooks
- **Base L2:** (Week 3) Optional on-chain monitoring
- **Ngrok:** (Development) Expose local webhook endpoint

### Hardware
- **PN532 NFC module:** Already validated with `test/detect-phone-tap.py`
- **FT232 USB-UART:** macOS development
- **Raspberry Pi GPIO UART:** Production deployment

### Libraries
- **Node.js:** coinbase-commerce-node, express, qrcode, dotenv, chalk
- **Python:** adafruit-circuitpython-pn532, pyserial (already installed)

---

## Notes

### Architecture Decisions
- **Reader mode:** PN532 only detects taps, doesn't transfer payment data
- **Coinbase Commerce:** Handles payment complexity (hosted checkout, blockchain)
- **IPC via JSON:** Python → Node.js communication via stdout
- **Webhook primary:** Polling is fallback only

### Future Enhancements (Phase 2+)

**Phase 2: Pull Payment Smart Contracts (Months 2-3)**

Add true pull payment model alongside Commerce API:

```solidity
// contracts/FastPayPull.sol
contract FastPayPull {
    struct PaymentRequest {
        address merchant;
        address token;
        uint256 amount;
        uint256 deadline;
        bool completed;
    }

    mapping(bytes32 => PaymentRequest) public requests;

    // Merchant creates on-chain request
    function createRequest(
        address token,
        uint256 amount,
        uint256 deadline
    ) external returns (bytes32 requestId) {
        requestId = keccak256(abi.encodePacked(
            msg.sender, token, amount, block.timestamp
        ));

        requests[requestId] = PaymentRequest({
            merchant: msg.sender,
            token: token,
            amount: amount,
            deadline: deadline,
            completed: false
        });

        emit RequestCreated(requestId, msg.sender, amount);
    }

    // Customer completes request (becomes counterparty)
    function completeRequest(bytes32 requestId) external {
        PaymentRequest storage req = requests[requestId];
        require(!req.completed, "Already completed");
        require(block.timestamp <= req.deadline, "Expired");

        IERC20(req.token).transferFrom(
            msg.sender, req.merchant, req.amount
        );

        req.completed = true;
        emit RequestCompleted(requestId, msg.sender);
    }
}
```

**NFC Payload (Phase 2):**
```json
{
  "version": "2.0",
  "mode": "pull",
  "contractAddress": "0xFASTPAY_PULL_CONTRACT",
  "requestId": "0xREQUEST_ID_HASH",
  "merchant": "0xMERCHANT_ADDRESS",
  "amount": "5000000",
  "token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "deadline": 1728000180
}
```

**Benefits of Pull Model:**
- ✅ Merchant controls transaction parameters (can't overpay/underpay)
- ✅ Atomic settlement (no escrow complexity)
- ✅ True "pull" payment (merchant requests, customer completes)
- ✅ Customer can't send to wrong address
- ✅ Instant finality (no webhook delays)

**Phase 2 Terminal Architecture:**
```javascript
// terminal/src/payment.js (Phase 2 enhancement)

class PaymentManager {
  async createPaymentRequest(amount, description) {
    if (config.paymentMode === 'pull') {
      // Create on-chain request via smart contract
      const tx = await fastPayContract.createRequest(
        USDC_ADDRESS,
        ethers.parseUnits(amount.toString(), 6),
        Math.floor(Date.now() / 1000) + 180 // 3 min deadline
      );
      const receipt = await tx.wait();
      const requestId = receipt.events[0].args.requestId;

      return {
        mode: 'pull',
        requestId,
        onChainTx: receipt.transactionHash,
      };
    } else {
      // Phase 1: Use Commerce API (current implementation)
      return await this.commerce.createCharge({ amount, description });
    }
  }
}
```

**Merchant Choice:**
```bash
# Terminal config
PAYMENT_MODE=push   # Phase 1: Commerce API (default)
PAYMENT_MODE=pull   # Phase 2: Smart contract pull payments
PAYMENT_MODE=hybrid # Phase 2: Merchant chooses per-transaction
```

**Phase 2 Positioning to Coinbase:**
- "We proved NFC works with Commerce API (Phase 1)"
- "Here's v2 with true pull payments (merchant-controlled requests)"
- "Data shows [X%] faster checkout with pull vs push"
- "Recommend evolving Commerce API to support pull payment mode"
- "Acquire both: proven product + future architecture"

**Other Phase 2+ Enhancements:**
- Multiple pending charges (multi-merchant support)
- LCD display (amount, QR code, status)
- Receipt printer integration
- POS system API (Square, Shopify)
- Gas sponsorship (EIP-4337) - merchant pays customer's gas
- Custom companion app (WalletConnect for better UX)

---

**Status:** Ready to implement Phase 1
**Next Action:** Create PR 1.1 (Project Structure)
**Phase 2 Timeline:** Months 2-3 (after proving Phase 1 market fit)
