import type { UserRole } from '../types'
import { authHeaders } from './authApi'

const API_ORIGIN = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const USERS_URL = API_ORIGIN ? `${API_ORIGIN}/api/users` : '/api/users'

export interface ManagedUser {
  id: string
  name: string
  email: string
  role: UserRole
  is_active: boolean
}

export interface CreateManagedUserPayload {
  name: string
  email: string
  password: string
  role: UserRole
}

async function getError(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // La respuesta puede no incluir JSON.
  }
  return 'No fue posible completar la operación.'
}

export async function listManagedUsers(): Promise<ManagedUser[]> {
  const response = await fetch(USERS_URL, { headers: authHeaders() })
  if (!response.ok) throw new Error(await getError(response))
  return response.json() as Promise<ManagedUser[]>
}

export async function createManagedUser(payload: CreateManagedUserPayload): Promise<ManagedUser> {
  const response = await fetch(USERS_URL, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(await getError(response))
  return response.json() as Promise<ManagedUser>
}

export async function updateManagedUser(
  userId: string,
  payload: { role?: UserRole; is_active?: boolean },
): Promise<ManagedUser> {
  const response = await fetch(`${USERS_URL}/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(await getError(response))
  return response.json() as Promise<ManagedUser>
}
