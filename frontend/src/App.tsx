import { FormEvent, useState } from 'react'
import { FiActivity, FiAlertCircle, FiArrowRight, FiArrowUpRight, FiBarChart2, FiCheckCircle, FiEye, FiEyeOff, FiLock, FiLogOut, FiMail } from 'react-icons/fi'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { authHeaders, clearSession, getSession, login } from './services/authApi'
import type { AuthSession, UserRole } from './types'

function BrandMark() {
  return <FiBarChart2 className="brand-mark" aria-hidden="true" />
}

function LoginPage({ onLogin }: { onLogin: (session: AuthSession) => void }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const session = await login({ email, password })
      onLogin(session)
      navigate('/dashboard', { replace: true })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No fue posible iniciar sesión.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story" aria-label="SaberPro BI">
        <div className="story-grid" />
        <div className="story-topline"><BrandMark /><span>SaberPro BI</span><span className="story-status"><FiCheckCircle /> plataforma activa</span></div>
        <div className="story-content">
          <p className="eyebrow">Inteligencia para la educación superior</p>
          <h1>Las decisiones<br /><em>empiezan</em> con datos.</h1>
          <p className="story-copy">Explora el desempeño académico colombiano desde una sola mirada. Una lectura más clara para cada equipo.</p>
        </div>
        <div className="story-footer"><span>01</span><div className="footer-line" /><span>Resultados Saber Pro · 2026</span></div>
      </section>
      <section className="login-panel">
        <div className="login-panel-inner">
          <div className="mobile-brand"><BrandMark /><strong>SaberPro <span>BI</span></strong></div>
          <div className="welcome">
            <p className="eyebrow">Área segura</p>
            <h2>Bienvenido de nuevo</h2>
            <p>Ingresa tus credenciales para continuar al centro de análisis.</p>
          </div>
          <form onSubmit={submit}>
            <label htmlFor="email">Correo institucional</label>
            <div className="input-wrap">
              <FiMail className="input-icon" aria-hidden="true" />
              <input id="email" type="email" autoComplete="email" placeholder="nombre@universidad.edu.co" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </div>
            <div className="label-row"><label htmlFor="password">Contraseña</label><a href="#help" onClick={(event) => event.preventDefault()}>¿Necesitas ayuda?</a></div>
            <div className="input-wrap">
              <FiLock className="input-icon" aria-hidden="true" />
              <input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Mínimo 6 caracteres" value={password} onChange={(event) => setPassword(event.target.value)} minLength={6} required />
              <button type="button" className="visibility" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>{showPassword ? <FiEyeOff /> : <FiEye />}</button>
            </div>
            {error && <div className="form-error" role="alert"><FiAlertCircle />{error}</div>}
            <button className="submit-button" type="submit" disabled={loading}>{loading ? 'Verificando...' : 'Iniciar sesión'}<FiArrowUpRight aria-hidden="true" /></button>
          </form>
          <p className="login-note"><FiLock className="lock" aria-hidden="true" /> Tus datos viajan protegidos y solo tú puedes acceder a ellos.</p>
          <p className="demo-hint">El acceso usa Neon Auth. Solicita una cuenta al administrador de la plataforma.</p>
        </div>
        <span className="panel-index">SBI / 01</span>
      </section>
    </main>
  )
}

const roleDetails: Record<UserRole, { title: string; description: string; accent: string }> = {
  Administrador: { title: 'Control del sistema', description: 'Supervisa usuarios, permisos y la salud de la plataforma.', accent: 'Vista administrativa' },
  Analista: { title: 'Lectura del desempeño', description: 'Convierte resultados en señales que orientan la acción.', accent: 'Vista analítica' },
  Investigador: { title: 'Explora nuevas preguntas', description: 'Encuentra patrones y evidencia para profundizar el análisis.', accent: 'Vista de investigación' },
}

function ProtectedRoute({ session, children }: { session: AuthSession | null; children: React.ReactNode }) {
  const location = useLocation()
  return session && authHeaders().Authorization ? children : <Navigate to="/login" replace state={{ from: location }} />
}

function Dashboard({ session, onLogout }: { session: AuthSession; onLogout: () => void }) {
  const navigate = useNavigate()
  const detail = roleDetails[session.user.role]
  return <main className="dashboard-shell">
    <header className="dashboard-header"><div className="dashboard-brand"><BrandMark /><span>SaberPro <b>BI</b></span></div><div className="user-area"><div className="avatar">{session.user.name.charAt(0)}</div><div><strong>{session.user.name}</strong><small>{session.user.role}</small></div><button onClick={() => { onLogout(); navigate('/login', { replace: true }) }} aria-label="Cerrar sesión">Salir <FiLogOut aria-hidden="true" /></button></div></header>
    <div className="dashboard-body"><aside><p className="eyebrow">Tu espacio</p><nav><a className="active" href="#overview">Resumen <span>01</span></a><a href="#reports">Reportes <span>02</span></a><a href="#data">Datos <span>03</span></a></nav><div className="side-foot"><span>Sesión protegida</span><FiCheckCircle /></div></aside><section className="dashboard-content"><div className="dashboard-intro"><div><p className="eyebrow">{detail.accent}</p><h1>{detail.title}</h1><p>{detail.description}</p></div><span className="date-stamp">07 NOV<br /><b>2026</b></span></div><div className="signal-card"><div><p className="eyebrow">Punto de partida</p><h2>Tu panel está listo.</h2><p>Elige una vista para comenzar a trabajar con los resultados Saber Pro.</p></div><div className="signal-orbit"><FiActivity aria-hidden="true" /></div></div><div className="metric-row"><div><small>Acceso actual</small><strong>{session.user.role}</strong></div><div><small>Estado de sesión</small><strong className="online">Activo <FiCheckCircle aria-hidden="true" /></strong></div><div><small>Próximo paso</small><strong>Explorar datos <FiArrowRight aria-hidden="true" /></strong></div></div></section></div>
  </main>
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(() => getSession())
  function logout() { clearSession(); setSession(null) }
  return <Routes><Route path="/login" element={session ? <Navigate to="/dashboard" replace /> : <LoginPage onLogin={setSession} />} /><Route path="/dashboard" element={<ProtectedRoute session={session}><Dashboard session={session!} onLogout={logout} /></ProtectedRoute>} /><Route path="*" element={<Navigate to={session ? '/dashboard' : '/login'} replace />} /></Routes>
}
