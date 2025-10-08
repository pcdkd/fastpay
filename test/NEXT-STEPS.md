# FastPay Development - Next Steps

## ✅ Setup Complete!

Your Mac is now ready for FastPay desktop development:
- ✅ Hardware working (PN532 + FT232)
- ✅ Adafruit library tested
- ✅ Serial port configured
- ✅ All tests passing

---

## 🚀 Ready to Code

### What You Can Do Now

**1. Start Building FastPay Terminal Code**

Create the monorepo structure from the project doc:
```bash
cd /Users/danieldewar/Documents/dev/fastpay

# Create directory structure
mkdir -p packages/types packages/utils
mkdir -p terminal/src terminal/scripts
mkdir -p customer-app/src
mkdir -p docs

# Copy working NFC test as starting point
cp test/test-adafruit-pn532.py terminal/scripts/nfc_bridge.py
```

**2. Implement NFC Bridge (Python)**

Edit `terminal/scripts/nfc_bridge.py` to:
- Accept payment requests via stdin (from Node.js)
- Encode as NDEF messages
- Write to card emulation mode
- Wait for customer phone tap

**3. Implement Terminal Software (Node.js)**

Create `terminal/src/` modules:
- `wallet.js` - EIP-712 signing
- `payment.js` - Payment request creation
- `nfc.js` - Spawn Python bridge, send payloads
- `monitor.js` - Watch Base L2 for transactions
- `index.js` - Main terminal loop

**4. Test End-to-End Flow**

- Create payment request
- Write to NFC
- Read with phone (test app needed)
- Parse signature
- Generate MetaMask link

---

## 📝 Configuration Needed

### Environment Variables (`terminal/.env`)

Create this file:
```bash
# Merchant wallet
MERCHANT_PRIVATE_KEY=0xYOUR_TEST_KEY_HERE
MERCHANT_NAME="Test Merchant"
TERMINAL_ID=terminal_001

# Network
BASE_RPC_URL=https://sepolia.base.org  # Start with testnet
CHAIN_ID=84532  # Base Sepolia testnet
USDC_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e  # USDC on Base Sepolia

# NFC (YOUR WORKING CONFIG)
NFC_PORT=/dev/tty.usbserial-ABSCDY4Z
NFC_BAUD_RATE=115200

# Payment settings
PAYMENT_MODE=direct  # Start with simple transfers
PAYMENT_EXPIRY_SECONDS=180
```

### Dependencies to Install

```bash
# Node.js packages (once package.json created)
npm install ethers@^6 dotenv

# Python already has:
# - pyserial
# - adafruit-circuitpython-pn532
```

---

## 🧪 Testing Strategy

### Phase 1: NFC Communication (This Week)

**Test 1: Write Dummy Data**
- Python bridge writes "Hello World" NDEF message
- Use any NFC reader app on phone to verify

**Test 2: Write JSON Payload**
- Python bridge writes JSON payment request
- Phone reads and displays JSON

**Test 3: Write Signed Payment Request**
- Node.js creates EIP-712 signed request
- Python encodes and writes to NFC
- Phone reads and verifies signature

### Phase 2: Blockchain Integration (Next Week)

**Test 4: Monitor Base Testnet**
- Node.js monitors for test USDC transfers
- Use testnet faucets for free test tokens
- Verify event detection works

**Test 5: End-to-End Flow**
- Create payment request
- Write to NFC
- Read with test app
- Sign transaction in MetaMask
- Detect payment on blockchain
- Display confirmation

---

## 💡 Development Tips

### Use Desktop Development First

Keep using your Mac + FT232 setup:
- Faster iteration than Raspberry Pi
- Better debugging tools
- Same code will work on Pi later
- Just change `NFC_PORT` in `.env`

### Start Simple

Don't implement everything at once:
1. ✅ NFC hardware working
2. → Write static NDEF message
3. → Write dynamic JSON
4. → Add EIP-712 signing
5. → Add blockchain monitoring
6. → Test full flow

### Leverage Adafruit Library

Don't rewrite PN532 protocol:
- Use `PN532_UART` for initialization
- Use card emulation methods
- Let library handle protocol details
- Focus on FastPay business logic

---

## 🎯 Week 1 Goal

**Milestone:** Write a signed payment request to NFC and read it with a phone

**Deliverables:**
- [ ] Node.js creates EIP-712 signed payment request
- [ ] Python NFC bridge receives request via stdin
- [ ] Python encodes as NDEF message
- [ ] Python writes to card emulation mode
- [ ] Test phone reads NFC successfully
- [ ] Test app displays payment details

**What You Need:**
- ✅ Hardware (done!)
- ✅ Libraries (done!)
- → Test phone with NFC (Android preferred)
- → Simple NFC reader app (Google Play Store)
- → Start coding!

---

## 📚 Resources

### Documentation
- FastPay Project Doc: `FastPay-Phase1-ProjectDoc.md`
- Setup Success: `test/SETUP-SUCCESS.md`
- Debug History: `test/DEBUG-REPORT.md`
- CLAUDE.md: Architecture guidance for AI

### Working Code
- `test/test-adafruit-pn532.py` - Your working NFC test
- `test/test-pn532-working-final.py` - Full test with SAM config

### References
- Adafruit PN532: https://learn.adafruit.com/adafruit-pn532-rfid-nfc
- NDEF Format: https://learn.adafruit.com/adafruit-pn532-rfid-nfc/ndef
- EIP-712: https://eips.ethereum.org/EIPS/eip-712
- Base Network: https://docs.base.org/

---

## ❓ If You Get Stuck

### Hardware Issues
1. Check `test/SETUP-SUCCESS.md` for working config
2. Run `python3 test/test-adafruit-pn532.py` to verify
3. Power cycle (unplug/replug USB) if needed

### Software Issues
1. Check `.env` file has correct settings
2. Verify `NFC_PORT=/dev/tty.usbserial-ABSCDY4Z`
3. Ensure DTR/RTS are set to False in code

### Protocol Issues
1. Reference Adafruit examples
2. Check FastPay project doc for EIP-712 schemas
3. Test with simple NDEF messages first

---

**You're ready to build! 🚀**

Need help implementing the NFC bridge or terminal code? Just ask!
