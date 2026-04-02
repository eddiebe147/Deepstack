import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { createClient as createSupabaseAdmin } from '@supabase/supabase-js';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-04-30.basil',
});

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;

// Use service role for webhook (no user session available)
function getAdminClient() {
  return createSupabaseAdmin(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

const PRODUCT_TO_TIER: Record<string, string> = {
  [process.env.STRIPE_PRODUCT_PRO || 'prod_Ta3YZOPq86bM2J']: 'pro',
  [process.env.STRIPE_PRODUCT_ELITE || 'prod_Ta3aXZCqBcoFnI']: 'elite',
};

async function updateSubscription(
  customerId: string,
  tier: string,
  status: string,
  subscriptionId?: string,
  endsAt?: string,
) {
  const supabase = getAdminClient();

  const updates: Record<string, unknown> = {
    subscription_tier: tier,
    subscription_status: status,
  };

  if (subscriptionId) updates.stripe_subscription_id = subscriptionId;
  if (status === 'active') updates.subscription_starts_at = new Date().toISOString();
  if (endsAt) updates.subscription_ends_at = endsAt;

  const { error } = await supabase
    .from('profiles')
    .update(updates)
    .eq('stripe_customer_id', customerId);

  if (error) {
    console.error('Failed to update subscription:', error);
    throw error;
  }

  console.log(`Subscription updated: customer=${customerId} tier=${tier} status=${status}`);
}

export async function POST(req: NextRequest) {
  const body = await req.text();
  const signature = req.headers.get('stripe-signature');

  if (!signature) {
    return NextResponse.json({ error: 'Missing signature' }, { status: 400 });
  }

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    console.error('Webhook signature verification failed:', err);
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        const customerId = session.customer as string;
        const tier = session.metadata?.tier || 'pro';
        const subscriptionId = session.subscription as string;

        await updateSubscription(customerId, tier, 'active', subscriptionId);
        break;
      }

      case 'customer.subscription.updated': {
        const sub = event.data.object as Stripe.Subscription;
        const customerId = sub.customer as string;
        const productId = sub.items.data[0]?.price.product as string;
        const tier = PRODUCT_TO_TIER[productId] || 'pro';
        const status = sub.status === 'active' ? 'active' : 'past_due';

        await updateSubscription(customerId, tier, status, sub.id);
        break;
      }

      case 'customer.subscription.deleted': {
        const sub = event.data.object as Stripe.Subscription;
        const customerId = sub.customer as string;
        const endsAt = new Date(sub.current_period_end * 1000).toISOString();

        await updateSubscription(customerId, 'free', 'canceled', sub.id, endsAt);
        break;
      }

      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = invoice.customer as string;

        await updateSubscription(customerId, 'pro', 'past_due');
        console.warn(`Payment failed for customer ${customerId}`);
        break;
      }

      default:
        // Ignore other event types
        break;
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('Webhook handler error:', error);
    return NextResponse.json({ error: 'Webhook handler failed' }, { status: 500 });
  }
}
