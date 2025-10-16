# FastPay Terminal - Quick Start Guide

## What You Just Built

You now have a **working FastPay terminal** with:

✅ **Phase 1 Architecture**: Push payment model via Coinbase Commerce
✅ **NFC Reader**: Python bridge for tap detection
✅ **Node.js Terminal**: Full payment orchestration
✅ **Webhook Server**: Payment confirmation endpoint

## Next Steps to Run

### 1. Configure Environment Variables

```bash
cd terminal
cp .env.example .env
nano .env  # or your favorite editor
```

**Required configuration:**

```bash
# NFC Hardware
NFC_PORT=/dev/tty.usbserial-ABSCDY4Z  # Update to your serial port

# Coinbase Commerce (get from https://commerce.coinbase.com/)
COINBASE_COMMERCE_API_KEY=your_api_key_here
COINBASE_WEBHOOK_SECRET=your_webhook_secret_here

# Merchant Info
MERCHANT_NAME="Your Business Name"
TERMINAL_ID=terminal_001
```

**To find your NFC serial port:**

```bash
# macOS/Linux
ls /dev/tty.usbserial*   # USB-UART adapters
ls /dev/ttyUSB*          # Linux USB serial
ls /dev/ttyAMA*          # Raspberry Pi GPIO UART
```

### 2. Get Coinbase Commerce API Key

1. Go to https://commerce.coinbase.com/
2. Create account (or log in)
3. Navigate to **Settings** → **API Keys**
4. Create new API key
5. Copy API key to `.env` → `COINBASE_COMMERCE_API_KEY`
6. Navigate to **Settings** → **Webhook subscriptions**
7. Add webhook URL: `http://localhost:3000/webhooks/coinbase` (for testing)
8. Copy webhook secret to `.env` → `COINBASE_WEBHOOK_SECRET`

**For remote webhook testing (recommended):**

```bash
# Install ngrok (if not installed)
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start ngrok tunnel
ngrok http 3000

# Copy HTTPS URL from ngrok (e.g., https://abc123.ngrok.io)
# Update Coinbase Commerce webhook URL to: https://abc123.ngrok.io/webhooks/coinbase
```

### 3. Test NFC Hardware (Optional but Recommended)

Before running the full terminal, verify NFC reader works:

```bash
# Test Python NFC reader standalone
python3 scripts/nfc_reader.py
```

**Expected output:**

```json
{"event": "ready", "firmware": "1.6", "port": "/dev/tty.usbserial-ABSCDY4Z", "timestamp": 1728404791}
```

**Tap your phone:**

```json
{"event": "tap", "uid": "086AF124", "timestamp": 1728404792}
```

Press `Ctrl+C` to stop.

### 4. Run the Terminal

```bash
# Development mode (auto-restart on changes)
npm run dev

# Production mode
npm start
```

**Expected startup:**

```
┌────────────────────────────────────────────────────────────────┐
│                                                                  │
│                    💳 FastPay Terminal                          │
│                  Tap-to-Pay Crypto Payments                     │
│                                                                  │
└────────────────────────────────────────────────────────────────┘

🚀 Initializing services...

📋 Configuration:
   Platform: macOS
   NFC Port: /dev/tty.usbserial-ABSCDY4Z
   Merchant: Your Business Name
   Terminal ID: terminal_001
   Webhook Port: 3000
   Coinbase API Key: 12345678...

✅ Webhook server listening on port 3000
   Endpoint: http://localhost:3000/webhooks/coinbase
   Health check: http://localhost:3000/health

🔌 Starting NFC reader...

[NFC] Starting NFC reader process...
[NFC] Script: /Users/.../terminal/scripts/nfc_reader.py
[NFC] Port: /dev/tty.usbserial-ABSCDY4Z
[NFC] Bridge started, waiting for PN532...
[NFC Debug] [NFC] Attempting to connect to PN532...
[NFC] Reader ready - Firmware v1.6 on /dev/tty.usbserial-ABSCDY4Z
✅ NFC reader ready (firmware 1.6)
   Port: /dev/tty.usbserial-ABSCDY4Z

──────────────────────────────────────────────────────────────────
💳 FastPay Terminal Ready
──────────────────────────────────────────────────────────────────

💵 Enter sale amount (USD) or "q" to quit: $
```

### 5. Test End-to-End Payment Flow

**Step 1: Create Charge**

```
💵 Enter sale amount (USD) or "q" to quit: $5.00

⏳ Creating charge for $5.00...

✅ Charge created successfully
   Charge ID: ABC123-DEF456
   Amount: $5.00

📱 Customer: Scan QR code OR tap your phone
──────────────────────────────────────────────────────────────────
[QR CODE DISPLAYS HERE]
──────────────────────────────────────────────────────────────────
🔗 Payment URL: https://commerce.coinbase.com/charges/ABC123-DEF456
──────────────────────────────────────────────────────────────────

⏳ Waiting for payment...
   (Charge expires in 3 minutes)
```

**Step 2: Customer Taps Phone (Optional)**

```
📱 Phone tapped! UID: 086AF124
✅ Tap associated with charge
💡 Customer can now complete payment on their phone
   (Charge ID: ABC123-DEF456)
```

**Step 3: Customer Completes Payment**

Customer either:
- Scans QR code → Opens Coinbase Commerce checkout
- Taps phone → Terminal detects, customer scans QR

Customer approves payment in wallet → Transaction broadcasts to Base L2

**Step 4: Webhook Confirmation**

```
══════════════════════════════════════════════════════════════════
🎉 PAYMENT CONFIRMED!
══════════════════════════════════════════════════════════════════
   Amount: $5.00 USD
   Charge ID: ABC123-DEF456
   Confirmed: 2025-10-15T10:30:00.000Z
══════════════════════════════════════════════════════════════════

[Terminal returns to idle in 3 seconds]

💵 Enter sale amount (USD) or "q" to quit: $
```

## Troubleshooting

### "Missing required environment variable: COINBASE_COMMERCE_API_KEY"

Edit `.env` and add your Coinbase Commerce API key.

### "NFC_PORT environment variable not set"

Edit `.env` and set `NFC_PORT` to your serial device path.

Find it with: `ls /dev/tty.usbserial*`

### "[NFC] Failed to start Python process: spawn python3 ENOENT"

Python 3 is not installed or not in PATH.

**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt install python3
```

### "No module named 'adafruit_pn532'"

Install Python dependencies (recommended: use a virtual environment):

```bash
# Recommended: Use virtual environment for dependency isolation
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install adafruit-circuitpython-pn532 pyserial
```

**Why use a virtual environment?**

Virtual environments keep your project dependencies isolated from system Python packages, preventing conflicts and making it easier to manage requirements.

**Alternative: Global installation (if virtual environment not desired):**

```bash
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
```

### "PN532 not responding"

1. Check wiring (TX/RX must crossover)
2. Verify serial port: `ls /dev/tty.usbserial*`
3. Update `NFC_PORT` in `.env`
4. Power cycle NFC module (unplug USB, wait 5s, replug)
5. Run hardware test: `python3 scripts/nfc_reader.py`

### "Webhook not receiving events"

1. Ensure ngrok is running: `ngrok http 3000`
2. Copy HTTPS URL to Coinbase Commerce webhook settings
3. Verify webhook secret in `.env` matches Coinbase dashboard
4. Check terminal logs for webhook events

### "Permission denied" (Linux/Raspberry Pi)

```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

## Architecture Recap

**Phase 1 (Current): Push Model via Coinbase Commerce**

```
Merchant enters amount
      ↓
Terminal creates Coinbase Commerce charge
      ↓
QR code + NFC tap detection
      ↓
Customer taps → PN532 detects UID → Associates with charge
      ↓
Customer scans QR → Opens Coinbase Commerce checkout
      ↓
Customer approves → PUSHES payment to deposit address
      ↓
Coinbase monitors blockchain → Sends webhook
      ↓
Terminal receives webhook → Shows "Payment Confirmed!"
```

**Phase 2 (Future): Pull Model via Smart Contracts**

See `terminal-implementation.md` for Phase 2 pull payment architecture with on-chain request contracts.

## What's Next?

**Immediate (This Week):**
- [ ] Get Coinbase Commerce API key
- [ ] Configure `.env`
- [ ] Test first payment
- [ ] Set up ngrok for webhook testing

**Week 3:**
- [ ] End-to-end testing with real wallet
- [ ] Measure payment completion time (<10s target)
- [ ] Deploy to Raspberry Pi (optional)

**Phase 2 (Months 2-3):**
- [ ] Build pull payment smart contracts
- [ ] Add on-chain request flow
- [ ] Compare push vs pull adoption

## Need Help?

**Documentation:**
- `README.md` - Project overview
- `terminal-implementation.md` - Detailed architecture and implementation plan
- `PAYMENT-INTENT-DECISION.md` - Architecture decision rationale
- `../CLAUDE.md` - Development guide

**Common Issues:**
See `../CLAUDE.md` → "Common Issues and Solutions"

**Hardware Setup:**
See `../test/SETUP-SUCCESS.md` for verified wiring diagram

---

**You're ready to process your first payment!** 🎉

Get your Coinbase Commerce API key and start the terminal:

```bash
cd terminal
npm run dev
```