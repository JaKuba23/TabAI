"use client"

import { useState } from "react"
import Badge from "@/components/ui/Badge"
import Card from "@/components/ui/Card"

interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  cta: string
  highlighted: boolean
  badge: string | null
}

const tiers: Tier[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Try TabAI with basic features.",
    features: [
      "3 songs per month",
      "Standard tuning only",
      "GP5 download",
      "Community support",
    ],
    cta: "Get Started",
    highlighted: false,
    badge: null,
  },
  {
    name: "Pro",
    price: "$9.99",
    period: "/mo",
    description: "For serious guitarists who want more.",
    features: [
      "50 songs per month",
      "All tunings supported",
      "GP5 + MIDI + MusicXML downloads",
      "Priority processing",
      "Chord progression analysis",
    ],
    cta: "Subscribe",
    highlighted: true,
    badge: "Most Popular",
  },
  {
    name: "Studio",
    price: "$29.99",
    period: "/mo",
    description: "For professionals and studios.",
    features: [
      "Unlimited songs",
      "API access",
      "Batch upload",
      "Custom tunings",
      "Dedicated support",
      "Early access to new features",
    ],
    cta: "Contact Us",
    highlighted: false,
    badge: null,
  },
]

interface FaqItem {
  question: string
  answer: string
}

const faqItems: FaqItem[] = [
  {
    question: "What audio formats are supported?",
    answer:
      "TabAI supports MP3, WAV, FLAC, OGG, and M4A files. For best results, use high-quality recordings with clearly audible guitar parts.",
  },
  {
    question: "How accurate are the generated tabs?",
    answer:
      "Accuracy depends on the complexity of the track and recording quality. Clean recordings with a single guitar typically achieve 85-95% accuracy. Multi-instrument mixes are separated first using AI source separation.",
  },
  {
    question: "Can I cancel my subscription at any time?",
    answer:
      "Yes, you can cancel anytime from your account settings. Your access continues until the end of your current billing period.",
  },
  {
    question: "What is the difference between GP5, MIDI, and MusicXML?",
    answer:
      "GP5 files open in Guitar Pro for interactive playback and editing. MIDI is a universal format for DAWs and notation software. MusicXML works with Finale, Sibelius, and MuseScore.",
  },
  {
    question: "Do unused songs roll over to the next month?",
    answer:
      "No, the monthly song allocation resets each billing cycle. Upgrade to Studio for unlimited songs if you need more capacity.",
  },
]

export default function PricingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  const toggleFaq = (index: number) => {
    setOpenFaq((prev) => (prev === index ? null : index))
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <a href="/" className="text-xl font-bold tracking-tight">
              <span className="text-accent">Tab</span>AI
            </a>
            <Badge variant="accent" size="sm">
              Beta
            </Badge>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="/"
              className="text-sm text-gray-400 transition-colors hover:text-white"
            >
              Home
            </a>
            <button className="rounded-lg border border-white/20 px-4 py-1.5 text-sm font-medium text-gray-300 transition-colors hover:bg-white/10">
              Sign In
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-16">
        {/* Hero */}
        <div className="mb-16 text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Simple, transparent{" "}
            <span className="text-accent">pricing</span>
          </h2>
          <p className="mt-4 text-lg text-gray-400">
            Choose the plan that fits your workflow. Upgrade or downgrade
            anytime.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid gap-8 md:grid-cols-3">
          {tiers.map((tier) => (
            <Card
              key={tier.name}
              highlighted={tier.highlighted}
              className="relative flex flex-col"
            >
              {tier.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge variant="accent" size="md">
                    {tier.badge}
                  </Badge>
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white">
                  {tier.name}
                </h3>
                <p className="mt-1 text-sm text-gray-400">{tier.description}</p>
              </div>

              <div className="mb-6">
                <span className="text-4xl font-bold text-white">
                  {tier.price}
                </span>
                <span className="text-sm text-gray-400">{tier.period}</span>
              </div>

              <ul className="mb-8 flex-1 space-y-3">
                {tier.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-2 text-sm text-gray-300"
                  >
                    <svg
                      className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                className={`w-full rounded-xl py-3 text-sm font-semibold transition-opacity hover:opacity-90 ${
                  tier.highlighted
                    ? "bg-accent text-white"
                    : "border border-white/20 text-gray-300 hover:bg-white/10"
                }`}
              >
                {tier.cta}
              </button>
            </Card>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-24">
          <h3 className="mb-8 text-center text-2xl font-bold text-white">
            Frequently Asked Questions
          </h3>

          <div className="mx-auto max-w-2xl space-y-3">
            {faqItems.map((faq, index) => (
              <div
                key={faq.question}
                className="rounded-xl border border-white/10 bg-white/[0.02]"
              >
                <button
                  onClick={() => toggleFaq(index)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-medium text-white"
                >
                  {faq.question}
                  <svg
                    className={`h-4 w-4 flex-shrink-0 text-gray-400 transition-transform ${
                      openFaq === index ? "rotate-180" : ""
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
                {openFaq === index && (
                  <div className="px-5 pb-4 text-sm leading-relaxed text-gray-400">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
