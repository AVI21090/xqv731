import type { DashboardResponse } from './types'

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchDashboard(dateStart: string, dateEnd: string): Promise<DashboardResponse> {
  const res = await fetch(`${baseUrl}/api/dashboard?start_date=${dateStart}&end_date=${dateEnd}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to load dashboard data')
  }
  return res.json() as Promise<DashboardResponse>
}

