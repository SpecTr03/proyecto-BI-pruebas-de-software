import type { AuthSession, LoginPayload } from '../types'

const SESSION_KEY = 'saberpro-bi.auth.v1'
const API_ORIGIN = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const LOGIN_URL = API_ORIGIN
  ? `${API_ORIGIN}/api/auth/login`
  : '/api/auth/login'

function isAuthSession(value: unknown): value is AuthSession {
  if (!value || typeof value !== 'object') return false
  const session = value as Partial<AuthSession>
  return Boolean(
    session.accessToken &&
      session.tokenType &&
      session.user?.id &&
      session.user?.email &&
      session.user?.role &&
      (session.expiresAt === undefined || Number.isFinite(session.expiresAt)),
  )
}

async function getApiError(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: unknown; message?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (typeof body.message === 'string') return body.message
  } catch {
    // The API may return an empty or non-JSON error body.
  }
  return 'No fue posible iniciar sesión. Inténtalo de nuevo.'
}

export async function login(payload: LoginPayload): Promise<AuthSession> {
  let response: Response
  try {
    response = await fetch(LOGIN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new Error('No se pudo conectar con el servidor. Verifica que la API esté activa.')
  }
  if (!response.ok) throw new Error(await getApiError(response))
  const raw = await response.json() as {
    access_token: string
    token_type: string
    expires_at: string
    user: AuthSession['user']
  }
  const expiresAt = Date.parse(raw.expires_at)
  const session: AuthSession = {
    accessToken: raw.access_token,
    tokenType: raw.token_type,
    expiresAt,
    user: raw.user,
  }
  if (!isAuthSession(session)) throw new Error('La respuesta de autenticación no es válida.')
  saveSession(session)
  return session
}

export function getSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const session: unknown = JSON.parse(raw)
    if (!isAuthSession(session)) return null
    if (session.expiresAt && session.expiresAt <= Date.now()) {
      clearSession()
      return null
    }
    return session
  } catch {
    clearSession()
    return null
  }
}

export function saveSession(session: AuthSession) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY)
}

export function authHeaders(): Record<string, string> {
  const session = getSession()
  return session ? { Authorization: `${session.tokenType} ${session.accessToken}` } : {}
}
