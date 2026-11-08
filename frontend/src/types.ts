export type UserRole = 'Administrador' | 'Analista' | 'Investigador'

export interface AuthUser {
  id: string
  name: string
  email: string
  role: UserRole
  permissions?: string[]
}

export interface AuthSession {
  accessToken: string
  tokenType: string
  expiresAt?: number
  user: AuthUser
}

export interface LoginPayload {
  email: string
  password: string
}
