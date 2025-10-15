import coinbaseCommerce from 'coinbase-commerce-node';

const { Client, resources, Webhook } = coinbaseCommerce;
const { Charge } = resources;

/**
 * Coinbase Commerce API Client
 *
 * Handles charge creation and retrieval via Coinbase Commerce API.
 * Phase 1 uses Commerce for hosted checkout (push payment model).
 *
 * Usage:
 *   const commerce = new CommerceClient(apiKey);
 *   const charge = await commerce.createCharge({ amount: 5.00, description: 'Coffee' });
 *   console.log(charge.hostedUrl); // Customer payment page
 */
export class CommerceClient {
  constructor(apiKey) {
    if (!apiKey) {
      throw new Error('Coinbase Commerce API key is required');
    }

    Client.init(apiKey);
    this.apiKey = apiKey;
  }

  /**
   * Create a charge via Coinbase Commerce API
   *
   * @param {Object} params
   * @param {number} params.amount - Amount in USD
   * @param {string} params.currency - Currency code (default: 'USD')
   * @param {string} params.description - Purchase description
   * @param {string} params.terminalId - Terminal identifier
   * @returns {Promise<Object>} Charge object with hostedUrl, addresses, etc.
   */
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

      console.log('[Commerce] Creating charge:', {
        amount: chargeData.local_price.amount,
        currency,
        description,
      });

      const charge = await Charge.create(chargeData);

      console.log('[Commerce] Charge created:', {
        id: charge.id,
        hostedUrl: charge.hosted_url,
      });

      return {
        id: charge.id,
        hostedUrl: charge.hosted_url,
        addresses: charge.addresses,
        pricing: charge.pricing,
        expiresAt: charge.expires_at,
        timeline: charge.timeline,
      };
    } catch (error) {
      console.error('[Commerce] Charge creation failed:', error.message);
      throw new Error(`Failed to create charge: ${error.message}`);
    }
  }

  /**
   * Retrieve charge by ID
   *
   * @param {string} chargeId - Charge identifier
   * @returns {Promise<Object>} Charge object with current status
   */
  async getCharge(chargeId) {
    try {
      const charge = await Charge.retrieve(chargeId);

      const latestStatus = charge.timeline[charge.timeline.length - 1].status;

      return {
        id: charge.id,
        status: latestStatus,
        payments: charge.payments,
        timeline: charge.timeline,
        addresses: charge.addresses,
        pricing: charge.pricing,
      };
    } catch (error) {
      console.error('[Commerce] Charge retrieval failed:', error.message);
      throw new Error(`Failed to retrieve charge: ${error.message}`);
    }
  }

  /**
   * Verify webhook signature
   *
   * @param {string} rawBody - Raw request body (string)
   * @param {string} signature - x-cc-webhook-signature header
   * @param {string} webhookSecret - Webhook secret from dashboard
   * @returns {Object|null} Parsed event or null if invalid
   */
  static verifyWebhook(rawBody, signature, webhookSecret) {
    try {
      const event = Webhook.verifyEventBody(rawBody, signature, webhookSecret);
      return event;
    } catch (error) {
      console.error('[Commerce] Webhook verification failed:', error.message);
      return null;
    }
  }
}
