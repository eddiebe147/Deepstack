'use client';

import { Check, Sparkles, Shield, Zap, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useUser } from '@/hooks/useUser';

const tiers = [
    {
        name: 'Free',
        price: '$0',
        period: 'forever',
        description: 'Perfect for getting started with paper trading',
        icon: Zap,
        color: 'from-gray-500 to-gray-600',
        features: [
            'Paper trading with $100k virtual cash',
            'Basic charts & market data',
            '100 AI credits/month',
            '10 journal entries',
            'Community support',
        ],
        cta: 'Start Free',
        tier: 'free' as const,
    },
    {
        name: 'Pro',
        price: '$19',
        period: 'per month',
        description: 'For serious traders who want more AI power',
        icon: Sparkles,
        color: 'from-amber-500 to-orange-600',
        popular: true,
        features: [
            'Everything in Free',
            '1,000 AI credits/month',
            'Unlimited journal entries',
            'Thesis tracking system',
            'Options analysis & Greeks',
            'Priority support',
        ],
        cta: 'Go Pro',
        tier: 'pro' as const,
    },
    {
        name: 'Elite',
        price: '$49',
        period: 'per month',
        description: 'Maximum power with the Emotional Firewall',
        icon: Shield,
        color: 'from-emerald-500 to-green-600',
        features: [
            'Everything in Pro',
            '5,000 AI credits/month',
            '🔥 Emotional Firewall',
            '🧠 Psychology Analytics',
            'Revenge trade detection',
            'Overtrading prevention',
            'VIP support',
        ],
        cta: 'Get Elite',
        tier: 'elite' as const,
    },
];

export default function PricingPage() {
    const { user } = useUser();
    const [loading, setLoading] = useState<string | null>(null);

    const handleUpgrade = async (tier: 'free' | 'pro' | 'elite') => {
        if (tier === 'free') {
            window.location.href = '/app';
            return;
        }

        if (!user) {
            window.location.href = '/login?redirect=/pricing';
            return;
        }

        setLoading(tier);

        try {
            // Call backend to create checkout session
            const response = await fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tier,
                    user_id: user.id,
                    user_email: user.email,
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to create checkout session');
            }

            const { url } = await response.json();
            window.location.href = url;
        } catch (error) {
            console.error('Error creating checkout session:', error);
            alert('Failed to start checkout. Please try again.');
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-b from-background via-background to-background/50 py-20 px-4">
            {/* Back Button */}
            <div className="max-w-7xl mx-auto mb-8">
                <Button variant="ghost" asChild>
                    <Link href="/app">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Back to App
                    </Link>
                </Button>
            </div>

            {/* Hero Section */}
            <div className="max-w-4xl mx-auto text-center mb-16">
                <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-amber-400 via-orange-500 to-emerald-500 bg-clip-text text-transparent">
                    Choose Your Path to Better Trading
                </h1>
                <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                    Unlike other platforms that profit when you overtrade, we&apos;re traders like you.
                    Our mission: <span className="text-amber-400 font-semibold">empower retail traders</span> on their journey to financial freedom.
                </p>
            </div>

            {/* Pricing Cards */}
            <div className="max-w-7xl mx-auto grid md:grid-cols-3 gap-8 mb-16">
                {tiers.map((tier) => {
                    const Icon = tier.icon;

                    return (
                        <div
                            key={tier.name}
                            className={`relative rounded-2xl border ${tier.popular
                                    ? 'border-amber-500 shadow-2xl shadow-amber-500/20 scale-105'
                                    : 'border-border'
                                } bg-card p-8 flex flex-col`}
                        >
                            {tier.popular && (
                                <div className="absolute -top-4 left-0 right-0 flex justify-center">
                                    <span className="bg-gradient-to-r from-amber-500 to-orange-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                                        Most Popular
                                    </span>
                                </div>
                            )}

                            <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${tier.color} flex items-center justify-center mb-4`}>
                                <Icon className="w-6 h-6 text-white" />
                            </div>

                            <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                            <p className="text-muted-foreground text-sm mb-4">{tier.description}</p>

                            <div className="mb-6">
                                <span className="text-4xl font-bold">{tier.price}</span>
                                <span className="text-muted-foreground ml-2">{tier.period}</span>
                            </div>

                            <ul className="space-y-3 mb-8 flex-grow">
                                {tier.features.map((feature) => (
                                    <li key={feature} className="flex items-start gap-2">
                                        <Check className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                                        <span className="text-sm">{feature}</span>
                                    </li>
                                ))}
                            </ul>

                            <Button
                                onClick={() => handleUpgrade(tier.tier)}
                                disabled={loading !== null}
                                className={tier.popular ? `bg-gradient-to-r ${tier.color} hover:opacity-90` : ''}
                                size="lg"
                            >
                                {loading === tier.tier ? 'Loading...' : tier.cta}
                            </Button>
                        </div>
                    );
                })}
            </div>

            {/* Emotional Firewall Callout */}
            <div className="max-w-4xl mx-auto bg-gradient-to-br from-amber-500/10 via-orange-500/10 to-emerald-500/10 border border-amber-500/30 rounded-2xl p-8">
                <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                    <Shield className="w-6 h-6 text-amber-400" />
                    Why the Emotional Firewall Matters
                </h2>
                <p className="text-muted-foreground mb-4">
                    82% of retail traders lose money. Most losses aren&apos;t from bad analysis—they&apos;re from emotional decisions:
                    revenge trading, overtrading, and FOMO.
                </p>
                <p className="text-muted-foreground">
                    The Emotional Firewall detects these patterns and <span className="text-emerald-400 font-semibold">stops you before you blow up your account</span>.
                    It&apos;s like having an experienced trading mentor watching over your shoulder 24/7.
                </p>
            </div>

            {/* AI Model Pricing */}
            <div className="max-w-4xl mx-auto mt-8 bg-card border border-border rounded-2xl p-8">
                <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                    <Sparkles className="w-6 h-6 text-primary" />
                    Flexible AI Model Pricing
                </h2>
                <p className="text-muted-foreground mb-6">
                    Choose the right model for each task. Budget-friendly options for quick questions, premium models for deep analysis.
                </p>
                <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                        <h3 className="font-semibold text-emerald-400">Budget-Friendly</h3>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between"><span>Haiku 4.5</span><span className="text-emerald-400 font-mono">4c</span></div>
                            <div className="flex justify-between"><span>Perplexity Search</span><span className="text-emerald-400 font-mono">6c</span></div>
                            <div className="flex justify-between"><span>DeepSeek R1</span><span className="text-emerald-400 font-mono">7c</span></div>
                        </div>
                    </div>
                    <div className="space-y-3">
                        <h3 className="font-semibold text-amber-400">Premium Power</h3>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between"><span>Grok</span><span className="font-mono">12c</span></div>
                            <div className="flex justify-between"><span>Sonnet 4.5</span><span className="font-mono">15c</span></div>
                            <div className="flex justify-between"><span>Opus 4.5</span><span className="text-amber-400 font-mono">45c</span></div>
                        </div>
                    </div>
                </div>
                <p className="text-xs text-muted-foreground mt-4 pt-4 border-t border-border">
                    Extended Thinking mode adds 50% to credit cost for deeper reasoning.
                </p>
            </div>

            {/* Trader-Focused Messaging */}
            <div className="max-w-4xl mx-auto mt-12 text-center">
                <p className="text-lg text-muted-foreground">
                    We&apos;re not a broker making money on your trades. We&apos;re <span className="text-amber-400 font-semibold">traders building tools for traders</span>.
                    Use this platform to empower you on your journey to financial freedom.
                </p>
            </div>
        </div>
    );
}
