
import type { DashboardResponse } from './types'

const baseUrl = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export async function fetchDashboard(
  dateStart: string,
  dateEnd: string,
  signal?: AbortSignal,
): Promise<DashboardResponse> {
  if (!dateStart || !dateEnd || dateStart > dateEnd) {
    throw new Error('Please select a valid date range.')
  }

  const params = new URLSearchParams({
    start_date: dateStart,
    end_date: dateEnd,
  })

  const res = await fetch(
    `${baseUrl}/api/dashboard?${params.toString()}`,
    { signal },
  )

  if (!res.ok) {
    const text = await res.text()
    throw new Error(
      text || `Failed to load dashboard data (${res.status})`,
    )
  }

  return (await res.json()) as DashboardResponse
}
