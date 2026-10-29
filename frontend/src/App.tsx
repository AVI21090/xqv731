import { useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, ArrowUpDown, CalendarDays, Gauge, RefreshCcw, TrendingDown, TrendingUp, Wind } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

import { fetchDashboard } from './api'
import type { DashboardResponse } from './types'

const defaultStart = '2026-01-01'
const defaultEnd = '2026-01-31'

function App() {
  const [dateStart, setDateStart] = useState(defaultStart)
  const [dateEnd, setDateEnd] = useState(defaultEnd)
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [meta, setMeta] = useState<DashboardResponse['metadata']>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const dashboard = await fetchDashboard(dateStart, dateEnd)
      setData(dashboard)
      setMeta(dashboard.metadata ?? null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load WindSight data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [dateStart, dateEnd])

  const kpis = useMemo(() => {
    const averageForecast = data?.kpis.average_forecast_generation_mw ?? null
    const averageActual = data?.kpis.average_actual_generation_mw ?? null
    const mae = data?.kpis.mae_mw ?? null
    const rmse = data?.kpis.rmse_mw ?? null
    const matched = data?.kpis.matched_periods ?? null
    return { averageForecast, averageActual, mae, rmse, matched }
  }, [data])

  const backendUnavailable = !loading && !!data && data.status !== 'ok'

  return (
    <div className="min-h-screen bg-[#f3f4f1] text-slate-800">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="border-b border-slate-200 bg-[#f7f8f5] px-4 py-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#1f4d3a] text-white">
                <Wind className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">UK wind analytics</p>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-900">WindSight</h1>
              </div>
            </div>

            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
                <CalendarDays className="h-4 w-4 text-[#1f4d3a]" />
                <input type="date" value={dateStart} onChange={(event) => setDateStart(event.target.value)} className="bg-transparent outline-none" />
              </label>
              <span className="text-slate-400">to</span>
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
                <CalendarDays className="h-4 w-4 text-[#1f4d3a]" />
                <input type="date" value={dateEnd} onChange={(event) => setDateEnd(event.target.value)} className="bg-transparent outline-none" />
              </label>
              <button onClick={() => void load()} className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#1f4d3a] bg-[#1f4d3a] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#173d30]">
                <RefreshCcw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>
        </header>

        <main className="space-y-6 py-6">
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">Decision-window analysis</p>
              <h2 className="text-xl font-semibold text-slate-900">Wind forecast versus actual generation</h2>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
                <Activity className="h-3.5 w-3.5 text-[#1f4d3a]" />
                Source: {meta?.source_url ? <a href={meta.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{meta.source ?? 'Elexon BMRS'}</a> : (meta?.source ?? 'Elexon BMRS')}
              </span>
              {meta?.retrieval_time ? (
                <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
                  <Gauge className="h-3.5 w-3.5 text-[#3b82f6]" />
                  Updated {new Date(meta.retrieval_time).toLocaleString()}
                </span>
              ) : null}
            </div>
          </div>

          {error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <div className="flex items-center gap-2 font-medium"><AlertTriangle className="h-4 w-4" /> Data unavailable</div>
              <p className="mt-2">{error}</p>
            </div>
          ) : null}

          {backendUnavailable ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                <div className="flex items-center gap-2 font-medium"><AlertTriangle className="h-4 w-4" /> {data?.status === 'unavailable' ? 'Live data unavailable' : 'No matched periods'}</div>
              <p className="mt-2">{data?.message ?? 'The backend could not retrieve Elexon data for this range. Values below are intentionally shown as unavailable.'}</p>
            </div>
          ) : null}

          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />
              ))}
            </div>
          ) : null}

          {!loading && data ? (
            <>
              <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <KpiCard title="Avg forecast" value={formatNumber(kpis.averageForecast, 'MW')} icon={<TrendingUp className="h-4 w-4" />} accent="text-[#1f4d3a]" />
                <KpiCard title="Avg actual" value={formatNumber(kpis.averageActual, 'MW')} icon={<TrendingDown className="h-4 w-4" />} accent="text-[#3b82f6]" />
                <KpiCard title="MAE" value={formatNumber(kpis.mae, 'MW')} icon={<ArrowUpDown className="h-4 w-4" />} accent="text-[#0f172a]" />
                <KpiCard title="RMSE" value={formatNumber(kpis.rmse, 'MW')} icon={<Gauge className="h-4 w-4" />} accent="text-[#334155]" />
                <KpiCard title="Matched periods" value={formatCount(kpis.matched)} icon={<CalendarDays className="h-4 w-4" />} accent="text-[#2563eb]" />
              </section>

              <section className="grid gap-6 xl:grid-cols-[2fr_1fr]">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-slate-900">Forecast vs. actual</h3>
                    <span className="text-xs text-slate-500">Half-hourly periods · hourly forecast held across each hour</span>
                  </div>
                  <div className="h-80">
                    {(data.kpis.matched_periods ?? 0) === 0 ? (
                      <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
                        No matched forecast-versus-actual periods are available for the selected range.
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data.series}>
                          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                          <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={24} />
                          <YAxis tick={{ fontSize: 11 }} unit=" MW" />
                          <Tooltip
                            labelFormatter={(value) => `Period: ${value}`}
                            formatter={(value) => [`${Number(Array.isArray(value) ? value[0] ?? 0 : value ?? 0).toFixed(1)} MW`, '']}
                          />
                          <Legend />
                          <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#1f4d3a" strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
                          <Line type="monotone" dataKey="actual" name="Actual" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-900">Accuracy summary</h3>
                  <div className="mt-4 space-y-3 text-sm">
                    <MetricRow label="MAE" value={formatNumber(data.accuracy.mae_mw, 'MW')} />
                    <MetricRow label="RMSE" value={formatNumber(data.accuracy.rmse_mw, 'MW')} />
                    <MetricRow label="Bias" value={formatNumber(data.accuracy.bias_mw, 'MW')} />
                    <MetricRow label="MAPE" value={formatNumber(data.accuracy.mape_pct, '%')} />
                    <MetricRow label="Coverage" value={formatPercent(data.accuracy.coverage_pct)} />
                    <MetricRow label="Matched periods" value={formatCount(data.accuracy.matched_periods)} />
                  </div>
                  <p className="mt-4 rounded-xl border border-[#dfe7e0] bg-[#f4f8f5] p-3 text-xs leading-6 text-slate-600">
                    The app selects the latest forecast published by 12:00 UTC on the day before delivery. WINDFOR is hourly, so each hourly forecast is applied to its two half-hourly FUELHH periods. This documented assignment assumption is not an official market purchasing deadline.
                  </p>
                </div>
              </section>

              <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-900">Largest forecast errors</h3>
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead className="border-b border-slate-200 text-slate-500">
                        <tr>
                          <th className="py-2 pr-4">Period</th>
                          <th className="py-2 pr-4">Forecast</th>
                          <th className="py-2 pr-4">Actual</th>
                          <th className="py-2 pr-4">Error</th>
                          <th className="py-2 pr-4">Abs</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.largest_errors.length === 0 ? (
                          <tr><td className="py-3 text-slate-500" colSpan={5}>No error records available.</td></tr>
                        ) : (
                          data.largest_errors.map((row) => (
                            <tr key={`${row.target_time}-${row.publish_time}`} className="border-b border-slate-100">
                              <td className="py-2 pr-4">{new Date(row.target_time).toLocaleString()}</td>
                              <td className="py-2 pr-4">{Number(row.forecast_generation).toFixed(1)}</td>
                              <td className="py-2 pr-4">{Number(row.actual_generation).toFixed(1)}</td>
                              <td className="py-2 pr-4">{Number(row.signed_error).toFixed(1)}</td>
                              <td className="py-2 pr-4 font-medium">{Number(row.absolute_error).toFixed(1)}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-900">Publication history</h3>
                  <div className="mt-4 space-y-3">
                    {data.forecast_history.length === 0 ? (
                      <p className="text-sm text-slate-500">No forecast history is available for the selected period.</p>
                    ) : (
                      <>
                      <p className="text-xs text-slate-500">Selected period: {new Date(data.forecast_history[0].startTime).toLocaleString()}</p>
                      {data.forecast_history.map((item) => (
                        <div key={`${item.startTime}-${item.publishTime}`} className={`rounded-xl border p-3 ${item.selected ? 'border-[#1f4d3a] bg-[#edf4f0]' : 'border-slate-200 bg-slate-50'}`}>
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs uppercase tracking-wide text-slate-500">{new Date(item.publishTime).toLocaleString()}</span>
                            {item.selected ? <span className="rounded-full bg-[#1f4d3a] px-2 py-0.5 text-[10px] font-semibold text-white">Selected</span> : null}
                          </div>
                          <p className="mt-2 text-sm font-medium text-slate-800">{Number(item.generation).toFixed(1)} MW</p>
                        </div>
                      ))}
                      </>
                    )}
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between gap-4">
                  <h3 className="text-lg font-semibold text-slate-900">Data quality and methodology</h3>
                </div>
                <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2 xl:grid-cols-4">
                  <InfoPill label="Decision cutoff assumption" value={meta?.selected_cutoff_assumption ?? 'Latest forecast published no later than 12:00 UTC on the day before delivery.'} />
                  <InfoPill label="Selected range" value={`${dateStart} to ${dateEnd}`} />
                  <InfoPill label="Missing actuals" value={String(data.metadata?.missing_actual_records ?? 0)} />
                  <InfoPill label="Missing forecasts" value={String(data.metadata?.missing_forecast_records ?? 0)} />
                </div>
              </section>
            </>
          ) : null}
        </main>
      </div>
    </div>
  )
}

function KpiCard({ title, value, icon, accent }: { title: string; value: string; icon: React.ReactNode; accent: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between text-slate-500">
        <span className="text-xs font-medium uppercase tracking-[0.12em]">{title}</span>
        <span className={accent}>{icon}</span>
      </div>
      <p className="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
    </div>
  )
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800">{value}</span>
    </div>
  )
}

function InfoPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="text-[10px] uppercase tracking-[0.12em] text-slate-500">{label}</div>
      <div className="mt-2 text-sm font-medium text-slate-700">{value}</div>
    </div>
  )
}

function formatNumber(value: number | null | undefined, unit: string) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  return `${Number(value).toFixed(1)} ${unit}`
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  return `${Number(value).toFixed(1)}%`
}

function formatCount(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  return String(value)
}

export default App
