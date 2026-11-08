import { FormEvent, useEffect, useRef, useState } from 'react'
import { FiActivity, FiAlertCircle, FiArrowRight, FiArrowUpRight, FiBarChart2, FiCheckCircle, FiDatabase, FiDownload, FiEye, FiEyeOff, FiFileText, FiLoader, FiLock, FiLogOut, FiMail, FiMenu, FiPieChart, FiShield, FiSliders, FiTrendingUp, FiUsers, FiX } from 'react-icons/fi'
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

const roleMenu: Record<UserRole, Array<{ id: string; label: string; icon: React.ReactNode }>> = {
  Administrador: [
    { id: 'overview', label: 'Resumen', icon: <FiActivity /> },
    { id: 'users', label: 'Usuarios y permisos', icon: <FiUsers /> },
    { id: 'reports', label: 'Reportes gerenciales', icon: <FiFileText /> },
    { id: 'data', label: 'Datos y ETL', icon: <FiDatabase /> },
    { id: 'health', label: 'Estado de la plataforma', icon: <FiShield /> },
  ],
  Analista: [
    { id: 'overview', label: 'Resumen', icon: <FiActivity /> },
    { id: 'kpis', label: 'Indicadores KPI', icon: <FiTrendingUp /> },
    { id: 'reports', label: 'Reportes analíticos', icon: <FiFileText /> },
    { id: 'data', label: 'Datos y filtros', icon: <FiSliders /> },
  ],
  Investigador: [
    { id: 'overview', label: 'Resumen', icon: <FiActivity /> },
    { id: 'distributions', label: 'Distribuciones', icon: <FiPieChart /> },
    { id: 'predictions', label: 'Predicciones', icon: <FiTrendingUp /> },
    { id: 'reports', label: 'Reportes de estudio', icon: <FiFileText /> },
  ],
}

function ProtectedRoute({ session, children }: { session: AuthSession | null; children: React.ReactNode }) {
  const location = useLocation()
  return session && authHeaders().Authorization ? children : <Navigate to="/login" replace state={{ from: location }} />
}

function Dashboard({ session, onLogout }: { session: AuthSession; onLogout: () => void }) {
  const navigate = useNavigate()
  const detail = roleDetails[session.user.role]
  const menuItems = roleMenu[session.user.role]
  const contentRef = useRef<HTMLElement>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [exportMessage, setExportMessage] = useState('')
  const [activeView, setActiveView] = useState(() => {
    const viewFromHash = window.location.hash.slice(1)
    return menuItems.some((item) => item.id === viewFromHash) ? viewFromHash : menuItems[0].id
  })
  const [menuOpen, setMenuOpen] = useState(false)
  const activeMenuItem = menuItems.find((item) => item.id === activeView) ?? menuItems[0]

  useEffect(() => {
    if (!menuOpen) return
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [menuOpen])

  function selectView(viewId: string) {
    setActiveView(viewId)
    setMenuOpen(false)
    window.history.replaceState(null, '', `#${viewId}`)
    document.getElementById('dashboard-main-content')?.focus({ preventScroll: true })
  }

  function logout() {
    setMenuOpen(false)
    onLogout()
    navigate('/login', { replace: true })
  }

  async function exportPdf() {
    if (!contentRef.current || isExporting) return

    setIsExporting(true)
    setExportMessage('')
    try {
      const { exportDashboardPdf } = await import('./services/dashboardPdf')
      await exportDashboardPdf(contentRef.current, {
        title: detail.title,
        viewerName: session.user.name,
        viewerRole: session.user.role,
        activeFilters: [],
      })
      setExportMessage('Reporte PDF generado correctamente.')
    } catch (reason) {
      setExportMessage(reason instanceof Error ? reason.message : 'No fue posible generar el reporte PDF.')
    } finally {
      setIsExporting(false)
    }
  }

  const currentDate = new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date())

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <div className="dashboard-brand"><BrandMark /><span>SaberPro <b>BI</b></span></div>
        <div className="user-area">
          <button
            className="mobile-menu-button"
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label={menuOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'}
            aria-expanded={menuOpen}
            aria-controls="role-navigation"
          >
            {menuOpen ? <FiX /> : <FiMenu />}
          </button>
          <button
            className="export-button"
            type="button"
            onClick={exportPdf}
            disabled={isExporting}
            aria-label="Exportar dashboard en PDF"
          >
            {isExporting ? <FiLoader className="export-spinner" aria-hidden="true" /> : <FiDownload aria-hidden="true" />}
            {isExporting ? 'Generando PDF...' : 'Exportar PDF'}
          </button>
          <div className="avatar">{session.user.name.charAt(0)}</div>
          <div className="user-copy"><strong>{session.user.name}</strong><small>{session.user.role}</small></div>
          <button className="logout-button" onClick={logout} aria-label="Cerrar sesión"><FiLogOut aria-hidden="true" /><span>Salir</span></button>
        </div>
      </header>
      <div className="dashboard-body">
        {menuOpen && <button className="menu-backdrop" type="button" onClick={() => setMenuOpen(false)} aria-label="Cerrar menú" />}
        <aside id="role-navigation" className={menuOpen ? 'is-open' : ''}>
          <div className="menu-heading">
            <p className="eyebrow">Tu espacio</p>
            <span>{session.user.role}</span>
          </div>
          <nav aria-label="Navegación principal">
            {menuItems.map((item, index) => (
              <button
                className={activeView === item.id ? 'active' : ''}
                type="button"
                onClick={() => selectView(item.id)}
                aria-current={activeView === item.id ? 'page' : undefined}
                key={item.id}
              >
                <span className="menu-item-icon">{item.icon}</span>
                <span>{item.label}</span>
                <small>{String(index + 1).padStart(2, '0')}</small>
              </button>
            ))}
          </nav>
          <div className="side-foot"><span>Sesión protegida</span><FiCheckCircle /></div>
        </aside>
        <section ref={contentRef} className="dashboard-content" id="dashboard-main-content" tabIndex={-1}>
          <div className="dashboard-intro">
            <div><p className="eyebrow">{activeView === 'overview' ? detail.accent : activeMenuItem.label}</p><h1>{activeView === 'overview' ? detail.title : activeMenuItem.label}</h1><p>{activeView === 'overview' ? detail.description : `Acceso habilitado para el perfil ${session.user.role}.`}</p></div>
            <span className="date-stamp">{currentDate}</span>
          </div>
          <div className="signal-card">
            <div><p className="eyebrow">Punto de partida</p><h2>{activeView === 'overview' ? 'Tu panel está listo.' : activeMenuItem.label}</h2><p>{activeView === 'overview' ? 'Elige una vista para comenzar a trabajar con los resultados Saber Pro.' : 'Esta sección está disponible según tu rol. Selecciona otra opción para cambiar de módulo.'}</p></div>
            <div className="signal-orbit"><FiActivity aria-hidden="true" /></div>
          </div>
          <div className="metric-row">
            <div><small>Acceso actual</small><strong>{session.user.role}</strong></div>
            <div><small>Estado de sesión</small><strong className="online">Activo <FiCheckCircle aria-hidden="true" /></strong></div>
            <div><small>Próximo paso</small><strong>Explorar datos <FiArrowRight aria-hidden="true" /></strong></div>
          </div>
        </section>
      </div>
      {exportMessage && (
        <div
          className={`export-feedback ${exportMessage.startsWith('Reporte') ? 'is-success' : 'is-error'}`}
          role="status"
          aria-live="polite"
        >
          {exportMessage.startsWith('Reporte') ? <FiCheckCircle aria-hidden="true" /> : <FiAlertCircle aria-hidden="true" />}
          <span>{exportMessage}</span>
          <button type="button" onClick={() => setExportMessage('')} aria-label="Cerrar mensaje">×</button>
        </div>
      )}
    </main>
  )
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(() => getSession())
  function logout() { clearSession(); setSession(null) }
  return <Routes><Route path="/login" element={session ? <Navigate to="/dashboard" replace /> : <LoginPage onLogin={setSession} />} /><Route path="/dashboard" element={<ProtectedRoute session={session}><Dashboard session={session!} onLogout={logout} /></ProtectedRoute>} /><Route path="*" element={<Navigate to={session ? '/dashboard' : '/login'} replace />} /></Routes>
}
