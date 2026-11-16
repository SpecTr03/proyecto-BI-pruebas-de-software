import { authHeaders } from './authApi'

const API_ORIGIN = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export const TREND_FILTERS = [
  { key: 'anio', label: 'Año', endpoint: 'anios' },
  { key: 'departamento', label: 'Departamento', endpoint: 'departamentos' },
  { key: 'municipio', label: 'Municipio', endpoint: 'municipios' },
  { key: 'institucion', label: 'Nombre IES', endpoint: 'instituciones' },
  { key: 'caracter_institucion', label: 'Carácter IES', endpoint: 'caracteres' },
  { key: 'programa', label: 'Programa', endpoint: 'programas' },
  { key: 'metodo_programa', label: 'Jornada', endpoint: 'metodos' },
  { key: 'genero', label: 'Género', endpoint: 'generos' },
  { key: 'estrato', label: 'Estrato socioeconómico', endpoint: 'estratos' },
  { key: 'grupo_referencia', label: 'Grupo de referencia', endpoint: 'nucleos' },
] as const

export type TrendFilterKey = typeof TREND_FILTERS[number]['key']
export type TrendFilters = Record<TrendFilterKey, string>
export type TrendFilterOptions = Record<TrendFilterKey, string[]>

export interface HistoricalPoint {
  anio: string
  promedio_global: number
  total_registros: number
}

export interface StratumPerformance {
  estrato: string
  promedio_global: number
  total_registros: number
}

export interface CompetencyComparison {
  institucion: string
  grupo_referencia: string
  promedios_institucion: Record<string, number>
  promedios_nacionales: Record<string, number>
  total_institucion: number
  total_nacional: number
}

interface FilterResponse {
  valores: string[]
  total: number
}

interface HistoricalResponse {
  puntos: HistoricalPoint[]
  filtros: Partial<TrendFilters>
}

interface StratumResponse {
  datos: StratumPerformance[]
}

interface ComparisonFilterOptions {
  instituciones: string[]
  grupos: string[]
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
    let message = `La API respondió con el estado ${response.status}.`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') message = body.detail
    } catch {
      // Retain the HTTP status when the API does not provide JSON details.
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export async function listTrendFilterOptions(signal?: AbortSignal): Promise<TrendFilterOptions> {
  const responses = await Promise.all(
    TREND_FILTERS.map(async ({ key, endpoint }) => {
      const result = await getJson<FilterResponse>(`/filtros/${endpoint}`, signal)
      return [key, result.valores] as const
    }),
  )
  return Object.fromEntries(responses) as TrendFilterOptions
}

export async function getHistoricalTrend(
  filters: TrendFilters,
  signal?: AbortSignal,
): Promise<HistoricalPoint[]> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value) query.set(key, value)
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : ''
  const response = await getJson<HistoricalResponse>(`/graficas/historico${suffix}`, signal)
  return response.puntos
}

export async function getStratumPerformance(signal?: AbortSignal): Promise<StratumPerformance[]> {
  const response = await getJson<StratumResponse>('/graficas/desempeno-estratos', signal)
  return response.datos
}

export async function listComparisonOptions(signal?: AbortSignal): Promise<ComparisonFilterOptions> {
  const [institutions, groups] = await Promise.all([
    getJson<FilterResponse>('/filtros/instituciones', signal),
    getJson<FilterResponse>('/filtros/nucleos', signal),
  ])
  return { instituciones: institutions.valores, grupos: groups.valores }
}

export async function getCompetencyComparison(
  institucion: string,
  grupoReferencia: string,
  signal?: AbortSignal,
): Promise<CompetencyComparison> {
  const query = new URLSearchParams({
    institucion,
    grupo_referencia: grupoReferencia,
  })
  return getJson<CompetencyComparison>(`/graficas/comparativo-competencias?${query}`, signal)
}
