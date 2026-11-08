import type { AuthSession, LoginPayload } from '../types'
import { createAuthClient } from '@neon/auth'

const SESSION_KEY = 'saberpro-bi.auth.v1'
const API_URL = import.meta.env.VITE_API_URL ?? ''
const NEON_AUTH_URL = import.meta.env.VITE_NEON_AUTH_URL
const authClient = createAuthClient(NEON_AUTH_URL)

function isAuthSession(value: unknown): value is AuthSession {
  if (!value || typeof value !== 'object') return false
  const session = value as Partial<AuthSession>
  return Boolean(session.accessToken && session.user?.email && session.user?.role)
}

export async function login(payload: LoginPayload): Promise<AuthSession> {
  if (API_URL) {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error('El correo o la contraseña no son correctos.')
    const data: AuthSession = await response.json()
    if (!isAuthSession(data)) throw new Error('La respuesta de autenticación no es válida.')
    saveSession(data)
    return data
  }

  const { data, error } = await authClient.signIn.email(payload)
  if (error || !data?.user) {
    throw new Error(error?.message ?? 'El correo o la contraseña no son correctos.')
  }

  const session: AuthSession = {
    accessToken: data.token,
    tokenType: 'Bearer',
    user: {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.email.includes('admin')
        ? 'Administrador'
        : data.user.email.includes('investigador') ? 'Investigador' : 'Analista',
    },
  }
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
  void authClient.signOut()
}

export function authHeaders(): Record<string, string> {
  const session = getSession()
  return session ? { Authorization: `${session.tokenType} ${session.accessToken}` } : {}
}
