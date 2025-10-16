import axios from 'axios';
import crypto from 'crypto';  // NOTE: Uses Node.js built-in crypto. Remove 'crypto' from package.json if present.

const COINBASE_COMMERCE_API_URL = 'https://api.commerce.coinbase.com';

/**
 * Coinbase Commerce API Client
 *
 * Handles charge creation and retrieval via Coinbase Commerce REST API.
 * Phase 1 uses Commerce for hosted checkout (push payment model).
 *
 * API Documentation: https://docs.cdp.coinbase.com/commerce-onchain/docs/api
 *
 * Usage:
 *   const commerce = new CommerceClient(apiKey);
 *   const charge = await commerce.createCharge({ amount: 5.00, description: 'Coffee' });
 *   console.log(charge.hostedUrl); // Customer payment page
 */
export class CommerceClient {
  constructor(apiKey, logger = console) {
    if (!apiKey) {
      throw new Error('Coinbase Commerce API key is required');
    }

    this.logger = logger;
    this.client = axios.create({
      baseURL: COINBASE_COMMERCE_API_URL,
      headers: {
        'X-CC-Api-Key': apiKey,
        'X-CC-Version': '2018-03-22',
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Transform API charge response to camelCase (DRY helper)
   * @private
   */
  _transformCharge(charge, includeStatus = false) {
    const transformed = {
      id: charge.id,
      hostedUrl: charge.hosted_url,
      addresses: charge.addresses,
      pricing: charge.pricing,
      expiresAt: charge.expires_at,
    };

    if (includeStatus) {
      transformed.timeline = charge.timeline;
      // Defensive: handle empty or missing timeline
      transformed.status = charge.timeline?.[charge.timeline.length - 1]?.status;
      transformed.payments = charge.payments;
    }

    return transformed;
  }

  /**
   * Create a charge via Coinbase Commerce API
   *
   * API: POST /charges
   * Docs: https://docs.cdp.coinbase.com/commerce-onchain/docs/api-charges#create-a-charge
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
          tap_uid: null,  // Will be updated via separate API call when customer taps
          created_at: new Date().toISOString(),
        },
      };

      this.logger.log('[Commerce] Creating charge:', {
        amount: chargeData.local_price.amount,
        currency,
        description,
      });

      const response = await this.client.post('/charges', chargeData);
      const charge = response.data.data;

      this.logger.log('[Commerce] Charge created:', {
        id: charge.id,
        hostedUrl: charge.hosted_url,
      });

      return this._transformCharge(charge);
    } catch (error) {
      const errorMessage = error.response?.data?.error?.message || error.message;
      this.logger.error('[Commerce] Charge creation failed:', errorMessage);
      throw new Error(`Failed to create charge: ${errorMessage}`);
    }
  }

  /**
   * Retrieve charge by ID
   *
   * API: GET /charges/:id
   * Docs: https://docs.cdp.coinbase.com/commerce-onchain/docs/api-charges#show-a-charge
   *
   * @param {string} chargeId - Charge identifier
   * @returns {Promise<Object>} Charge object with current status
   */
  async getCharge(chargeId) {
    try {
      const response = await this.client.get(`/charges/${chargeId}`);
      const charge = response.data.data;

      return this._transformCharge(charge, true);
    } catch (error) {
      const errorMessage = error.response?.data?.error?.message || error.message;
      this.logger.error('[Commerce] Charge retrieval failed:', errorMessage);
      throw new Error(`Failed to retrieve charge: ${errorMessage}`);
    }
  }

  /**
   * Verify webhook signature
   *
   * Coinbase Commerce signs webhooks with HMAC-SHA256.
   * Docs: https://docs.cdp.coinbase.com/commerce-onchain/docs/api-webhooks#securing-webhooks
   *
   * @param {string} rawBody - Raw request body (string)
   * @param {string} signature - x-cc-webhook-signature header
   * @param {string} webhookSecret - Webhook secret from dashboard
   * @param {Object} logger - Logger instance (default: console)
   * @returns {Object|null} Parsed event or null if invalid
   */
  static verifyWebhook(rawBody, signature, webhookSecret, logger = console) {
    // Input validation
    if (!rawBody || !signature || !webhookSecret) {
      logger.error('[Commerce] Webhook verification failed: Missing rawBody, signature, or webhookSecret');
      return null;
    }

    try {
      // Compute HMAC-SHA256 signature
      const hmac = crypto.createHmac('sha256', webhookSecret);
      hmac.update(rawBody);
      const computedSignature = hmac.digest('hex');

      // Constant-time comparison to prevent timing attacks
      // Handle length mismatch to prevent timingSafeEqual crash
      const sigBuf = Buffer.from(signature);
      const compBuf = Buffer.from(computedSignature);
      if (sigBuf.length !== compBuf.length) {
        logger.error('[Commerce] Webhook signature length mismatch');
        return null;
      }
      if (!crypto.timingSafeEqual(sigBuf, compBuf)) {
        logger.error('[Commerce] Webhook signature mismatch');
        return null;
      }

      // Parse and return event - separate error handling for JSON parsing
      try {
        return JSON.parse(rawBody);
      } catch (parseError) {
        logger.error('[Commerce] Webhook payload parsing failed after successful signature verification:', parseError.message);
        return null;
      }
    } catch (error) {
      logger.error('[Commerce] Webhook verification failed:', error.message);
      return null;
    }
  }
}
