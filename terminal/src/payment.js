import QRCode from 'qrcode';

// Constants
const CHARGE_EXPIRATION_MS = 180_000;  // 3 minutes
const EXPIRATION_CHECK_INTERVAL_MS = 30_000;  // Check every 30 seconds

/**
 * Payment Manager - Handles charge lifecycle and tap association
 *
 * Tracks pending charges, associates NFC taps with charges,
 * and manages charge expiration.
 *
 * Usage:
 *   const manager = new PaymentManager(commerceClient, terminalId);
 *   const charge = await manager.createPaymentRequest(5.00, 'Coffee');
 *   manager.associateTap('086AF124'); // When customer taps
 *   manager.completePurchase(charge.id); // After webhook confirmation
 *   manager.shutdown(); // Clean up resources
 */
export class PaymentManager {
  constructor(commerceClient, terminalId) {
    this.commerce = commerceClient;
    this.terminalId = terminalId;
    this.pendingCharges = new Map();  // chargeId → charge data
    this.tapMap = new Map();  // tapUid → chargeId

    // Start periodic expiration check
    this.expirationInterval = setInterval(() => this._cleanupExpiredCharges(), EXPIRATION_CHECK_INTERVAL_MS);
  }

  /**
   * Remove a charge and its tap mapping (DRY helper)
   * @private
   */
  _removeCharge(chargeId) {
    const charge = this.pendingCharges.get(chargeId);
    if (!charge) {
      return;
    }

    // Clean up tap mapping to prevent memory leak
    if (charge.tapUid) {
      this.tapMap.delete(charge.tapUid);
    }

    this.pendingCharges.delete(chargeId);
  }

  /**
   * Clean up expired charges (removes from both pendingCharges and tapMap)
   * @private
   */
  _cleanupExpiredCharges() {
    const now = Date.now();
    try {
      for (const [chargeId, charge] of this.pendingCharges.entries()) {
        if (now - charge.createdAt >= CHARGE_EXPIRATION_MS) {
          console.log(`[Payment] Charge ${chargeId} expired`);
          this._removeCharge(chargeId);
        }
      }
    } catch (error) {
      console.error('[Payment] Error during charge cleanup:', error);
    }
  }

  /**
   * Shutdown payment manager and clean up resources
   */
  shutdown() {
    if (this.expirationInterval) {
      clearInterval(this.expirationInterval);
      this.expirationInterval = null;
    }
    console.log('[Payment] Payment manager shut down');
  }

  /**
   * Create a payment request (Coinbase Commerce charge)
   *
   * @param {number} amount - Amount in USD
   * @param {string} description - Purchase description
   * @returns {Promise<Object>} Charge object
   */
  async createPaymentRequest(amount, description) {
    const charge = await this.commerce.createCharge({
      amount,
      description,
      terminalId: this.terminalId,
    });

    // Track pending charge
    this.pendingCharges.set(charge.id, {
      ...charge,
      amount,
      description,
      createdAt: Date.now(),
      tapUid: null,
    });

    console.log(`[Payment] Payment request created: $${amount.toFixed(2)}`);

    return charge;
  }

  /**
   * Associate a tap UID with the most recent pending charge
   *
   * @param {string} tapUid - Tap UID from NFC reader
   * @returns {Object|null} Associated charge or null if no pending charges
   */
  associateTap(tapUid) {
    // Find most recent untapped charge using direct iteration (avoids array allocation)
    let charge = null;
    for (const c of this.pendingCharges.values()) {
      if (!c.tapUid && (!charge || c.createdAt > charge.createdAt)) {
        charge = c;
      }
    }

    if (!charge) {
      console.warn('[Payment] Tap received but no pending charges');
      return null;
    }

    // Associate tap with charge
    charge.tapUid = tapUid;
    this.tapMap.set(tapUid, charge.id);

    console.log(`[Payment] Tap ${tapUid} associated with charge ${charge.id}`);

    return charge;
  }

  /**
   * Generate QR code for hosted URL
   *
   * @param {string} hostedUrl - Coinbase Commerce hosted checkout URL
   * @returns {Promise<string|null>} QR code string (terminal format) or null if error
   */
  async generateQR(hostedUrl) {
    try {
      const qr = await QRCode.toString(hostedUrl, {
        type: 'terminal',
        small: true,
        errorCorrectionLevel: 'M',
      });
      return qr;
    } catch (error) {
      console.error('[Payment] QR generation failed:', error.message);
      return null;
    }
  }

  /**
   * Get pending charge by ID
   *
   * @param {string} chargeId - Charge identifier
   * @returns {Object|undefined} Charge data or undefined
   */
  getPendingCharge(chargeId) {
    return this.pendingCharges.get(chargeId);
  }

  /**
   * Get all pending charges
   *
   * @returns {Array<Object>} Array of pending charges
   */
  getAllPendingCharges() {
    return Array.from(this.pendingCharges.values());
  }

  /**
   * Complete purchase (remove from pending)
   *
   * @param {string} chargeId - Charge identifier
   */
  completePurchase(chargeId) {
    if (this.pendingCharges.has(chargeId)) {
      this._removeCharge(chargeId);
      console.log(`[Payment] Purchase completed: ${chargeId}`);
    }
  }
}
