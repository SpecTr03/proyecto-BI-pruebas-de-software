import { FormEvent, useEffect, useRef, useState } from 'react'
import { FiActivity, FiAlertCircle, FiArrowRight, FiArrowUpRight, FiBarChart2, FiCheckCircle, FiDatabase, FiDownload, FiEye, FiEyeOff, FiFileText, FiLoader, FiLock, FiLogOut, FiMail, FiMenu, FiPieChart, FiShield, FiSliders, FiTrendingUp, FiUsers, FiX } from 'react-icons/fi'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { authHeaders, clearSession, getSession, login } from './services/authApi'
import { getGlobalKpi, listPeriods, type GlobalKpi } from './services/kpisApi'
import {
  getHistoricalTrend,
  listTrendFilterOptions,
  TREND_FILTERS,
  type HistoricalPoint,
  type TrendFilterKey,
  type TrendFilterOptions,
  type TrendFilters,
} from './services/historicalApi'
import {
  createManagedUser,
  listManagedUsers,
  updateManagedUser,
  type ManagedUser,
} from './services/usersApi'
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
              <input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Mínimo 8 caracteres" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required />
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

function UserManagement({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('Analista')

  async function loadUsers() {
    setLoading(true)
    setError('')
    try {
      setUsers(await listManagedUsers())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No fue posible cargar los usuarios.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadUsers()
  }, [])

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const created = await createManagedUser({ name, email, password, role })
      setUsers((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)))
      setName('')
      setEmail('')
      setPassword('')
      setRole('Analista')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No fue posible crear el usuario.')
    } finally {
      setSaving(false)
    }
  }

  async function updateUser(userId: string, payload: { role?: UserRole; is_active?: boolean }) {
    setSaving(true)
    setError('')
    try {
      const updated = await updateManagedUser(userId, payload)
      setUsers((current) => current.map((user) => user.id === updated.id ? updated : user))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No fue posible actualizar el usuario.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="user-management">
      <form className="user-create-form" onSubmit={createUser}>
        <div>
          <label htmlFor="user-name">Nombre completo</label>
          <input id="user-name" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} />
        </div>
        <div>
          <label htmlFor="user-email">Correo</label>
          <input id="user-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </div>
        <div>
          <label htmlFor="user-password">Contraseña temporal</label>
          <input id="user-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
        </div>
        <div>
          <label htmlFor="user-role">Rol</label>
          <select id="user-role" value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
            <option>Administrador</option>
            <option>Analista</option>
            <option>Investigador</option>
          </select>
        </div>
        <button type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Crear usuario'}</button>
      </form>

      {error && <div className="management-error" role="alert">{error}</div>}
      {loading ? (
        <p className="management-loading">Cargando usuarios...</p>
      ) : (
        <div className="users-table-wrap">
          <table className="users-table">
            <thead><tr><th>Usuario</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Acción</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>
                    <select
                      value={user.role}
                      disabled={saving}
                      aria-label={`Cambiar rol de ${user.name}`}
                      onChange={(event) => void updateUser(user.id, { role: event.target.value as UserRole })}
                    >
                      <option>Administrador</option>
                      <option>Analista</option>
                      <option>Investigador</option>
                    </select>
                  </td>
                  <td><span className={`status-pill ${user.is_active ? 'active' : 'inactive'}`}>{user.is_active ? 'Activo' : 'Inactivo'}</span></td>
                  <td>
                    <button
                      className="state-button"
                      type="button"
                      disabled={saving || user.id === currentUserId}
                      onClick={() => void updateUser(user.id, { is_active: !user.is_active })}
                    >
                      {user.is_active ? 'Desactivar' : 'Activar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function GlobalKpiCard() {
  const [periods, setPeriods] = useState<string[]>([])
  const [period, setPeriod] = useState('')
  const [kpi, setKpi] = useState<GlobalKpi | null>(null)
  const [loadingPeriods, setLoadingPeriods] = useState(true)
  const [loadingKpi, setLoadingKpi] = useState(false)
  const [periodsFailed, setPeriodsFailed] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    listPeriods(controller.signal)
      .then((values) => {
        const ordered = [...values].sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))
        setPeriods(ordered)
        setPeriod(ordered[0] ?? '')
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setPeriodsFailed(true)
          setError(reason instanceof Error ? reason.message : 'No fue posible cargar los periodos.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingPeriods(false)
      })

    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (loadingPeriods || periodsFailed) return
    const controller = new AbortController()
    setLoadingKpi(true)
    setError('')
    getGlobalKpi(period || null, controller.signal)
      .then(setKpi)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setError(reason instanceof Error ? reason.message : 'No fue posible consultar el KPI.')
          setKpi(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingKpi(false)
      })

    return () => controller.abort()
  }, [loadingPeriods, period, periodsFailed])

  const comparison = kpi?.comparativo_porcentual
  const comparisonClass = comparison === null || comparison === undefined
    ? 'neutral'
    : comparison >= 0 ? 'positive' : 'negative'

  return (
    <section className="global-kpi" aria-labelledby="global-kpi-title">
      <div className="global-kpi-heading">
        <div>
          <p className="eyebrow">Indicador de desempeño</p>
          <h2 id="global-kpi-title">Promedio global Saber Pro</h2>
          <p>Promedio de las cinco competencias para el periodo seleccionado.</p>
        </div>
        <label className="period-filter" htmlFor="kpi-period">
          Periodo académico
          <select
            id="kpi-period"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            disabled={loadingPeriods || periods.length === 0}
          >
            {periods.length === 0 && <option value="">Todos los periodos</option>}
            {periods.map((value) => <option value={value} key={value}>{value}</option>)}
          </select>
        </label>
      </div>

      {error ? (
        <p className="global-kpi-message is-error" role="alert">{error}</p>
      ) : loadingPeriods || loadingKpi ? (
        <p className="global-kpi-message" role="status">Cargando indicador...</p>
      ) : kpi ? (
        <div className="global-kpi-content" aria-live="polite">
          <div className="global-kpi-value">
            <span>{kpi.total_registros > 0 ? kpi.promedio_global.toFixed(2) : '—'}</span>
            <small>puntos promedio</small>
          </div>
          <div className="global-kpi-details">
            <div>
              <small>Estudiantes evaluados</small>
              <strong>{kpi.total_registros.toLocaleString('es-CO')}</strong>
            </div>
            <div>
              <small>Variación frente al periodo anterior</small>
              <strong className={`kpi-comparison ${comparisonClass}`}>
                {comparison === null || comparison === undefined
                  ? 'No disponible'
                  : `${comparison > 0 ? '+' : ''}${comparison.toFixed(2)}%`}
              </strong>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

const EMPTY_TREND_FILTERS: TrendFilters = {
  anio: '',
  departamento: '',
  municipio: '',
  institucion: '',
  caracter_institucion: '',
  programa: '',
  metodo_programa: '',
  genero: '',
  estrato: '',
  grupo_referencia: '',
}

const EMPTY_TREND_OPTIONS: TrendFilterOptions = {
  anio: [],
  departamento: [],
  municipio: [],
  institucion: [],
  caracter_institucion: [],
  programa: [],
  metodo_programa: [],
  genero: [],
  estrato: [],
  grupo_referencia: [],
}

function HistoricalTrend() {
  const [filters, setFilters] = useState<TrendFilters>(EMPTY_TREND_FILTERS)
  const [options, setOptions] = useState<TrendFilterOptions>(EMPTY_TREND_OPTIONS)
  const [points, setPoints] = useState<HistoricalPoint[]>([])
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [loadingTrend, setLoadingTrend] = useState(false)
  const [optionsError, setOptionsError] = useState('')
  const [trendError, setTrendError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    listTrendFilterOptions(controller.signal)
      .then(setOptions)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setOptionsError(reason instanceof Error ? reason.message : 'No fue posible cargar los filtros.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingOptions(false)
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (loadingOptions || optionsError) return
    const controller = new AbortController()
    setLoadingTrend(true)
    setTrendError('')
    getHistoricalTrend(filters, controller.signal)
      .then(setPoints)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setTrendError(reason instanceof Error ? reason.message : 'No fue posible consultar la serie histórica.')
          setPoints([])
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingTrend(false)
      })
    return () => controller.abort()
  }, [filters, loadingOptions, optionsError])

  function updateFilter(key: TrendFilterKey, value: string) {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  const width = 760
  const height = 300
  const left = 54
  const right = 18
  const top = 24
  const bottom = 42
  const chartWidth = width - left - right
  const chartHeight = height - top - bottom
  const values = points.map((point) => point.promedio_global)
  const minimum = values.length ? Math.min(...values) : 0
  const maximum = values.length ? Math.max(...values) : 1
  const valueRange = maximum - minimum || 1
  const plottedPoints = points.map((point, index) => ({
    ...point,
    x: points.length === 1 ? left + chartWidth / 2 : left + index * chartWidth / (points.length - 1),
    y: top + chartHeight - ((point.promedio_global - minimum) / valueRange) * chartHeight,
  }))
  const linePath = plottedPoints
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ')

  return (
    <section className="historical-trend" aria-labelledby="historical-trend-title">
      <header className="historical-trend-heading">
        <div>
          <p className="eyebrow">Evolución temporal</p>
          <h2 id="historical-trend-title">Puntaje global medio por año</h2>
          <p>Selecciona los filtros para segmentar la serie. Cada punto muestra el promedio global del año.</p>
        </div>
      </header>

      <div className="trend-filters" aria-label="Filtros de la serie histórica">
        {TREND_FILTERS.map(({ key, label }) => (
          <label key={key} htmlFor={`trend-${key}`}>
            {label}
            <select
              id={`trend-${key}`}
              value={filters[key]}
              onChange={(event) => updateFilter(key, event.target.value)}
              disabled={loadingOptions || optionsError !== ''}
            >
              <option value="">Todos</option>
              {options[key].map((value) => <option value={value} key={value}>{value}</option>)}
            </select>
          </label>
        ))}
      </div>

      {optionsError ? (
        <p className="trend-message is-error" role="alert">{optionsError}</p>
      ) : loadingOptions || loadingTrend ? (
        <p className="trend-message" role="status">Cargando serie histórica...</p>
      ) : trendError ? (
        <p className="trend-message is-error" role="alert">{trendError}</p>
      ) : points.length === 0 ? (
        <p className="trend-message" role="status">No hay resultados para los filtros seleccionados.</p>
      ) : (
        <>
          <div className="trend-chart-wrap">
            <svg
              className="trend-chart"
              viewBox={`0 0 ${width} ${height}`}
              role="img"
              aria-labelledby="historical-trend-title historical-trend-description"
            >
              <desc id="historical-trend-description">
                Gráfico de líneas del promedio global de Saber Pro por año. Pasa sobre cada punto para ver el puntaje y el total de registros.
              </desc>
              {[0, 0.5, 1].map((fraction) => {
                const y = top + chartHeight * fraction
                const value = maximum - valueRange * fraction
                return (
                  <g key={fraction}>
                    <line x1={left} x2={width - right} y1={y} y2={y} className="trend-gridline" />
                    <text x={left - 10} y={y + 4} textAnchor="end" className="trend-axis-label">{value.toFixed(1)}</text>
                  </g>
                )
              })}
              <path d={linePath} className="trend-line" />
              {plottedPoints.map((point) => (
                <g key={point.anio}>
                  <circle cx={point.x} cy={point.y} r="6" className="trend-point">
                    <title>{`${point.anio}: ${point.promedio_global.toFixed(2)} puntos; ${point.total_registros.toLocaleString('es-CO')} registros`}</title>
                  </circle>
                  <text x={point.x} y={height - 13} textAnchor="middle" className="trend-axis-label">{point.anio}</text>
                </g>
              ))}
            </svg>
          </div>
          <div className="trend-table-wrap">
            <table className="trend-table">
              <thead><tr><th>Año</th><th>Promedio global</th><th>Registros</th></tr></thead>
              <tbody>
                {points.map((point) => (
                  <tr key={point.anio}>
                    <td>{point.anio}</td>
                    <td>{point.promedio_global.toFixed(2)}</td>
                    <td>{point.total_registros.toLocaleString('es-CO')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
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
        title: activeView === 'overview'
          ? `${detail.title} - Resumen`
          : activeMenuItem.label,
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
          {activeView === 'users' ? (
            <UserManagement currentUserId={session.user.id} />
          ) : activeView === 'kpis' ? (
            <>
              <GlobalKpiCard />
              <HistoricalTrend />
            </>
          ) : (
            <>
              <div className="signal-card">
                <div><p className="eyebrow">Punto de partida</p><h2>{activeView === 'overview' ? 'Tu panel está listo.' : activeMenuItem.label}</h2><p>{activeView === 'overview' ? 'Elige una vista para comenzar a trabajar con los resultados Saber Pro.' : 'Esta sección está disponible según tu rol. Selecciona otra opción para cambiar de módulo.'}</p></div>
                <div className="signal-orbit"><FiActivity aria-hidden="true" /></div>
              </div>
              <div className="metric-row">
                <div><small>Acceso actual</small><strong>{session.user.role}</strong></div>
                <div><small>Estado de sesión</small><strong className="online">Activo <FiCheckCircle aria-hidden="true" /></strong></div>
                <div><small>Próximo paso</small><strong>Explorar datos <FiArrowRight aria-hidden="true" /></strong></div>
              </div>
            </>
          )}
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
