# FastPay Terminal

Node.js terminal software for FastPay NFC tap-to-pay crypto payments.

## Quick Start

### Prerequisites

- Node.js v20+
- Python 3.11+ with dependencies:
  ```bash
  pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
  ```
- PN532 NFC module connected via USB-UART or GPIO UART
- Coinbase Commerce API key ([Get one here](https://commerce.coinbase.com/))

### Installation

```bash
# Install Node.js dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### Required Environment Variables

Edit `.env` and configure:

1. **NFC_PORT** - Your serial port (find with `ls /dev/tty.usbserial*` or `ls /dev/ttyUSB*`)
2. **COINBASE_COMMERCE_API_KEY** - From Coinbase Commerce dashboard
3. **COINBASE_WEBHOOK_SECRET** - From Coinbase Commerce webhook settings
4. **MERCHANT_NAME** - Your business name
5. **TERMINAL_ID** - Unique terminal identifier

### Running the Terminal

```bash
# Production mode
npm start

# Development mode (auto-restart on changes)
npm run dev
```

### Testing Hardware

Before running the full terminal, verify NFC hardware works:

```bash
# Test NFC reader (should detect PN532 firmware)
python3 scripts/nfc_reader.py
```

Expected output:
```
{"event": "ready", "firmware": "1.6", "port": "/dev/tty.usbserial-ABSCDY4Z", "timestamp": 1728404791}
```

## Usage

1. Start terminal: `npm run dev`
2. Enter sale amount when prompted: `$5.00`
3. Terminal displays QR code for customer
4. Customer can either:
   - Scan QR code on phone → Opens payment page
   - Tap phone on NFC reader → Terminal detects tap (UX convenience)
5. Customer completes payment via Coinbase Commerce checkout
6. Webhook confirms payment → Terminal displays success

## Architecture

**Phase 1: Push Model via Coinbase Commerce**

```
Terminal (Node.js)
    ↓
Coinbase Commerce API (charge creation)
    ↓
QR Code + NFC Tap Detection
    ↓
Customer Wallet → Coinbase Commerce Hosted Checkout
    ↓
Customer PUSHES payment to deposit address
    ↓
Webhook → Terminal confirmation
```

See `terminal-implementation.md` for detailed architecture and Phase 2 pull payment roadmap.

## Project Structure

```
terminal/
├── src/
│   ├── index.js       # Main application entry point
│   ├── nfc.js         # NFC bridge (Node.js ↔ Python IPC)
│   ├── commerce.js    # Coinbase Commerce API wrapper
│   ├── payment.js     # Charge lifecycle management
│   └── webhook.js     # Webhook server for payment confirmations
├── scripts/
│   └── nfc_reader.py  # Python NFC hardware bridge
├── config/
│   └── index.js       # Environment configuration & validation
├── package.json
├── .env.example
└── README.md
```

## Development

### NFC Reader (Python)

The NFC reader runs as a child process spawned by Node.js:

```bash
# Run standalone for testing
python3 scripts/nfc_reader.py

# Outputs JSON events via stdout:
# {"event": "ready", ...}
# {"event": "tap", "uid": "086AF124", ...}
# {"event": "error", ...}
```

### Node.js Services

The terminal application coordinates:

- **NFCBridge** (`src/nfc.js`) - Spawns Python reader, parses JSON events
- **CommerceClient** (`src/commerce.js`) - Creates charges via Coinbase API
- **PaymentManager** (`src/payment.js`) - Tracks pending charges, associates taps
- **Webhook Server** (`src/webhook.js`) - Receives payment confirmations

## Troubleshooting

### "No module named 'adafruit_pn532'"

```bash
pip3 install adafruit-circuitpython-pn532 pyserial --break-system-packages
```

### "PN532 not responding"

1. Check serial port: `ls /dev/tty.usbserial*`
2. Update `NFC_PORT` in `.env`
3. Verify wiring (TX/RX must crossover)
4. Power cycle NFC module (unplug USB, wait 5s, replug)

### "Cannot find serial port"

**macOS/Linux:**
```bash
ls /dev/tty.usbserial*  # USB-UART adapters
ls /dev/ttyUSB*         # Linux USB serial
ls /dev/ttyAMA*         # Raspberry Pi GPIO UART
```

**Raspberry Pi permissions:**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### "Webhook not receiving events"

1. Ensure webhook endpoint is accessible
2. For local testing, use ngrok:
   ```bash
   ngrok http 3000
   # Copy HTTPS URL to Coinbase Commerce webhook settings
   ```

### "Tap detected but no charge pending"

- Create charge first (enter sale amount)
- Charge expires after 3 minutes

## Next Steps

See `../terminal-implementation.md` for:

- Detailed implementation plan (Graphite-style stacks)
- Code examples for each module
- Testing checklist
- Deployment guide (Raspberry Pi)
- Phase 2 pull payment architecture

## License

MIT
