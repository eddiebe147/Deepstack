'use client';

import Link from 'next/link';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef, useEffect } from 'react';
import { useState, useEffect as useEffectReact } from 'react';
import {
  MessageSquare,
  TrendingUp,
  Shield,
  BookOpen,
  Lightbulb,
  ChevronRight,
  Zap,
  BarChart3,
  Brain,
  Sparkles,
  AlertTriangle,
  Clock,
  Flame,
  Ban,
  TrendingDown,
  Activity,
  Calculator,
  Newspaper,
  Eye,
  Lock,
  Quote,
  Target,
  Search,
  XCircle,
  CheckCircle,
  Scale,
  ArrowRight,
  Play,
  RotateCcw,
} from 'lucide-react';

import { IntelligentBackground } from '@/components/landing/IntelligentBackground';
import { FrostedOverlay } from '@/components/landing/FrostedOverlay';
import { TypewriterChatDemo } from '@/components/landing/TypewriterChatDemo';
import {
  ScrollProgressBar,
  StickySection,
  ScrollReveal,
  ParallaxSection,
} from '@/components/landing/StickySection';

// The Three Pillars
const THREE_PILLARS = [
  {
    icon: <BarChart3 className="w-8 h-8" />,
    title: 'Prediction Market Intelligence',
    subtitle: 'Kalshi + Polymarket',
    description: 'Live odds, cross-platform comparison, and AI-powered probability analysis. See what the market thinks, then decide if it is wrong.',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10',
    borderColor: 'border-cyan-500/30',
  },
  {
    icon: <Shield className="w-8 h-8" />,
    title: 'Emotional Discipline Engine',
    subtitle: 'Your Behavioral Circuit Breaker',
    description: '92% of prediction market traders lose money. The pattern is emotional, not analytical. We detect revenge trading, overtrading, and weak conviction before they cost you.',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
  },
  {
    icon: <Lightbulb className="w-8 h-8" />,
    title: 'Thesis to Settlement',
    subtitle: 'Structured Conviction',
    description: 'Develop hypotheses, track them against live markets, and validate your thinking with real probabilities. Good theses survive the overnight test.',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
];

// Process Integrity Dimensions
const INTEGRITY_DIMENSIONS = [
  {
    icon: <BookOpen className="w-5 h-5" />,
    name: 'Research Quality',
    description: 'Did you do the work? Tool usage, devil\'s advocate, assumptions documented.',
    score: 72,
    color: 'text-green-400',
    bgColor: 'bg-green-500/15',
  },
  {
    icon: <Clock className="w-5 h-5" />,
    name: 'Time in Thesis',
    description: 'How long have you been developing this idea? Good ideas survive overnight.',
    score: 'Nascent',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/15',
  },
  {
    icon: <Target className="w-5 h-5" />,
    name: 'Conviction Integrity',
    description: 'How certain are you? Are you hedging or committed?',
    score: 85,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/15',
  },
];

// What DeepStack is NOT vs IS
const NOT_IS_COMPARISON = {
  not: [
    { icon: <XCircle className="w-5 h-5" />, text: 'A signal service telling you what to bet' },
    { icon: <XCircle className="w-5 h-5" />, text: 'A bot that trades for you' },
    { icon: <XCircle className="w-5 h-5" />, text: 'A news aggregator with vibes-based sentiment' },
    { icon: <XCircle className="w-5 h-5" />, text: 'A get-rich-quick prediction engine' },
  ],
  is: [
    { icon: <CheckCircle className="w-5 h-5" />, text: 'A research terminal for prediction market traders' },
    { icon: <CheckCircle className="w-5 h-5" />, text: 'An emotional firewall that catches your worst instincts' },
    { icon: <CheckCircle className="w-5 h-5" />, text: 'A thesis engine that tracks conviction over time' },
    { icon: <CheckCircle className="w-5 h-5" />, text: 'Cross-platform intelligence across Kalshi and Polymarket' },
  ],
};

// Feature grid - prediction markets first
const FEATURES = [
  {
    icon: <BarChart3 className="w-6 h-6" />,
    title: 'Prediction Markets',
    description: 'Live Kalshi and Polymarket odds. Cross-platform comparison. Event tracking with settlement countdowns.',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10',
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: 'Emotional Firewall',
    description: 'Detects revenge trading, overtrading, and exhaustion in real time. Your behavioral circuit breaker.',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
  },
  {
    icon: <MessageSquare className="w-6 h-6" />,
    title: 'AI Research Assistant',
    description: '30+ analysis tools powered by Claude. Challenge your thesis, find the bearish case, stress-test assumptions.',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
  },
  {
    icon: <Lightbulb className="w-6 h-6" />,
    title: 'Thesis Engine',
    description: 'Structured hypotheses that mature over time. Link theses to prediction markets with live validation scores.',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
  },
  {
    icon: <BookOpen className="w-6 h-6" />,
    title: 'Trade Journal',
    description: 'Log trades with emotional state, P&L tracking, and rich text notes. See your patterns over time.',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
  },
  {
    icon: <TrendingUp className="w-6 h-6" />,
    title: 'Professional Charts',
    description: '30+ indicators, drawing tools, and multi-timeframe analysis. Real-time data via Alpaca.',
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
  },
  {
    icon: <Calculator className="w-6 h-6" />,
    title: 'Options Builder',
    description: 'Full options chains, Greeks, and multi-leg strategy construction with payoff diagrams.',
    color: 'text-pink-400',
    bgColor: 'bg-pink-500/10',
  },
  {
    icon: <Newspaper className="w-6 h-6" />,
    title: 'News & Screener',
    description: 'Natural language stock screener. Auto-refreshing news. Congressional trading tracker.',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
  },
];

// Emotional Firewall patterns
const FIREWALL_PATTERNS = [
  {
    icon: <Flame className="w-5 h-5" />,
    name: 'Revenge Trading',
    description: 'Blocked when you trade within 30 min of a loss',
    cooldown: '60 min cooldown',
    color: 'text-red-400',
    bgColor: 'bg-red-500/15',
    borderColor: 'border-red-500/30',
  },
  {
    icon: <Activity className="w-5 h-5" />,
    name: 'Overtrading',
    description: 'Triggered at 3+ trades/hour or 10+ trades/day',
    cooldown: '4 hour cooldown',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/15',
    borderColor: 'border-orange-500/30',
  },
  {
    icon: <TrendingDown className="w-5 h-5" />,
    name: 'Streak Blindness',
    description: 'Warns during 5+ consecutive wins or losses',
    cooldown: '3 hour cooldown',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/15',
    borderColor: 'border-yellow-500/30',
  },
];

// AI Models powering the chat
const AI_MODELS = [
  {
    name: 'Claude',
    company: 'Anthropic',
    description: 'Sonnet, Opus & Haiku',
    // Official Anthropic logo from Bootstrap Icons
    icon: (
      <svg viewBox="0 0 16 16" className="w-8 h-8" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M9.218 2h2.402L16 12.987h-2.402zM4.379 2h2.512l4.38 10.987H8.82l-.895-2.308h-4.58l-.896 2.307H0L4.38 2.001zm2.755 6.64L5.635 4.777 4.137 8.64z"
        />
      </svg>
    ),
    color: 'text-amber-400',
  },
  {
    name: 'Grok',
    company: 'xAI',
    description: 'Fast analysis',
    // X/xAI style
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
    color: 'text-white',
  },
  {
    name: 'Perplexity',
    company: 'Perplexity AI',
    description: 'Real-time search',
    // Official Perplexity logo - angular P shape
    icon: (
      <svg viewBox="0 0 512 509.64" className="w-8 h-8">
        <path
          fill="currentColor"
          fillRule="evenodd"
          d="M348.851 128.063l-68.946 58.302h68.946v-58.302zm-83.908 48.709l100.931-85.349v94.942h32.244v143.421h-38.731v90.004l-94.442-86.662v83.946h-17.023v-83.906l-96.596 86.246v-89.628h-37.445V186.365h38.732V90.768l95.309 84.958v-83.16h17.023l-.002 84.206zm-29.209 26.616c-34.955.02-69.893 0-104.83 0v109.375h20.415v-27.121l84.415-82.254zm41.445 0l82.208 82.324v27.051h21.708V203.388c-34.617 0-69.274.02-103.916 0zm-42.874-17.023l-64.669-57.646v57.646h64.669zm13.617 124.076v-95.2l-79.573 77.516v88.731l79.573-71.047zm17.252-95.022v94.863l77.19 70.83c0-29.485-.012-58.943-.012-88.425l-77.178-77.268z"
        />
      </svg>
    ),
    color: 'text-cyan-400',
  },
  {
    name: 'DeepSeek R1',
    company: 'via Perplexity',
    description: 'Advanced reasoning',
    // DeepSeek official whale logo
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M23.748 4.482c-.254-.124-.364.113-.512.234-.051.039-.094.09-.137.136-.372.397-.806.657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.156-.708-.311-.955-.65-.172-.241-.219-.51-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.093.172.187.129.323-.082.28-.18.552-.266.833-.055.179-.137.217-.329.14a5.526 5.526 0 01-1.736-1.18c-.857-.828-1.631-1.742-2.597-2.458a11.365 11.365 0 00-.689-.471c-.985-.957.13-1.743.388-1.836.27-.098.093-.432-.779-.428-.872.004-1.67.295-2.687.684a3.055 3.055 0 01-.465.137 9.597 9.597 0 00-2.883-.102c-1.885.21-3.39 1.102-4.497 2.623C.082 8.606-.231 10.684.152 12.85c.403 2.284 1.569 4.175 3.36 5.653 1.858 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.133-.284 4.994-1.86.47.234.962.327 1.78.397.63.059 1.236-.03 1.705-.128.735-.156.684-.837.419-.961-2.155-1.004-1.682-.595-2.113-.926 1.096-1.296 2.746-2.642 3.392-7.003.05-.347.007-.565 0-.845-.004-.17.035-.237.23-.256a4.173 4.173 0 001.545-.475c1.396-.763 1.96-2.015 2.093-3.517.02-.23-.004-.467-.247-.588zM11.581 18c-2.089-1.642-3.102-2.183-3.52-2.16-.392.024-.321.471-.235.763.09.288.207.486.371.739.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.167-1.361-.802-2.5-1.86-3.301-3.307-.774-1.393-1.224-2.887-1.298-4.482-.02-.386.093-.522.477-.592a4.696 4.696 0 011.529-.039c2.132.312 3.946 1.265 5.468 2.774.868.86 1.525 1.887 2.202 2.891.72 1.066 1.494 2.082 2.48 2.914.348.292.625.514.891.677-.802.09-2.14.11-3.054-.614zm1-6.44a.306.306 0 01.415-.287.302.302 0 01.2.288.306.306 0 01-.31.307.303.303 0 01-.304-.308zm3.11 1.596c-.2.081-.399.151-.59.16a1.245 1.245 0 01-.798-.254c-.274-.23-.47-.358-.552-.758a1.73 1.73 0 01.016-.588c.07-.327-.008-.537-.239-.727-.187-.156-.426-.199-.688-.199a.559.559 0 01-.254-.078c-.11-.054-.2-.19-.114-.358.028-.054.16-.186.192-.21.356-.202.767-.136 1.146.016.352.144.618.408 1.001.782.391.451.462.576.685.914.176.265.336.537.445.848.067.195-.019.354-.25.452z" />
      </svg>
    ),
    color: 'text-blue-400',
  },
];

// Data sources powering the platform
const DATA_SOURCES = [
  {
    name: 'Alpaca',
    description: 'Market data & news',
    // Alpaca llama head logo - friendly llama silhouette
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M17.5 4c-.8 0-1.5.3-2 .8L14 6.5c-.5-.3-1-.5-1.5-.5-1.5 0-3 1-3.5 2.5L8.5 10c-1 .5-1.5 1.5-1.5 2.5v1.5c0 1 .5 2 1.5 2.5v3.5c0 .6.4 1 1 1h1c.6 0 1-.4 1-1v-3h2v3c0 .6.4 1 1 1h1c.6 0 1-.4 1-1v-3.5c1-.5 1.5-1.5 1.5-2.5v-1.5c0-.5-.1-1-.3-1.5l1.8-2.5c.3-.5.5-1 .5-1.5V5c0-.6-.4-1-1-1h-1zm-1 4c.6 0 1 .4 1 1s-.4 1-1 1-1-.4-1-1 .4-1 1-1z" />
      </svg>
    ),
    color: 'text-yellow-400',
  },
  {
    name: 'Kalshi',
    description: 'CFTC-regulated markets',
    // K logo style
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M6 4h3v7l6-7h4l-7 8 7 8h-4l-6-7v7H6z" />
      </svg>
    ),
    color: 'text-green-400',
  },
  {
    name: 'Polymarket',
    description: 'Prediction markets',
    // P with market chart
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M7 4h5c3 0 5 2 5 5s-2 5-5 5H9v6H7V4zm2 8h3c1.7 0 3-1.3 3-3s-1.3-3-3-3H9v6z" />
      </svg>
    ),
    color: 'text-purple-400',
  },
  {
    name: 'Supabase',
    description: 'Auth & database',
    // Supabase style
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M13.5 21.5c-.4.6-1.4.2-1.4-.5V14h8.4c.9 0 1.4 1 .8 1.7l-7.8 5.8zM10.5 2.5c.4-.6 1.4-.2 1.4.5V10H3.5c-.9 0-1.4-1-.8-1.7l7.8-5.8z" />
      </svg>
    ),
    color: 'text-emerald-400',
  },
];

// ============================================
// ANIMATED FEATURE DEMOS
// ============================================

// Process Integrity Flow Demo
function ProcessIntegrityDemo() {
  const [step, setStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffectReact(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setStep((s) => (s + 1) % 5);
    }, 2000);
    return () => clearInterval(timer);
  }, [isPlaying]);

  const steps = [
    { label: 'User declares intent', sublabel: '"I\'m going to buy NVDA"', color: 'text-blue-400' },
    { label: 'Research Quality Check', sublabel: 'Score: 72%', color: 'text-green-400' },
    { label: 'Time in Thesis Check', sublabel: '1.5 hours (Nascent)', color: 'text-yellow-400' },
    { label: 'Friction Generated', sublabel: 'Medium: "Thesis is young"', color: 'text-orange-400' },
    { label: 'User Decides', sublabel: 'Override or Wait', color: 'text-purple-400' },
  ];

  return (
    <div className="relative p-6 rounded-2xl bg-card/40 border border-border/50 backdrop-blur-sm h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-orange-400" />
          <span className="font-bold text-sm">Process Integrity Flow</span>
        </div>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
        >
          {isPlaying ? <RotateCcw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
      </div>

      <div className="space-y-2">
        {steps.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0.4, x: -10 }}
            animate={{
              opacity: step >= i ? 1 : 0.4,
              x: step >= i ? 0 : -10,
              scale: step === i ? 1.02 : 1,
            }}
            transition={{ duration: 0.3 }}
            className={`p-3 rounded-lg border ${
              step === i
                ? 'bg-card/80 border-orange-500/50 shadow-lg shadow-orange-500/10'
                : step > i
                  ? 'bg-card/40 border-border/30'
                  : 'bg-card/20 border-transparent'
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  step > i
                    ? 'bg-green-500/20 text-green-400'
                    : step === i
                      ? 'bg-orange-500/20 text-orange-400'
                      : 'bg-muted/30 text-muted-foreground'
                }`}
              >
                {step > i ? <CheckCircle className="w-4 h-4" /> : i + 1}
              </div>
              <div className="flex-1">
                <p className={`text-sm font-medium ${step >= i ? s.color : 'text-muted-foreground'}`}>
                  {s.label}
                </p>
                <p className="text-xs text-muted-foreground">{s.sublabel}</p>
              </div>
              {step === i && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-2 h-2 rounded-full bg-orange-400 animate-pulse"
                />
              )}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-4 flex gap-1">
        {steps.map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              step >= i ? 'bg-orange-400' : 'bg-muted/30'
            }`}
          />
        ))}
      </div>
    </div>
  );
}

// Thesis Evolution Demo
function ThesisEvolutionDemo() {
  const [stage, setStage] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffectReact(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setStage((s) => (s + 1) % 4);
    }, 2500);
    return () => clearInterval(timer);
  }, [isPlaying]);

  const stages = [
    {
      status: 'Nascent',
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
      borderColor: 'border-yellow-500/30',
      thesis: 'NVDA looks bullish',
      details: 'Initial idea, no research',
      score: 25,
    },
    {
      status: 'Developing',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
      borderColor: 'border-blue-500/30',
      thesis: 'NVDA: AI demand + data center growth',
      details: 'Analysis started, thesis forming',
      score: 55,
    },
    {
      status: 'Active',
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
      borderColor: 'border-green-500/30',
      thesis: 'NVDA: Dominant AI infrastructure play',
      details: 'Full analysis, assumptions documented',
      score: 82,
    },
    {
      status: 'Validated',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/20',
      borderColor: 'border-purple-500/30',
      thesis: 'NVDA: Entry at $138, thesis confirmed',
      details: 'Conviction proven, position taken',
      score: 95,
    },
  ];

  const current = stages[stage];

  return (
    <div className="relative p-6 rounded-2xl bg-card/40 border border-border/50 backdrop-blur-sm h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-purple-400" />
          <span className="font-bold text-sm">Thesis Evolution</span>
        </div>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
        >
          {isPlaying ? <RotateCcw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
      </div>

      {/* Status badge */}
      <motion.div
        key={stage}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${current.bgColor} ${current.color} border ${current.borderColor}`}>
          <div className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
          {current.status}
        </span>
      </motion.div>

      {/* Thesis content */}
      <motion.div
        key={`thesis-${stage}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={`p-4 rounded-xl border ${current.borderColor} ${current.bgColor.replace('/20', '/10')} mb-4`}
      >
        <p className="font-medium text-sm mb-1">{current.thesis}</p>
        <p className="text-xs text-muted-foreground">{current.details}</p>
      </motion.div>

      {/* Research score bar */}
      <div className="mb-2">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-muted-foreground">Research Score</span>
          <span className={current.color}>{current.score}%</span>
        </div>
        <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${current.score}%` }}
            transition={{ duration: 0.5 }}
            className={`h-full rounded-full ${current.bgColor.replace('/20', '')}`}
          />
        </div>
      </div>

      {/* Stage indicator */}
      <div className="flex gap-2 mt-4">
        {stages.map((s, i) => (
          <button
            key={i}
            onClick={() => {
              setStage(i);
              setIsPlaying(false);
            }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all ${
              stage === i
                ? `${s.bgColor} ${s.color} border ${s.borderColor}`
                : 'bg-muted/20 text-muted-foreground hover:bg-muted/40'
            }`}
          >
            {s.status}
          </button>
        ))}
      </div>
    </div>
  );
}

// Research Quality Building Demo
function ResearchQualityDemo() {
  const [activities, setActivities] = useState<{ action: string; points: number; done: boolean }[]>([
    { action: 'Analyzed fundamentals', points: 15, done: false },
    { action: 'Checked bearish case', points: 20, done: false },
    { action: 'Documented assumptions', points: 15, done: false },
    { action: 'Reviewed news sentiment', points: 10, done: false },
    { action: 'Calculated position size', points: 12, done: false },
  ]);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffectReact(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = prev + 1;
        if (next >= activities.length) {
          // Reset after showing all
          setTimeout(() => {
            setActivities((acts) => acts.map((a) => ({ ...a, done: false })));
            setCurrentIndex(-1);
          }, 1500);
          return prev;
        }
        setActivities((acts) =>
          acts.map((a, i) => (i === next ? { ...a, done: true } : a))
        );
        return next;
      });
    }, 1200);
    return () => clearInterval(timer);
  }, [isPlaying, activities.length]);

  const totalScore = activities.reduce((sum, a) => sum + (a.done ? a.points : 0), 0);
  const maxScore = activities.reduce((sum, a) => sum + a.points, 0);

  return (
    <div className="relative p-6 rounded-2xl bg-card/40 border border-border/50 backdrop-blur-sm h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-green-400" />
          <span className="font-bold text-sm">Research Quality Score</span>
        </div>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
        >
          {isPlaying ? <RotateCcw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
      </div>

      {/* Score display */}
      <div className="text-center mb-4">
        <motion.div
          key={totalScore}
          initial={{ scale: 1.2 }}
          animate={{ scale: 1 }}
          className="text-4xl font-bold"
        >
          <span className={totalScore > 50 ? 'text-green-400' : totalScore > 25 ? 'text-yellow-400' : 'text-red-400'}>
            {totalScore}
          </span>
          <span className="text-muted-foreground text-lg">/{maxScore}</span>
        </motion.div>
        <p className="text-xs text-muted-foreground">Research Points</p>
      </div>

      {/* Activities */}
      <div className="space-y-2">
        {activities.map((activity, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0.5 }}
            animate={{
              opacity: activity.done ? 1 : 0.5,
              scale: currentIndex === i ? 1.02 : 1,
            }}
            className={`flex items-center justify-between p-2 rounded-lg transition-colors ${
              activity.done ? 'bg-green-500/10 border border-green-500/30' : 'bg-muted/20'
            }`}
          >
            <div className="flex items-center gap-2">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center ${
                  activity.done ? 'bg-green-500/20 text-green-400' : 'bg-muted/30 text-muted-foreground'
                }`}
              >
                {activity.done ? <CheckCircle className="w-3 h-3" /> : <div className="w-2 h-2 rounded-full bg-current" />}
              </div>
              <span className={`text-sm ${activity.done ? 'text-foreground' : 'text-muted-foreground'}`}>
                {activity.action}
              </span>
            </div>
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: activity.done ? 1 : 0.3 }}
              className={`text-xs font-bold ${activity.done ? 'text-green-400' : 'text-muted-foreground'}`}
            >
              +{activity.points}
            </motion.span>
          </motion.div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(totalScore / maxScore) * 100}%` }}
            transition={{ duration: 0.3 }}
            className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full"
          />
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });

  // Parallax transforms for hero
  const heroOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.5], [1, 0.95]);
  const heroY = useTransform(scrollYProgress, [0, 0.5], [0, 50]);

  // Enable scrolling on landing page (overrides global overflow:hidden)
  useEffect(() => {
    document.documentElement.classList.add('landing-page');
    document.body.classList.add('landing-page');
    return () => {
      document.documentElement.classList.remove('landing-page');
      document.body.classList.remove('landing-page');
    };
  }, []);

  return (
    <div className="min-h-screen bg-background relative overflow-x-hidden">
      {/* Scroll Progress Bar */}
      <ScrollProgressBar />

      {/* Background Layer - Fixed position */}
      <div className="fixed inset-0 z-0">
        <IntelligentBackground />
      </div>

      {/* Frosted Glass Overlay */}
      <FrostedOverlay intensity="medium" className="fixed inset-0 z-10" />

      {/* Content Layer */}
      <div className="relative z-20">
        {/* Navigation */}
        <nav className="fixed top-0 left-0 right-0 z-50 bg-background/50 backdrop-blur-md border-b border-border/20 supports-[backdrop-filter]:bg-background/20">
          <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="w-7 h-7 text-primary animate-pulse-soft" />
              <span className="text-xl font-semibold tracking-tight">deepstack</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/help"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors hidden sm:inline"
              >
                Help
              </Link>
              <Link
                href="/login"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/app"
                className="px-4 py-2 text-sm bg-primary/90 text-primary-foreground hover:bg-primary rounded-lg font-medium transition-all shadow-[0_0_15px_rgba(251,146,60,0.3)] hover:shadow-[0_0_25px_rgba(251,146,60,0.5)]"
              >
                Try Demo
              </Link>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section ref={heroRef} className="min-h-screen flex items-center justify-center pt-16 px-4 relative">
          <motion.div
            style={{ opacity: heroOpacity, scale: heroScale, y: heroY }}
            className="max-w-5xl mx-auto text-center"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-8 border border-primary/20 backdrop-blur-sm"
            >
              <BarChart3 className="w-4 h-4" />
              <span>Prediction Market Intelligence</span>
            </motion.div>

            {/* Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="text-5xl md:text-7xl font-bold mb-6 tracking-tight leading-[1.1]"
            >
              Trade Smarter.
              <br />
              <span className="text-gradient-shimmer">Not More.</span>
            </motion.h1>

            {/* Evocative tagline */}
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="text-2xl md:text-3xl text-foreground/90 mb-4 font-medium"
            >
              The research terminal for Kalshi and Polymarket traders who want to win with discipline, not impulse.
            </motion.p>

            {/* Subheadline */}
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed"
            >
              AI-powered analysis, cross-platform odds, and an emotional firewall that catches revenge trading before it costs you. 92% of prediction market traders lose. DeepStack helps you be in the 8%.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3 }}
              className="flex flex-col items-center gap-4"
            >
              {/* Free Forever Badge */}
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 text-sm font-bold border border-emerald-500/30"
              >
                <Sparkles className="w-4 h-4" />
                100% FREE — No Credit Card Required
              </motion.div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Link
                    href="/app"
                    className="relative w-full sm:w-auto px-10 py-5 bg-primary text-primary-foreground hover:bg-primary/90 rounded-2xl font-bold transition-all text-xl flex items-center justify-center gap-3 group shadow-[0_0_30px_rgba(251,146,60,0.5)] hover:shadow-[0_0_50px_rgba(251,146,60,0.7)]"
                  >
                    {/* Animated ring */}
                    <span className="absolute inset-0 rounded-2xl border-2 border-primary/50 animate-ping opacity-20" />
                    Start Trading Smarter
                    <ChevronRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </motion.div>
                <Link
                  href="#how-it-works"
                  className="w-full sm:w-auto px-8 py-4 bg-secondary/80 text-secondary-foreground hover:bg-secondary/90 rounded-xl font-medium transition-all text-lg backdrop-blur-sm border border-border/50"
                >
                  See How It Works
                </Link>
              </div>
            </motion.div>

            {/* Trust Signals */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.5 }}
              className="mt-8 flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-sm text-muted-foreground/80"
            >
              <span className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-primary/70" />
                No signup required
              </span>
              <span className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary/70" />
                Data stays private
              </span>
              <span className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-primary/70" />
                Powered by Claude
              </span>
            </motion.div>

            {/* Scroll indicator */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.7 }}
              className="absolute bottom-8 left-1/2 -translate-x-1/2"
            >
              <motion.div
                animate={{ y: [0, 8, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                className="w-6 h-10 rounded-full border-2 border-muted-foreground/30 flex items-start justify-center p-2"
              >
                <motion.div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
              </motion.div>
            </motion.div>
          </motion.div>
        </section>

        {/* ================================================================== */}
        {/* THE THREE PILLARS */}
        {/* ================================================================== */}
        <StickySection
          id="pillars"
          title="Why Traders Choose DeepStack"
          subtitle="Intelligence. Discipline. Conviction."
          badge="The Edge"
          badgeIcon={<BarChart3 className="w-4 h-4" />}
          badgeColor="bg-primary/10 text-primary border-primary/20"
          scrollHeight="min-h-fit"
          align="center"
        >
          {/* Three Pillars */}
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {THREE_PILLARS.map((pillar, i) => (
              <ScrollReveal key={pillar.title} delay={i * 0.1} direction="up">
                <div className={`p-6 rounded-2xl bg-card/30 border ${pillar.borderColor} backdrop-blur-sm text-center h-full`}>
                  <div className={`w-16 h-16 rounded-2xl ${pillar.bgColor} flex items-center justify-center ${pillar.color} mx-auto mb-4`}>
                    {pillar.icon}
                  </div>
                  <p className={`text-xs font-bold uppercase tracking-wider ${pillar.color} mb-2`}>{pillar.subtitle}</p>
                  <h3 className="text-xl font-bold mb-3">{pillar.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{pillar.description}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </StickySection>

        {/* ================================================================== */}
        {/* WHAT WE'RE NOT / WHAT WE ARE */}
        {/* ================================================================== */}
        <section className="py-20 px-4 relative">
          <div className="max-w-4xl mx-auto">
            <ScrollReveal className="text-center mb-12">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50 text-muted-foreground text-sm font-medium border border-border/30 mb-4">
                <Search className="w-4 h-4" />
                Honest About What We Are
              </span>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Built for prediction market traders who want an edge, not a shortcut.
              </h2>
            </ScrollReveal>

            <div className="grid md:grid-cols-2 gap-6">
              {/* NOT Column */}
              <ScrollReveal direction="left">
                <div className="p-6 rounded-2xl bg-red-500/5 border border-red-500/20">
                  <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
                    <XCircle className="w-5 h-5" />
                    DeepStack is NOT
                  </h3>
                  <ul className="space-y-3">
                    {NOT_IS_COMPARISON.not.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-muted-foreground">
                        <span className="text-red-400/60 mt-0.5">{item.icon}</span>
                        <span>{item.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </ScrollReveal>

              {/* IS Column */}
              <ScrollReveal direction="right" delay={0.1}>
                <div className="p-6 rounded-2xl bg-green-500/5 border border-green-500/20">
                  <h3 className="text-lg font-bold text-green-400 mb-4 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    DeepStack IS
                  </h3>
                  <ul className="space-y-3">
                    {NOT_IS_COMPARISON.is.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-foreground/80">
                        <span className="text-green-400 mt-0.5">{item.icon}</span>
                        <span>{item.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </ScrollReveal>
            </div>
          </div>
        </section>

        {/* ================================================================== */}
        {/* HOW IT WORKS - Process Integrity Engine */}
        {/* ================================================================== */}
        <section id="how-it-works" className="py-24 px-4 relative bg-gradient-to-b from-transparent via-orange-950/5 to-transparent">
          <div className="max-w-6xl mx-auto">
            {/* Section Header */}
            <ScrollReveal className="text-center mb-16">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium border border-primary/20 mb-4">
                <Shield className="w-4 h-4" />
                Emotional Discipline Engine
              </span>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Your behavioral circuit breaker.{' '}
                <span className="text-gradient-shimmer">Not a nanny.</span>
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                When you&apos;re about to act, we check three dimensions. If your process is weak, you&apos;ll know — and you can still proceed.
              </p>
            </ScrollReveal>

            {/* Two-panel layout */}
            <div className="grid lg:grid-cols-2 gap-8">
              {/* Panel 1: AI Research */}
              <ScrollReveal direction="left">
                <div className="h-full p-6 rounded-2xl bg-card/30 border border-border/30 backdrop-blur-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                      <Brain className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-bold">AI Research Assistant</h3>
                      <p className="text-xs text-muted-foreground">Challenge your thesis, find the bearish case</p>
                    </div>
                  </div>
                  <TypewriterChatDemo />
                </div>
              </ScrollReveal>

              {/* Panel 2: Process Integrity */}
              <ScrollReveal direction="right" delay={0.1}>
                <div className="h-full p-6 rounded-2xl bg-card/30 border border-orange-500/20 backdrop-blur-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center">
                      <Shield className="w-5 h-5 text-orange-400" />
                    </div>
                    <div>
                      <h3 className="font-bold">Process Integrity Check</h3>
                      <p className="text-xs text-muted-foreground">Three dimensions before commitment</p>
                    </div>
                  </div>

                  {/* Three Dimensions */}
                  <div className="space-y-3 mb-4">
                    {INTEGRITY_DIMENSIONS.map((dim) => (
                      <div key={dim.name} className={`p-3 rounded-lg ${dim.bgColor} border border-border/30 flex items-center gap-3`}>
                        <div className={`${dim.color} shrink-0`}>{dim.icon}</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-sm">{dim.name}</p>
                            <span className={`text-xs font-bold ${dim.color}`}>
                              {typeof dim.score === 'number' ? `${dim.score}%` : dim.score}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground truncate">{dim.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Friction mockup */}
                  <div className="rounded-xl bg-card/60 border border-orange-500/30 p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium">Friction Level</span>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                        <span className="text-xs text-yellow-400 font-medium">Medium</span>
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 mb-3">
                      <p className="text-sm text-foreground/90 mb-1">
                        &quot;Your thesis is still young. You&apos;ve been developing it for less than 2 hours.&quot;
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Good ideas survive the overnight test.
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button className="flex-1 px-3 py-2 text-xs font-medium rounded-lg bg-muted/50 text-muted-foreground border border-border/50">
                        Wait & Research
                      </button>
                      <button className="flex-1 px-3 py-2 text-xs font-medium rounded-lg bg-orange-500/20 text-orange-400 border border-orange-500/30">
                        Override with Reason
                      </button>
                    </div>
                  </div>
                </div>
              </ScrollReveal>
            </div>
          </div>
        </section>

        {/* Thesis Builder and Prediction Markets sections removed - consolidated into Full Toolkit below */}

        {/* ================================================================== */}
        {/* FEATURES GRID - Full Toolkit */}
        {/* ================================================================== */}
        <StickySection
          id="features"
          title="Your Complete Trading Terminal"
          subtitle="Prediction markets, research, discipline. One workspace."
          badge="Full Toolkit"
          badgeIcon={<Sparkles className="w-4 h-4" />}
          scrollHeight="min-h-fit"
          className="bg-card/20"
          align="center"
        >
          {/* Feature cards with parallax */}
          <ParallaxSection speed={30} direction="left" className="mt-16">
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {FEATURES.slice(0, 4).map((feature, i) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.5, delay: i * 0.05 }}
                  whileHover={{
                    y: -8,
                    scale: 1.02,
                    transition: { duration: 0.25, ease: 'easeOut' }
                  }}
                  className="relative bg-card/40 backdrop-blur-md border border-border/50 rounded-2xl p-5 hover:border-primary/50 hover:bg-card/60 transition-all duration-300 group hover:shadow-[0_8px_30px_rgba(251,146,60,0.15)]"
                >
                  <motion.div
                    className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${feature.bgColor}`}
                    whileHover={{ scale: 1.15, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className={`${feature.color} group-hover:drop-shadow-[0_0_8px_currentColor] transition-all duration-300`}>
                      {feature.icon}
                    </div>
                  </motion.div>
                  <h3 className="text-base font-bold mb-2 group-hover:text-primary transition-colors duration-200">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground text-sm leading-relaxed group-hover:text-muted-foreground/90 transition-colors duration-200">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </ParallaxSection>

          <ParallaxSection speed={30} direction="right" className="mt-4">
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {FEATURES.slice(4, 8).map((feature, i) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.5, delay: i * 0.05 }}
                  whileHover={{
                    y: -8,
                    scale: 1.02,
                    transition: { duration: 0.25, ease: 'easeOut' }
                  }}
                  className="relative bg-card/40 backdrop-blur-md border border-border/50 rounded-2xl p-5 hover:border-primary/50 hover:bg-card/60 transition-all duration-300 group hover:shadow-[0_8px_30px_rgba(251,146,60,0.15)]"
                >
                  <motion.div
                    className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${feature.bgColor}`}
                    whileHover={{ scale: 1.15, rotate: 5 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className={`${feature.color} group-hover:drop-shadow-[0_0_8px_currentColor] transition-all duration-300`}>
                      {feature.icon}
                    </div>
                  </motion.div>
                  <h3 className="text-base font-bold mb-2 group-hover:text-primary transition-colors duration-200">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground text-sm leading-relaxed group-hover:text-muted-foreground/90 transition-colors duration-200">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </ParallaxSection>
        </StickySection>

        {/* ================================================================== */}
        {/* FEATURES IN ACTION - 3 Animated Demos */}
        {/* ================================================================== */}
        <section className="py-24 px-4 relative bg-gradient-to-b from-transparent via-primary/5 to-transparent">
          <div className="max-w-6xl mx-auto">
            {/* Section Header */}
            <ScrollReveal className="text-center mb-16">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium border border-primary/20 mb-4">
                <Play className="w-4 h-4" />
                Features in Action
              </span>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                See How It{' '}
                <span className="text-gradient-shimmer">Actually Works</span>
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Three core features that turn scattered research into grounded conviction.
              </p>
            </ScrollReveal>

            {/* Three Animated Demos */}
            <div className="grid lg:grid-cols-3 gap-6">
              <ScrollReveal direction="up" delay={0}>
                <ProcessIntegrityDemo />
              </ScrollReveal>
              <ScrollReveal direction="up" delay={0.1}>
                <ThesisEvolutionDemo />
              </ScrollReveal>
              <ScrollReveal direction="up" delay={0.2}>
                <ResearchQualityDemo />
              </ScrollReveal>
            </div>

            {/* Feature descriptions */}
            <div className="grid lg:grid-cols-3 gap-6 mt-8">
              <ScrollReveal delay={0.1}>
                <div className="text-center p-4">
                  <h3 className="font-bold text-orange-400 mb-2">Process Integrity</h3>
                  <p className="text-sm text-muted-foreground">
                    When you declare intent to act, we check your research quality, time-in-thesis, and conviction. Friction reveals weak process.
                  </p>
                </div>
              </ScrollReveal>
              <ScrollReveal delay={0.15}>
                <div className="text-center p-4">
                  <h3 className="font-bold text-purple-400 mb-2">Thesis Evolution</h3>
                  <p className="text-sm text-muted-foreground">
                    Track how your thesis matures from nascent idea to validated conviction. Good ideas survive overnight.
                  </p>
                </div>
              </ScrollReveal>
              <ScrollReveal delay={0.2}>
                <div className="text-center p-4">
                  <h3 className="font-bold text-green-400 mb-2">Research Score</h3>
                  <p className="text-sm text-muted-foreground">
                    Every research action builds your score. Analysis, devil&apos;s advocate, assumptions — all tracked.
                  </p>
                </div>
              </ScrollReveal>
            </div>
          </div>
        </section>

        {/* ================================================================== */}
        {/* POWERED BY - Full Services Section */}
        {/* ================================================================== */}
        <section className="py-20 px-4 border-y border-border/20 bg-card/10">
          <div className="max-w-5xl mx-auto">
            <ScrollReveal className="text-center mb-12">
              <h3 className="text-2xl font-bold mb-2">Powered by Industry Leaders</h3>
              <p className="text-sm text-muted-foreground">Enterprise-grade AI and real-time market data</p>
            </ScrollReveal>

            {/* AI Models */}
            <ScrollReveal delay={0.1}>
              <div className="mb-10">
                <p className="text-center text-xs text-muted-foreground font-medium uppercase tracking-wider mb-6">
                  AI Models
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {AI_MODELS.map((model, i) => (
                    <motion.div
                      key={model.name}
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.05 }}
                      whileHover={{ scale: 1.05, y: -4 }}
                      className="p-4 rounded-xl bg-card/40 border border-border/50 backdrop-blur-sm text-center hover:border-primary/30 transition-colors group"
                    >
                      <div className={`${model.color} opacity-60 group-hover:opacity-100 transition-opacity mx-auto mb-2 flex justify-center`}>
                        {model.icon}
                      </div>
                      <p className="font-medium text-sm">{model.name}</p>
                      <p className="text-xs text-muted-foreground">{model.description}</p>
                    </motion.div>
                  ))}
                </div>
              </div>
            </ScrollReveal>

            {/* Data Sources */}
            <ScrollReveal delay={0.2}>
              <div>
                <p className="text-center text-xs text-muted-foreground font-medium uppercase tracking-wider mb-6">
                  Data Sources
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {DATA_SOURCES.map((source, i) => (
                    <motion.div
                      key={source.name}
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.05 }}
                      whileHover={{ scale: 1.05, y: -4 }}
                      className="p-4 rounded-xl bg-card/40 border border-border/50 backdrop-blur-sm text-center hover:border-primary/30 transition-colors group"
                    >
                      <div className={`${source.color} opacity-60 group-hover:opacity-100 transition-opacity mx-auto mb-2 flex justify-center`}>
                        {source.icon}
                      </div>
                      <p className="font-medium text-sm">{source.name}</p>
                      <p className="text-xs text-muted-foreground">{source.description}</p>
                    </motion.div>
                  ))}
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>

        {/* ================================================================== */}
        {/* Final CTA Section with Founder Story */}
        {/* ================================================================== */}
        <section className="py-32 px-4 relative">
          {/* Glow effect */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />

          <div className="max-w-3xl mx-auto text-center relative">
            {/* Founder Story - emotional close */}
            <ScrollReveal>
              <div className="mb-12 p-6 rounded-2xl bg-card/30 border border-primary/20 text-center max-w-xl mx-auto">
                <Quote className="w-6 h-6 text-primary/40 mx-auto mb-3" />
                <p className="text-base italic text-foreground/80 mb-3 leading-relaxed">
                  &quot;I built a trading bot that placed unauthorized trades. I realized the problem was never the code. It was me trading on impulse without a system. That is why I built DeepStack.&quot;
                </p>
                <p className="text-xs text-muted-foreground font-medium">— Eddie, Founder</p>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={0.1}>
              <h2 className="text-4xl md:text-6xl font-bold mb-6">
                Ready to trade
                <br />
                <span className="text-gradient-shimmer">with discipline?</span>
              </h2>
            </ScrollReveal>

            <ScrollReveal delay={0.2}>
              <p className="text-muted-foreground text-xl mb-8">
                Prediction market intelligence meets emotional discipline. Free to start.
              </p>
            </ScrollReveal>

            <ScrollReveal delay={0.3}>
              <div className="flex flex-col items-center gap-4">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Link
                    href="/app"
                    className="relative inline-flex items-center justify-center gap-3 px-12 py-6 bg-primary text-primary-foreground hover:bg-primary/90 rounded-2xl font-bold transition-all text-xl group shadow-[0_0_40px_rgba(251,146,60,0.5)] hover:shadow-[0_0_60px_rgba(251,146,60,0.7)]"
                  >
                    <span className="absolute inset-0 rounded-2xl border-2 border-primary/50 animate-ping opacity-20" />
                    Start Trading Smarter
                    <ChevronRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </motion.div>
                <p className="text-sm text-muted-foreground flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  100% Free — No credit card required
                </p>
              </div>
            </ScrollReveal>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 px-4 border-t border-border/20 bg-background/60 backdrop-blur-md">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-primary" />
                <span className="font-semibold tracking-tight">deepstack</span>
                <span className="text-muted-foreground text-sm ml-2 px-2 py-0.5 bg-muted rounded-full">
                  Prediction Market Intelligence
                </span>
              </div>
              <div className="flex items-center gap-8 text-sm font-medium">
                <Link
                  href="/help"
                  className="text-muted-foreground hover:text-primary transition-colors"
                >
                  Help Center
                </Link>
                <Link
                  href="/terms"
                  className="text-muted-foreground hover:text-primary transition-colors"
                >
                  Terms
                </Link>
                <Link
                  href="/privacy"
                  className="text-muted-foreground hover:text-primary transition-colors"
                >
                  Privacy
                </Link>
              </div>
            </div>
            <div className="mt-8 text-center text-xs text-muted-foreground/60 max-w-2xl mx-auto leading-relaxed">
              deepstack is a research platform powered by AI. It does not execute trades or provide
              personalized financial advice. All investing involves risk.
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
