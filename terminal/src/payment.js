import QRCode from 'qrcode';

/**
 * Payment Manager - Handles charge lifecycle and tap association
 *
 * Tracks pending charges, associates NFC taps with charges,
 * and manages charge expiration.
 *
 * Usage:
 *   const manager = new PaymentManager(commerceClient, terminalId);
 *   const charge = await manager.createPaymentRequest(5.00, 'Coffee');
 *   await manager.associateTap('086AF124'); // When customer taps
 *   manager.completePurchase(charge.id); // After webhook confirmation
 */
export class PaymentManager {
  constructor(commerceClient, terminalId) {
    this.commerce = commerceClient;
    this.terminalId = terminalId;
    this.pendingCharges = new Map();  // chargeId → charge data
    this.tapMap = new Map();  // tapUid → chargeId
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

    // Auto-expire after 3 minutes
    setTimeout(() => {
      if (this.pendingCharges.has(charge.id)) {
        console.log(`[Payment] Charge ${charge.id} expired`);
        this.pendingCharges.delete(charge.id);
      }
    }, 180_000);

    console.log(`[Payment] Payment request created: $${amount.toFixed(2)}`);

    return charge;
  }

  /**
   * Associate a tap UID with the most recent pending charge
   *
   * @param {string} tapUid - Tap UID from NFC reader
   * @returns {Object|null} Associated charge or null if no pending charges
   */
  async associateTap(tapUid) {
    // Find most recent pending charge (not already tapped)
    const charges = Array.from(this.pendingCharges.values())
      .filter(c => !c.tapUid)
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
    const charge = this.pendingCharges.get(chargeId);

    if (charge) {
      // Clean up tap mapping
      if (charge.tapUid) {
        this.tapMap.delete(charge.tapUid);
      }

      // Remove from pending
      this.pendingCharges.delete(chargeId);

      console.log(`[Payment] Purchase completed: ${chargeId}`);
    }
  }
}
