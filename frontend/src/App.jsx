import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  Activity,
  Ambulance,
  ArrowRightLeft,
  BadgeAlert,
  BarChart3,
  Bell,
  Clock3,
  FileText,
  Loader2,
  MapPin,
  Radio,
  ShieldAlert,
  Siren,
  Truck,
  Users,
  Zap,
} from 'lucide-react'
import TrafficMap from './components/TrafficMap'

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
const API_URL = `${API_BASE_URL}/api/analyze_event`
const FEED_URL = `${API_BASE_URL}/api/live_events`
const LEGACY_FEED_URL = `${API_BASE_URL}/api/event_feed`
const SOURCE_HEALTH_URL = `${API_BASE_URL}/api/source_health`
const FEATURE_URL = `${API_BASE_URL}/api/feature_report`

const SEVERITY_STYLES = {
  Critical: {
    badge: 'bg-red-500/15 text-red-300 ring-red-500/30',
    chip: 'text-red-300',
    glow: 'shadow-red-500/20',
  },
  High: {
    badge: 'bg-orange-500/15 text-orange-300 ring-orange-500/30',
    chip: 'text-orange-300',
    glow: 'shadow-orange-500/20',
  },
  Medium: {
    badge: 'bg-yellow-500/15 text-yellow-300 ring-yellow-500/30',
    chip: 'text-yellow-300',
    glow: 'shadow-yellow-500/20',
  },
  Low: {
    badge: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    chip: 'text-emerald-300',
    glow: 'shadow-emerald-500/20',
  },
}

function App() {
  const [inputText, setInputText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [feedLoading, setFeedLoading] = useState(false)
  const [feed, setFeed] = useState([])
  const [featureReport, setFeatureReport] = useState(null)
  const [overview, setOverview] = useState(null)
  const [sourceHealth, setSourceHealth] = useState(null)
  const [timelineMinutes, setTimelineMinutes] = useState(60)
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

  const loadEventFeed = async () => {
    setFeedLoading(true)
    try {
      const primaryResponse = await fetch(FEED_URL)
      const response = primaryResponse.ok ? primaryResponse : await fetch(LEGACY_FEED_URL)
      if (!response.ok) {
        throw new Error(`Feed load failed (${response.status})`)
      }
      const data = await response.json()
      setFeed(data.feed ?? [])
    } catch (err) {
      setFeed([])
    } finally {
      setFeedLoading(false)
    }
  }

  useEffect(() => {
    if (feed.length === 0 && !feedLoading) {
      loadEventFeed()
    }
  }, [])

  useEffect(() => {
    const loadFeatureReport = async () => {
      try {
        const response = await fetch(FEATURE_URL)
        if (!response.ok) return
        const data = await response.json()
        setFeatureReport(data)
      } catch (err) {
        setFeatureReport(null)
      }
    }

    loadFeatureReport()
  }, [])

  useEffect(() => {
    const loadOverview = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/command_overview`)
        if (!response.ok) return
        const data = await response.json()
        setOverview(data)
      } catch (err) {
        setOverview(null)
      }
    }

    loadOverview()
  }, [])

  useEffect(() => {
    const loadSourceHealth = async () => {
      try {
        const response = await fetch(SOURCE_HEALTH_URL)
        if (!response.ok) return
        const data = await response.json()
        setSourceHealth(data)
      } catch (err) {
        setSourceHealth(null)
      }
    }

    loadSourceHealth()
  }, [])

  const extraction = result?.entities ?? result?.extraction ?? {}
  const predictions = result?.predictions ?? {}
  const historicalEvidence = result?.historical_evidence ?? {}
  const routeOptimization = result?.route_optimization ?? {}
  const actionPlan = result?.action_plan ?? {}
  const routeRationale = routeOptimization.route_rationale ?? {}
  const explainability = extraction.explainability ?? []

  const predictedDelay = predictions.predicted_delay_mins ?? 0
  const predictedClearance = predictions.predicted_clearance_mins ?? 0
  const predictionConfidence = predictions.prediction_confidence ?? predictions.model_score ?? 0
  const congestionScore = Math.min(100, Math.round((predictedDelay + (actionPlan.priority_level === 'Critical' ? 30 : actionPlan.priority_level === 'High' ? 20 : 10)) / 2))
  const severity = actionPlan.priority_level || extraction.severity || 'Low'
  const severityStyle = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.Low
  const activeAlerts = useMemo(() => {
    const alerts = [
      severity === 'Critical' ? 'Critical incident active' : null,
      routeOptimization.recommended_closures?.length ? 'Road closure recommended' : null,
      predictedDelay > 45 ? 'Congestion escalation likely' : null,
      historicalEvidence.similar_incidents > 0 ? 'Historical precedent found' : null,
      extraction.expected_congestion && extraction.expected_congestion !== 'unknown' ? `Expected congestion: ${extraction.expected_congestion}` : null,
    ]
    return alerts.filter(Boolean)
  }, [historicalEvidence.similar_incidents, predictedDelay, routeOptimization.recommended_closures?.length, severity])

  const liveFeedCards = useMemo(() => {
    const normalized = feed.slice(0, 4).map((item, index) => ({
      ...item,
      key: `${item.source}-${index}`,
      severity: index === 0 ? 'Critical' : index === 1 ? 'High' : index === 2 ? 'Medium' : 'Low',
      icon: index === 0 ? Siren : index === 1 ? Users : index === 2 ? Bell : Radio,
      summary: item.description ?? item.text ?? '',
      source_name: item.source_name ?? item.source,
      source_type: item.source_type ?? 'event',
      event_category: item.event_category ?? item.source,
      confidence_score: item.confidence_score ?? item.reliability_score ?? 0,
      verification_status: item.verification_status ?? 'Verified',
      data_origin: item.data_origin ?? 'Simulated',
      original_link: item.original_link ?? item.source_url,
    }))
    return normalized
  }, [feed])

  const routeCards = [
    {
      label: 'Route A',
      route: routeOptimization.route_a,
      percent: routeOptimization.split_percentages?.[0] ?? 0,
      color: 'text-emerald-300',
    },
    {
      label: 'Route B',
      route: routeOptimization.route_b,
      percent: routeOptimization.split_percentages?.[1] ?? 0,
      color: 'text-orange-300',
    },
    {
      label: 'Route C',
      route: routeOptimization.route_c,
      percent: routeOptimization.split_percentages?.[2] ?? 0,
      color: 'text-sky-300',
    },
  ]

  const matchedCorridors = historicalEvidence.matched_corridors ?? []
  const matchedLocations = historicalEvidence.matched_locations ?? []
  const topMatches = historicalEvidence.top_matches ?? []
  const topDiversions = routeOptimization.top_diversions ?? []
  const datasetRows = featureReport?.row_count ?? 0
  const datasetColumns = featureReport?.column_count ?? 0

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(248,113,113,0.18),_transparent_32%),radial-gradient(circle_at_80%_20%,_rgba(249,115,22,0.14),_transparent_22%),linear-gradient(180deg,_#04070d_0%,_#0a1020_100%)] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:64px_64px] opacity-40" />

      <div className="relative mx-auto flex min-h-screen max-w-[1900px] flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8">
        <header className="rounded-3xl border border-white/10 bg-slate-950/65 p-5 shadow-2xl shadow-black/30 backdrop-blur-xl lg:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-4">
              <div className="rounded-2xl bg-red-500/15 p-3 ring-1 ring-red-400/30">
                <BarChart3 className="h-8 w-8 text-red-300" />
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.45em] text-red-200/80">ASTraM</p>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
                  AI Traffic Intelligence Command Center
                </h1>
                <p className="mt-1 max-w-3xl text-sm text-slate-300">
                  Bengaluru Traffic Police operational dashboard for live incident understanding, diversion routing, and deployment planning.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:min-w-[640px]">
              <MetricChip label="Incident Status" value={severity} tone={severityStyle.chip} />
              <MetricChip label="Congestion Score" value={`${congestionScore}/100`} tone="text-orange-200" />
              <MetricChip label="Predicted Delay" value={`${predictedDelay} min`} tone="text-red-200" />
              <MetricChip label="Clearance Time" value={`${predictedClearance} min`} tone="text-emerald-200" />
              <MetricChip label="Prediction Confidence" value={`${Math.round(predictionConfidence)}%`} tone="text-sky-200" />
              <MetricChip label="Impact Radius" value={`${Math.round(extraction.impact_radius_meters ?? 0)} m`} tone="text-amber-200" />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/10 pt-4 text-xs text-slate-300">
            <span className="rounded-full bg-slate-800/80 px-3 py-1 ring-1 ring-white/10">Active Alerts</span>
            {activeAlerts.length ? activeAlerts.map((alert) => (
              <span key={alert} className="rounded-full bg-red-500/15 px-3 py-1 text-red-100 ring-1 ring-red-400/20">
                {alert}
              </span>
            )) : <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-emerald-100 ring-1 ring-emerald-400/20">No active alerts</span>}
          </div>
        </header>

        <section className="grid grid-cols-2 gap-3 rounded-3xl border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/25 backdrop-blur-xl xl:grid-cols-6">
          <MetricChip label="Active Incidents" value={overview?.active_incidents ?? 0} tone="text-slate-50" />
          <MetricChip label="Critical" value={overview?.critical_incidents ?? 0} tone="text-red-200" />
          <MetricChip label="High Severity" value={overview?.high_severity_incidents ?? 0} tone="text-orange-200" />
          <MetricChip label="Average Delay" value={`${overview?.average_delay_mins ?? 0} min`} tone="text-amber-200" />
          <MetricChip label="Average Clearance" value={`${overview?.average_clearance_mins ?? 0} min`} tone="text-emerald-200" />
          <MetricChip label="Traffic Status" value={overview?.current_traffic_status ?? 'Normal'} tone="text-sky-200" />
        </section>

        <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/25 backdrop-blur-xl">
          <SectionHeader title="DATA SOURCE HEALTH" subtitle="Real RSS/public feeds and fallback status" icon={Activity} />
          <div className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
            <MetricChip label="Real Sources Active" value={sourceHealth?.real_sources_active ?? 0} tone="text-emerald-200" />
            <MetricChip label="Failed Sources" value={sourceHealth?.failed_sources ?? 0} tone="text-red-200" />
            <MetricChip label="Events Collected" value={sourceHealth?.events_collected ?? 0} tone="text-sky-200" />
            <MetricChip label="Last Refresh" value={formatTimestamp(sourceHealth?.last_refresh)} tone="text-amber-200" />
          </div>
        </section>

        <div className="grid flex-1 grid-cols-1 gap-5 xl:grid-cols-[360px_minmax(0,1fr)_360px]">
          <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <SectionHeader title="LIVE EVENT INTELLIGENCE" subtitle="Traffic Police Feed · Citizen Reports · Social Media · News Alerts" icon={Radio} />

            <div className="mt-4 space-y-3">
              {feedLoading && <LoadingStrip label="Loading live feed simulation..." />}
              {liveFeedCards.map((item) => {
                const Icon = item.icon
                return (
                  <div key={item.key} className="rounded-2xl border border-white/10 bg-slate-900/80 p-4 transition duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-slate-900">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-white/5 p-2 ring-1 ring-white/10">
                          <Icon className="h-4 w-4 text-red-300" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-50">{item.source}</p>
                          <p className="text-xs text-slate-400">{formatTimestamp(item.timestamp)}</p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <SeverityBadge severity={item.severity} />
                        <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] ring-1 ${item.data_origin === 'Real Data' ? 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/20' : 'bg-slate-500/15 text-slate-200 ring-slate-400/20'}`}>
                          {item.data_origin ?? 'Simulated'}
                        </span>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.18em] text-slate-300">
                      <span className="rounded-full bg-white/5 px-2 py-1 ring-1 ring-white/10">{item.source_type ?? 'unknown'}</span>
                      <span className="rounded-full bg-white/5 px-2 py-1 ring-1 ring-white/10">{item.source_name ?? item.source ?? 'source'}</span>
                      <span className="rounded-full bg-white/5 px-2 py-1 ring-1 ring-white/10">{item.event_category ?? 'event'}</span>
                      <span className="rounded-full bg-white/5 px-2 py-1 ring-1 ring-white/10">Confidence {item.confidence_score ?? item.reliability_score ?? 0}%</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{item.summary}</p>
                    <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-400">
                      <span>{item.verification_status ?? 'Verified'}</span>
                      {item.original_link ? (
                        <a href={item.original_link} target="_blank" rel="noreferrer" className="text-sky-300 hover:text-sky-200">
                          View Original Source
                        </a>
                      ) : (
                        <span>Source link unavailable</span>
                      )}
                    </div>
                  </div>
                )
              })}
              {!feedLoading && liveFeedCards.length === 0 && (
                <EmptyState title="Live feed unavailable" description="The backend feed simulation will populate this panel." />
              )}
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
              <div className="flex items-center gap-2 text-slate-200">
                <Radio className="h-4 w-4 text-red-300" />
                <h3 className="text-sm font-semibold uppercase tracking-[0.2em]">Input Feed</h3>
              </div>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder='e.g. "A truck overturned near Silk Board Junction."'
                rows={6}
                className="mt-3 w-full resize-none rounded-2xl border border-white/10 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-red-400/60 focus:ring-2 focus:ring-red-500/20"
              />
              {error && <div className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={loading}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-red-500 via-orange-500 to-amber-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.18em] text-slate-950 shadow-lg shadow-orange-500/25 transition hover:from-red-400 hover:to-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? <><Loader2 className="h-4 w-4 animate-spin" />Running analysis...</> : <><Zap className="h-4 w-4" />Analyze Incident</>}
              </button>
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">Explainability</h3>
              <div className="mt-3 space-y-2">
                {explainability.length ? explainability.map((item) => (
                  <div key={item} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200">
                    {item}
                  </div>
                )) : <EmptyState title="No explainability yet" description="Structured evidence will appear after analysis." compact />}
              </div>
            </div>
          </section>

          <section className="flex min-h-0 flex-col gap-5 rounded-3xl border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <SectionHeader title="COMMAND MAP" subtitle="Incident epicenter · ripple zones · heatmap · route diversions" icon={MapPin} />
            <div className="min-h-[620px] flex-1 overflow-hidden rounded-3xl border border-white/10 bg-slate-900/80 p-2">
              <TrafficMap result={result} timelineMinutes={timelineMinutes} />
            </div>
          </section>

          <aside className="rounded-3xl border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <SectionHeader title="OPERATIONAL ACTION PLAN" subtitle="Police deployment · barricades · tow support" icon={ShieldAlert} />

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <ActionCard label="Police Officers Required" value={actionPlan.officers_required ?? 0} icon={Users} tone="text-red-200" />
              <ActionCard label="Barricades Required" value={actionPlan.barricades_required ?? 0} icon={BadgeAlert} tone="text-orange-200" />
              <ActionCard label="Tow Trucks Required" value={actionPlan.tow_trucks_required ?? 0} icon={Truck} tone="text-amber-200" />
              <ActionCard label="Priority Level" value={actionPlan.priority_level ?? 'Low'} icon={Siren} tone={severityStyle.chip} />
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">Deployment Zones</h3>
              <div className="mt-3 space-y-2">
                {(actionPlan.deployment_zones ?? []).length ? actionPlan.deployment_zones.map((zone) => (
                  <div key={zone} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200">
                    <ArrowRightLeft className="h-4 w-4 text-red-300" />
                    {zone}
                  </div>
                )) : <EmptyState title="No deployment zones" description="Operational zones will appear after analysis." compact />}
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">
                <Clock3 className="h-4 w-4 text-orange-300" />
                Clearance Summary
              </div>
              <p className="mt-2 text-3xl font-semibold text-slate-50">{predictedClearance} min</p>
              <p className="mt-1 text-sm text-slate-400">Model-derived clearance prediction from cleaned dataset training.</p>
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">Route Rationale</h3>
              <div className="mt-3 space-y-2 text-sm text-slate-300">
                <p>Matched corridor: {routeRationale.location_match || 'Pending'}</p>
                <p>Historical similarity: {routeRationale.historical_similarity ?? 0}%</p>
                <p>Top diversions: {topDiversions.length ? topDiversions.join(', ') : 'Pending'}</p>
                <p>Peak-hour impact: {extraction.expected_congestion || 'unknown'}</p>
                <p>Why: {routeRationale.reason || 'Historical corridor risk and ripple zones drive the diversion plan.'}</p>
              </div>
            </div>
          </aside>
        </div>

        <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
          <Panel title="Historical Evidence" icon={Activity}>
            <div className="grid grid-cols-2 gap-3">
              <StatTile label="Similar Incidents" value={historicalEvidence.similar_incidents ?? 0} />
              <StatTile label="Average Delay" value={`${historicalEvidence.average_delay ?? 0} min`} />
              <StatTile label="Average Clearance" value={`${historicalEvidence.average_clearance_time ?? 0} min`} />
              <StatTile label="Confidence" value={`${historicalEvidence.confidence ?? 0}%`} />
            </div>
            <p className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-3 text-sm leading-6 text-slate-300">
              {historicalEvidence.common_response_strategy || 'Historical rationale will appear after analysis.'}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <StatTile label="Matched Corridors" value={String(matchedCorridors.length)} />
              <StatTile label="Matched Locations" value={String(matchedLocations.length)} />
            </div>
            <div className="mt-3 space-y-2">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Most Common Resolution</p>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
                {historicalEvidence.most_common_resolution || 'Pending'}
              </div>
            </div>
            <div className="mt-3 space-y-2">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Top Historical Matches</p>
              <div className="space-y-2">
                {(topMatches.length ? topMatches : []).map((match, index) => (
                  <div key={`${match.location}-${index}`} className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-slate-300">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-100">{match.location}</span>
                      <span className="text-xs text-slate-400">{Math.round(match.similarity_score ?? 0)} score</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">{match.corridor} · {match.priority} · {match.clearance_mins} min clearance</p>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="Traffic Diversion Plan" icon={ArrowRightLeft}>
            <div className="space-y-3">
              {routeCards.map((route) => (
                <div key={route.label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{route.label}</p>
                      <p className={`mt-1 text-lg font-semibold ${route.color}`}>{route.route || 'Pending'}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-950/80 px-3 py-2 text-xl font-semibold text-slate-50 ring-1 ring-white/10">{route.percent}%</div>
                  </div>
                </div>
              ))}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <MiniList title="Recommended Closures" items={routeOptimization.recommended_closures ?? []} />
                <MiniList title="Diversion Points" items={routeOptimization.diversion_points ?? []} />
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                Route Confidence Score: <span className="font-semibold text-slate-50">{routeOptimization.route_confidence_score ?? 0}%</span>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                Top Diversions: <span className="font-semibold text-slate-50">{topDiversions.join(' · ') || 'Pending'}</span>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                Road Closures: <span className="font-semibold text-slate-50">{(routeOptimization.recommended_closures ?? []).join(' · ') || 'Pending'}</span>
              </div>
            </div>
          </Panel>

          <Panel title="AI Incident Understanding" icon={FileText}>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <EntityRow label="Incident Type" value={extraction.incident_type} />
              <EntityRow label="Location" value={extraction.location} />
              <EntityRow label="Severity" value={extraction.severity} />
              <EntityRow label="Vehicle Type" value={extraction.vehicle_type} />
              <EntityRow label="Crowd Size" value={extraction.crowd_size} />
              <EntityRow label="Lanes Blocked" value={String(extraction.lanes_blocked ?? 0)} />
              <EntityRow label="Impact Radius" value={`${extraction.impact_radius_meters ?? 0} m`} />
              <EntityRow label="Expected Congestion" value={extraction.expected_congestion} />
              <EntityRow label="Expected Impact" value={extraction.expected_impact} />
            </div>
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Why this recommendation?</p>
              <div className="mt-3 space-y-2">
                {(predictions.reasoning ?? []).map((reason) => (
                  <div key={reason} className="rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2">{reason}</div>
                ))}
              </div>
            </div>
          </Panel>
        </section>

        <section className="grid grid-cols-1 gap-5 xl:grid-cols-[2fr_1fr]">
          <Panel title="Dataset Signals" icon={BarChart3}>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="Rows" value={String(datasetRows)} />
              <StatTile label="Columns" value={String(datasetColumns)} />
              <StatTile label="Used Fields" value={String(featureReport?.used_fields?.length ?? 0)} />
              <StatTile label="Unused Fields" value={String(featureReport?.unused_fields?.length ?? 0)} />
            </div>
            <div className="mt-4 space-y-2 text-sm text-slate-300">
              <p className="font-semibold text-slate-100">Top corridor risk</p>
              {(featureReport?.top_corridors ?? []).slice(0, 4).map((item) => (
                <div key={item.corridor} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                  {item.corridor} · {item.incident_count} incidents · {item.average_clearance_mins} min avg clearance
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="AI Understanding" icon={FileText}>
            <div className="space-y-3 text-sm text-slate-300">
              {(extraction.explainability ?? []).length ? extraction.explainability.map((item) => (
                <div key={item} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">{item}</div>
              )) : <EmptyState title="Awaiting analysis" description="Explainability will appear here after you analyze an incident." compact />}
            </div>
          </Panel>
        </section>

        <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.4fr_1fr]">
          <Panel title="Ripple Timeline" icon={Clock3}>
            <div className="flex flex-wrap gap-2">
              {[0, 15, 30, 45, 60].map((minute) => (
                <button
                  key={minute}
                  type="button"
                  onClick={() => setTimelineMinutes(minute)}
                  className={`rounded-full px-4 py-2 text-xs uppercase tracking-[0.18em] ring-1 transition ${timelineMinutes === minute ? 'bg-red-500/20 text-red-100 ring-red-400/30' : 'bg-white/5 text-slate-300 ring-white/10 hover:bg-white/10'}`}
                >
                  {minute === 0 ? 'Current' : `${minute} mins`}
                </button>
              ))}
            </div>
            <p className="mt-4 text-sm text-slate-400">Move through time to inspect congestion propagation, diversion pressure, and ripple zones.</p>
          </Panel>

          <Panel title="Command Pulse" icon={ShieldAlert}>
            <div className="grid grid-cols-2 gap-3">
              <StatTile label="Priority" value={actionPlan.priority_level ?? 'Low'} />
              <StatTile label="Officers" value={String(actionPlan.officers_required ?? 0)} />
              <StatTile label="Barricades" value={String(actionPlan.barricades_required ?? 0)} />
              <StatTile label="Tow Trucks" value={String(actionPlan.tow_trucks_required ?? 0)} />
            </div>
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Why these values?</p>
              <div className="mt-3 space-y-2">
                {(actionPlan.rationale ?? []).map((reason) => (
                  <div key={reason} className="rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2">{reason}</div>
                ))}
              </div>
            </div>
          </Panel>
        </section>
      </div>
    </div>
  )
}

function SectionHeader({ title, subtitle, icon: Icon }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
      <div>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.35em] text-slate-400">
          <Icon className="h-4 w-4 text-red-300" />
          {title}
        </div>
        <p className="mt-2 text-sm text-slate-400">{subtitle}</p>
      </div>
      <div className="rounded-full bg-red-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-red-200 ring-1 ring-red-400/20">
        Live
      </div>
    </div>
  )
}

function MetricChip({ label, value, tone }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  )
}

function ActionCard({ label, value, icon: Icon, tone }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg shadow-black/20">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{label}</p>
        <Icon className={`h-5 w-5 ${tone}`} />
      </div>
      <p className={`mt-4 text-3xl font-semibold ${tone}`}>{value}</p>
    </div>
  )
}

function StatTile({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-50">{value}</p>
    </div>
  )
}

function EntityRow({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <p className="mt-2 text-base font-medium capitalize text-slate-50">{value || 'Unknown'}</p>
    </div>
  )
}

function MiniList({ title, items }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length ? items.map((item) => (
          <div key={item} className="rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-slate-200">
            {item}
          </div>
        )) : <p className="text-sm text-slate-500">No data yet.</p>}
      </div>
    </div>
  )
}

function SeverityBadge({ severity }) {
  const config = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.Low
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ring-1 ${config.badge}`}>
      {severity}
    </span>
  )
}

function EmptyState({ title, description, compact = false }) {
  return (
    <div className={`rounded-2xl border border-dashed border-white/10 bg-white/5 ${compact ? 'p-3' : 'p-4'}`}>
      <p className="text-sm font-medium text-slate-200">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
    </div>
  )
}

function LoadingStrip({ label }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
      <Loader2 className="h-4 w-4 animate-spin text-red-300" />
      {label}
    </div>
  )
}

function Panel({ title, icon: Icon, children }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-4 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.35em] text-slate-400">
        <Icon className="h-4 w-4 text-red-300" />
        {title}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function formatTimestamp(timestamp) {
  if (!timestamp) return 'Live'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default App
