import type { AuthSession, LoginPayload } from '../types'

const SESSION_KEY = 'saberpro-bi.auth.v1'
const API_URL = import.meta.env.VITE_API_URL ?? ''

function isAuthSession(value: unknown): value is AuthSession {
  if (!value || typeof value !== 'object') return false
  const session = value as Partial<AuthSession>
  return Boolean(session.accessToken && session.user?.email && session.user?.role)
}

export async function login(payload: LoginPayload): Promise<AuthSession> {
  if (!API_URL) {
    return demoLogin(payload)
  }

  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const message = response.status === 401
      ? 'El correo o la contraseña no son correctos.'
      : 'No fue posible conectar con el servicio de acceso.'
    throw new Error(message)
  }

  const data: AuthSession = await response.json()
  if (!isAuthSession(data)) throw new Error('La respuesta de autenticación no es válida.')
  saveSession(data)
  return data
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

async function demoLogin({ email, password }: LoginPayload): Promise<AuthSession> {
  await new Promise((resolve) => window.setTimeout(resolve, 650))
  if (!email || password.length < 6) {
    throw new Error('El correo o la contraseña no son correctos.')
  }

  const role: AuthSession['user']['role'] = email.includes('admin')
    ? 'Administrador'
    : email.includes('investigador') ? 'Investigador' : 'Analista'

  const session: AuthSession = {
    accessToken: `demo-token-${crypto.randomUUID()}`,
    tokenType: 'Bearer',
    expiresAt: Date.now() + 8 * 60 * 60 * 1000,
    user: {
      id: 'demo-user',
      name: role === 'Administrador' ? 'María Gómez' : role === 'Investigador' ? 'Carlos Ruiz' : 'Laura Méndez',
      email,
      role,
    },
  }
  saveSession(session)
  return session
}
