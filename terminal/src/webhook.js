import express from 'express';
import { CommerceClient } from './commerce.js';

/**
 * Create Webhook Server for Coinbase Commerce payment confirmations
 *
 * @param {Object} config - Configuration object
 * @param {PaymentManager} paymentManager - Payment manager instance
 * @returns {express.Application} Express app instance
 */
export function createWebhookServer(config, paymentManager) {
  const app = express();

  // Raw body needed for signature verification
  app.use(express.json({
    verify: (req, res, buf) => {
      req.rawBody = buf.toString();
    },
  }));

  /**
   * Health check endpoint
   */
  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      terminal: config.terminalId,
      merchant: config.merchantName,
      pendingCharges: paymentManager.getAllPendingCharges().length,
    });
  });

  /**
   * Coinbase Commerce webhook endpoint
   *
   * Handles payment confirmation events from Coinbase Commerce.
   * Verifies webhook signature and processes charge:confirmed events.
   */
  app.post('/webhooks/coinbase', (req, res) => {
    const signature = req.headers['x-cc-webhook-signature'];

    if (!signature) {
      console.error('[Webhook] Missing signature header');
      return res.sendStatus(400);
    }

    try {
      // Verify webhook signature
      const event = CommerceClient.verifyWebhook(
        req.rawBody,
        signature,
        config.webhookSecret
      );

      if (!event) {
        console.error('[Webhook] Invalid signature');
        return res.sendStatus(400);
      }

      console.log(`[Webhook] Received: ${event.type}`);

      // Handle different event types
      switch (event.type) {
        case 'charge:created':
          console.log(`[Webhook] Charge created: ${event.data.id}`);
          break;

        case 'charge:confirmed':
          handleChargeConfirmed(event, app, paymentManager);
          break;

        case 'charge:failed':
          console.log(`[Webhook] Charge failed: ${event.data.id}`);
          break;

        case 'charge:delayed':
          console.log(`[Webhook] Charge delayed: ${event.data.id}`);
          break;

        case 'charge:pending':
          console.log(`[Webhook] Charge pending: ${event.data.id}`);
          break;

        case 'charge:resolved':
          console.log(`[Webhook] Charge resolved: ${event.data.id}`);
          break;

        default:
          console.log(`[Webhook] Unhandled event type: ${event.type}`);
      }

      res.sendStatus(200);
    } catch (error) {
      console.error('[Webhook] Error processing event:', error.message);
      res.sendStatus(500);
    }
  });

  return app;
}

/**
 * Handle charge:confirmed event
 *
 * @param {Object} event - Webhook event
 * @param {express.Application} app - Express app (for emitting events)
 * @param {PaymentManager} paymentManager - Payment manager instance
 */
function handleChargeConfirmed(event, app, paymentManager) {
  const charge = event.data;

  console.log(`[Webhook] ✅ Payment confirmed for charge: ${charge.id}`);

  // Extract payment details
  const paymentDetails = {
    chargeId: charge.id,
    amount: charge.pricing.local.amount,
    currency: charge.pricing.local.currency,
    payments: charge.payments,
    confirmedAt: new Date().toISOString(),
  };

  // Emit event for main app to consume
  app.emit('payment:confirmed', paymentDetails);

  // Clean up pending charge
  paymentManager.completePurchase(charge.id);
}
