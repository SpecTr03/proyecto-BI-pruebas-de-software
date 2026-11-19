import { authHeaders } from './authApi'

const API_ORIGIN = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export interface PredictionInput {
  genero: string
  estrato: string
  educacion_padre: string
  educacion_madre: string
  tiene_internet: string
  tiene_computador: string
  caracter_academico: string
  metodo_programa: string
  depto_reside: string
  depto_institucion: string
}

export interface PredictionResult {
  puntaje_predicho: number
  nivel_desempeno: string
  confianza: number | null
  probabilidad_superar_media_nacional: number
  media_nacional: number
}

export interface PredictionFilterOptions {
  educacion_padre: string[]
  educacion_madre: string[]
  caracter_academico: string[]
  metodo_programa: string[]
  depto_reside: string[]
  depto_institucion: string[]
}

interface FilterResponse {
  valores: string[]
  total: number
}

async function getFilterOptions(
  path: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const response = await fetch(`${API_ORIGIN}/api${path}`, {
    headers: authHeaders(),
    signal,
  })
  if (!response.ok) {
    throw new Error('No fue posible cargar las opciones del perfil.')
  }
  const body = await response.json() as FilterResponse
  return body.valores
}

export async function listPredictionFilterOptions(
  signal?: AbortSignal,
): Promise<PredictionFilterOptions> {
  const [
    educacionPadre,
    educacionMadre,
    caracteres,
    metodos,
    departamentos,
    departamentosInstitucion,
  ] = await Promise.all([
    getFilterOptions('/filtros/educacion-padre', signal),
    getFilterOptions('/filtros/educacion-madre', signal),
    getFilterOptions('/filtros/caracteres', signal),
    getFilterOptions('/filtros/metodos', signal),
    getFilterOptions('/filtros/departamentos', signal),
    getFilterOptions('/filtros/departamentos-institucion', signal),
  ])

  return {
    educacion_padre: educacionPadre,
    educacion_madre: educacionMadre,
    caracter_academico: caracteres,
    metodo_programa: metodos,
    depto_reside: departamentos,
    depto_institucion: departamentosInstitucion,
  }
}

export async function predictPerformance(
  payload: PredictionInput,
  signal?: AbortSignal,
): Promise<PredictionResult> {
  let response: Response
  try {
    response = await fetch(`${API_ORIGIN}/api/predecir`, {
      method: 'POST',
      headers: {
        ...authHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
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
      // Keep the status-based fallback for non-JSON errors.
    }
    throw new Error(message)
  }

  return response.json() as Promise<PredictionResult>
}
