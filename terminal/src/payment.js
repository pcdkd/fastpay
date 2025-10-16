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
  constructor(commerceClient, terminalId, logger = console) {
    this.commerce = commerceClient;
    this.terminalId = terminalId;
    this.logger = logger;
    this.pendingCharges = new Map();  // chargeId → charge data
    this.tapMap = new Map();  // tapUid → chargeId

    // Start periodic expiration check
    this.expirationInterval = setInterval(() => this._cleanupExpiredCharges(), EXPIRATION_CHECK_INTERVAL_MS);
    this.expirationInterval.unref();  // Don't keep process alive if nothing else is pending
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

    // Clean up tap mapping only if it still points to this charge (prevents race condition)
    if (charge.tapUid && this.tapMap.get(charge.tapUid) === chargeId) {
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
          this.logger.log(`[Payment] Charge ${chargeId} expired`);
          this._removeCharge(chargeId);
        }
      }
    } catch (error) {
      this.logger.error('[Payment] Error during charge cleanup:', error);
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
    this.logger.log('[Payment] Payment manager shut down');
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

    this.logger.log(`[Payment] Payment request created: $${amount.toFixed(2)}`);

    return charge;
  }

  /**
   * Associate a tap UID with the most recent pending charge
   *
   * @param {string} tapUid - Tap UID from NFC reader
   * @returns {Object|null} Associated charge or null if no pending charges
   */
  associateTap(tapUid) {
    // Find the most recent untapped charge. Since Maps preserve insertion order, we can
    // iterate backwards to find the most recent charge first and exit early.
    const now = Date.now();
    const charges = Array.from(this.pendingCharges.values());
    let charge = null;
    for (let i = charges.length - 1; i >= 0; i--) {
      const c = charges[i];
      // Find the first (most recent) charge that is not tapped and not expired
      if (!c.tapUid && (now - c.createdAt < CHARGE_EXPIRATION_MS)) {
        charge = c;
        break;  // Early exit - found the most recent valid charge
      }
    }

    if (!charge) {
      this.logger.warn('[Payment] Tap received but no pending charges');
      return null;
    }

    // Associate tap with charge
    charge.tapUid = tapUid;
    this.tapMap.set(tapUid, charge.id);

    this.logger.log(`[Payment] Tap ${tapUid} associated with charge ${charge.id}`);

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
      this.logger.error('[Payment] QR generation failed:', error.message);
      return null;
    }
  }

  /**
   * Get pending charge by ID
   *
   * @param {string} chargeId - Charge identifier
   * @returns {Object|undefined} Charge data (shallow copy) or undefined
   */
  getPendingCharge(chargeId) {
    const charge = this.pendingCharges.get(chargeId);
    return charge ? { ...charge } : undefined;
  }

  /**
   * Get all pending charges
   *
   * @returns {Array<Object>} Array of pending charges (shallow copies to prevent mutation)
   */
  getAllPendingCharges() {
    // Return shallow copies to prevent external mutation of internal state
    return Array.from(this.pendingCharges.values(), c => ({ ...c }));
  }

  /**
   * Complete purchase (remove from pending)
   *
   * @param {string} chargeId - Charge identifier
   */
  completePurchase(chargeId) {
    if (this.pendingCharges.has(chargeId)) {
      this._removeCharge(chargeId);
      this.logger.log(`[Payment] Purchase completed: ${chargeId}`);
    }
  }
}
