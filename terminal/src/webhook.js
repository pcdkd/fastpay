import express from 'express';
import { EventEmitter } from 'events';
import { CommerceClient } from './commerce.js';

// Coinbase Commerce event types (prevents typos)
const EVENT_TYPES = {
  CHARGE_CREATED: 'charge:created',
  CHARGE_CONFIRMED: 'charge:confirmed',
  CHARGE_FAILED: 'charge:failed',
  CHARGE_DELAYED: 'charge:delayed',
  CHARGE_PENDING: 'charge:pending',
  CHARGE_RESOLVED: 'charge:resolved',
};

/**
 * Create Webhook Server for Coinbase Commerce payment confirmations
 *
 * @param {Object} config - Configuration object
 * @param {PaymentManager} paymentManager - Payment manager instance
 * @returns {Object} { app: Express app, events: EventEmitter }
 */
export function createWebhookServer(config, paymentManager) {
  const app = express();
  const events = new EventEmitter();

  // Raw body needed for signature verification (with size limit to prevent DoS)
  app.use(express.json({
    limit: '10kb',  // Prevent large payload attacks (Coinbase Commerce webhooks are <10kb)
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
        case EVENT_TYPES.CHARGE_CREATED:
          console.log(`[Webhook] Charge created: ${event.data.id}`);
          break;

        case EVENT_TYPES.CHARGE_CONFIRMED:
          handleChargeConfirmed(event, events, paymentManager);
          break;

        case EVENT_TYPES.CHARGE_FAILED:
          console.log(`[Webhook] Charge failed: ${event.data.id}`);
          break;

        case EVENT_TYPES.CHARGE_DELAYED:
          console.log(`[Webhook] Charge delayed: ${event.data.id}`);
          break;

        case EVENT_TYPES.CHARGE_PENDING:
          console.log(`[Webhook] Charge pending: ${event.data.id}`);
          break;

        case EVENT_TYPES.CHARGE_RESOLVED:
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

  return { app, events };
}

/**
 * Handle charge:confirmed event
 *
 * @param {Object} event - Webhook event
 * @param {EventEmitter} events - Event emitter for application events
 * @param {PaymentManager} paymentManager - Payment manager instance
 */
function handleChargeConfirmed(event, events, paymentManager) {
  const charge = event.data;

  console.log(`[Webhook] ✅ Payment confirmed for charge: ${charge.id}`);

  // Find the confirmation time from the charge timeline
  const confirmedTimelineEntry = Array.isArray(charge.timeline)
    ? charge.timeline.find(entry => entry.status === 'CONFIRMED')
    : null;
  const confirmedAt = confirmedTimelineEntry ? confirmedTimelineEntry.time : null;

  // Extract payment details
  const paymentDetails = {
    chargeId: charge.id,
    amount: charge.pricing.local.amount,
    currency: charge.pricing.local.currency,
    payments: charge.payments,
    confirmedAt,  // Use actual confirmation time from timeline
  };

  // Emit event for main app to consume
  events.emit('payment:confirmed', paymentDetails);

  // Clean up pending charge with error handling
  try {
    paymentManager.completePurchase(charge.id);
  } catch (error) {
    console.error(`[Webhook] Error completing purchase for charge ${charge.id}:`, error.message);
    // Event was already emitted, so log error but don't fail webhook
  }
}
