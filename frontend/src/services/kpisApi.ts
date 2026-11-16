import { authHeaders } from './authApi'

const API_ORIGIN = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export interface GlobalKpi {
  promedio_global: number
  total_registros: number
  periodo_actual: string | null
  comparativo_porcentual: number | null
}

interface FilterOptions {
  valores: string[]
  total: number
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_ORIGIN}/api${path}`, {
      headers: authHeaders(),
      signal,
    })
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === 'AbortError') throw reason
    throw new Error('No fue posible conectarse con la API.')
  }

  if (!response.ok) {
    let detail = `La API respondió con el estado ${response.status}.`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // Keep the HTTP status message when the response has no JSON body.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export async function listPeriods(signal?: AbortSignal): Promise<string[]> {
  const options = await getJson<FilterOptions>('/filtros/periodos', signal)
  return options.valores
}

export async function getGlobalKpi(period: string | null, signal?: AbortSignal): Promise<GlobalKpi> {
  const query = new URLSearchParams()
  if (period) query.set('periodo', period)
  const suffix = query.size > 0 ? `?${query.toString()}` : ''
  return getJson<GlobalKpi>(`/kpis/global${suffix}`, signal)
}
