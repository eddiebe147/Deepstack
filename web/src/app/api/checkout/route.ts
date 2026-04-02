import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { createClient } from '@/lib/supabase/server';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-04-30.basil',
});

// Use product IDs -- prices are looked up automatically
const PRODUCT_MAP: Record<string, string> = {
  pro: process.env.STRIPE_PRODUCT_PRO || 'prod_Ta3YZOPq86bM2J',
  elite: process.env.STRIPE_PRODUCT_ELITE || 'prod_Ta3aXZCqBcoFnI',
};

async function getPriceForProduct(productId: string): Promise<string> {
  const prices = await stripe.prices.list({
    product: productId,
    active: true,
    type: 'recurring',
    limit: 1,
  });
  if (!prices.data.length) {
    throw new Error(`No active recurring price found for product ${productId}`);
  }
  return prices.data[0].id;
}

export async function POST(req: NextRequest) {
  try {
    const { tier, user_id, user_email } = await req.json();

    if (!tier || !PRODUCT_MAP[tier]) {
      return NextResponse.json({ error: 'Invalid tier' }, { status: 400 });
    }

    if (!user_id || !user_email) {
      return NextResponse.json({ error: 'User not authenticated' }, { status: 401 });
    }

    const supabase = await createClient();

    // Check if user already has a Stripe customer ID
    const { data: profile } = await supabase
      .from('profiles')
      .select('stripe_customer_id')
      .eq('id', user_id)
      .single();

    let customerId = profile?.stripe_customer_id;

    // Create Stripe customer if none exists
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user_email,
        metadata: { supabase_user_id: user_id },
      });
      customerId = customer.id;

      await supabase
        .from('profiles')
        .update({ stripe_customer_id: customerId })
        .eq('id', user_id);
    }

    // Look up price from product ID
    const priceId = await getPriceForProduct(PRODUCT_MAP[tier]);

    // Create checkout session
    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${req.nextUrl.origin}/app?upgraded=${tier}`,
      cancel_url: `${req.nextUrl.origin}/pricing`,
      metadata: {
        supabase_user_id: user_id,
        tier,
      },
    });

    return NextResponse.json({ url: session.url });
  } catch (error) {
    console.error('Checkout error:', error);
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    );
  }
}
