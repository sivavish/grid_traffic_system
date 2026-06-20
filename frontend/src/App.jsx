import { useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Clock,
  Loader2,
  MapPin,
  Radio,
  Shield,
  Truck,
  Zap,
} from 'lucide-react'
import TrafficMap from './components/TrafficMap'

const API_URL = 'http://127.0.0.1:8000/api/analyze_event'

function App() {
  const [inputText, setInputText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAnalyze = async () => {
    if (!inputText.trim()) {
      setError('Please enter a feed message to analyze.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText.trim() }),
      })

      if (!response.ok) {
        throw new Error(`Analysis failed (${response.status})`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setResult(null)
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to reach the ASTraM backend. Ensure FastAPI is running on port 8000.',
      )
    } finally {
      setLoading(false)
    }
  }

  const predictedDelay = result?.predictions?.predicted_delay_mins ?? 0
  const isHighDelay = predictedDelay > 45

  const resourceCards = result
    ? [
        {
          label: 'Predicted Delay',
          value: `${predictedDelay} min`,
          icon: Clock,
          accent: isHighDelay ? 'text-red-400' : 'text-emerald-400',
          glow: isHighDelay ? 'shadow-red-500/20' : 'shadow-emerald-500/20',
        },
        {
          label: 'Police Required',
          value: result.predictions.police_required,
          icon: Shield,
          accent: 'text-cyan-400',
          glow: 'shadow-cyan-500/20',
        },
        {
          label: 'Barricades',
          value: result.predictions.barricades,
          icon: AlertTriangle,
          accent: 'text-blue-400',
          glow: 'shadow-blue-500/20',
        },
        {
          label: 'Tow Trucks',
          value: result.predictions.tow_trucks,
          icon: Truck,
          accent: 'text-emerald-400',
          glow: 'shadow-emerald-500/20',
        },
      ]
    : []

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_45%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.08),_transparent_40%)]" />

      <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-10 border-b border-slate-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-cyan-500/10 p-2 ring-1 ring-cyan-400/30">
              <BarChart3 className="h-6 w-6 text-cyan-400" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-cyan-400/80">
                Bengaluru Traffic Police
              </p>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                ASTraM // Event-Driven Traffic Intelligence
              </h1>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-1">
            <section className="rounded-2xl border border-slate-800 bg-slate-800/60 p-6 shadow-xl shadow-black/20 backdrop-blur">
              <div className="mb-4 flex items-center gap-2">
                <Radio className="h-5 w-5 text-emerald-400" />
                <h2 className="text-lg font-medium text-slate-100">
                  Live Feed Ingestion
                </h2>
              </div>
              <p className="mb-4 text-sm text-slate-400">
                Live Social/Radio Feed
              </p>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder='e.g. "Heavy truck breakdown reported near HSR Layout junction..."'
                rows={8}
                className="w-full resize-none rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-cyan-500/60 focus:ring-2 focus:ring-cyan-500/20"
              />

              {error && (
                <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                  {error}
                </div>
              )}

              <button
                type="button"
                onClick={handleAnalyze}
                disabled={loading}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 px-5 py-3 text-sm font-semibold uppercase tracking-wider text-slate-950 shadow-lg shadow-cyan-500/25 transition hover:from-cyan-400 hover:to-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing Feed...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    Execute Analysis
                  </>
                )}
              </button>
            </section>

            {result && !loading && (
              <section className="rounded-2xl border border-slate-800 bg-slate-800/60 p-6 shadow-xl shadow-black/20">
                <h2 className="mb-4 text-lg font-medium text-slate-100">
                  Extraction Details
                </h2>
                <div className="space-y-4">
                  <DetailCard
                    label="Incident Type"
                    value={result.extraction.incident_type}
                  />
                  <DetailCard
                    label="Location"
                    value={result.extraction.location}
                    icon={MapPin}
                  />
                  <DetailCard
                    label="Severity"
                    value={result.extraction.severity}
                    highlight
                  />
                </div>
              </section>
            )}
          </div>

          <div className="space-y-6 lg:col-span-2">
            {loading && (
              <div className="flex min-h-[120px] items-center justify-center rounded-2xl border border-slate-800 bg-slate-800/40">
                <div className="flex items-center gap-3 text-cyan-300">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span>Running NLP, ML, and graph engines...</span>
                </div>
              </div>
            )}

            {result && !loading && (
              <section className="rounded-2xl border border-slate-800 bg-slate-800/60 p-6 shadow-xl shadow-black/20">
                <h2 className="mb-4 text-lg font-medium text-slate-100">
                  Resource Action Plan
                </h2>
                <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
                  {resourceCards.map((card) => {
                    const Icon = card.icon
                    return (
                      <div
                        key={card.label}
                        className={`rounded-xl border border-slate-700 bg-slate-900/70 p-4 shadow-lg ${card.glow}`}
                      >
                        <div className="mb-3 flex items-center justify-between">
                          <span className="text-xs uppercase tracking-wider text-slate-400">
                            {card.label}
                          </span>
                          <Icon className={`h-4 w-4 ${card.accent}`} />
                        </div>
                        <p className={`text-2xl font-semibold ${card.accent}`}>
                          {card.value}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </section>
            )}

            <section className="rounded-2xl border border-slate-800 bg-slate-800/60 p-4 shadow-xl shadow-black/20">
              <div className="mb-3 flex items-center justify-between px-2">
                <h2 className="text-lg font-medium text-slate-100">
                  Spatio-Temporal Ripple Map
                </h2>
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
                    Epicenter
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-orange-500" />
                    Ripple Zone
                  </span>
                </div>
              </div>
              <div className="h-[500px] overflow-hidden rounded-xl border border-slate-700">
                <TrafficMap result={result} />
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

function DetailCard({ label, value, icon: Icon, highlight = false }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-3">
      <p className="mb-1 text-xs uppercase tracking-wider text-slate-400">
        {label}
      </p>
      <div className="flex items-center gap-2">
        {Icon && <Icon className="h-4 w-4 text-cyan-400" />}
        <p
          className={`text-base font-medium capitalize ${
            highlight ? 'text-emerald-400' : 'text-slate-100'
          }`}
        >
          {value}
        </p>
      </div>
    </div>
  )
}

export default App
