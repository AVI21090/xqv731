export type SeriesPoint = {
  time: string
  forecast: number | null
  actual: number | null
  error: number | null
}

export type DashboardResponse = {
  status: 'ok' | 'unavailable' | 'empty'
  source?: string | null
  message?: string | null
  retrieval_time?: string | null
  selected_range?: string | null
  metadata?: {
    source?: string | null
    source_url?: string | null
    status?: string
    retrieval_time?: string | null
    coverage_start?: string | null
    coverage_end?: string | null
    missing_actual_records?: number
    missing_forecast_records?: number
    records_returned?: number
    valid_records?: number
    upstream_available?: boolean
    upstream_error?: string | null
    actual_endpoint?: string | null
    forecast_endpoint?: string | null
    selected_cutoff_assumption?: string
  } | null
  kpis: {
    average_forecast_generation_mw?: number | null
    average_actual_generation_mw?: number | null
    mae_mw?: number | null
    rmse_mw?: number | null
    matched_periods?: number | null
  }
  series: SeriesPoint[]
  accuracy: {
    mae_mw?: number | null
    rmse_mw?: number | null
    bias_mw?: number | null
    mape_pct?: number | null
    matched_periods?: number
    coverage_pct?: number
  }
  largest_errors: Array<{
    target_time: string
    forecast_generation: number
    actual_generation: number
    signed_error: number
    absolute_error: number
    publish_time: string
  }>
  forecast_history: Array<{
    startTime: string
    publishTime: string
    generation: number
    selected: boolean
  }>
}
