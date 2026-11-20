import { FormEvent, useEffect, useRef, useState } from 'react'
import { FiActivity, FiAlertCircle, FiArrowRight, FiArrowUpRight, FiBarChart2, FiCheckCircle, FiDatabase, FiDownload, FiEye, FiEyeOff, FiFileText, FiLoader, FiLock, FiLogOut, FiMail, FiMenu, FiPieChart, FiShield, FiSliders, FiTrendingUp, FiUsers, FiX } from 'react-icons/fi'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { ComposableMap, Geographies, Geography, ZoomableGroup } from 'react-simple-maps'
import { authHeaders, clearSession, getSession, login } from './services/authApi'
import { getGlobalKpi, listPeriods, type GlobalKpi } from './services/kpisApi'
import {
  getHistoricalTrend,
  getCompetencyComparison,
  getInstitutionRankings,
  getDepartmentDistribution,
  listYearOptions,
  listComparisonOptions,
  getStratumPerformance,
  listTrendFilterOptions,
  TREND_FILTERS,
  type HistoricalPoint,
  type CompetencyComparison,
  type InstitutionRanking,
  type InstitutionRankings,
  type DepartmentResult,
  type TrendFilterKey,
  type TrendFilterOptions,
  type TrendFilters,
  type StratumPerformance,
} from './services/historicalApi'
import {
  createManagedUser,
  listManagedUsers,
  updateManagedUser,
  type ManagedUser,
} from './services/usersApi'
import {
  listPredictionFilterOptions,
  predictPerformance,
  type PredictionInput,
  type PredictionResult,
  type PredictionFilterOptions,
} from './services/predictionApi'
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

function StratumPerformanceChart() {
  const [data, setData] = useState<StratumPerformance[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    getStratumPerformance(controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setError(reason instanceof Error ? reason.message : 'No fue posible consultar el desempeño por estrato.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  const width = 760
  const height = 280
  const left = 54
  const right = 18
  const top = 20
  const bottom = 42
  const chartHeight = height - top - bottom
  const chartWidth = width - left - right
  const slotWidth = data.length ? chartWidth / data.length : chartWidth
  const barWidth = Math.min(56, slotWidth * 0.55)

  return (
    <section className="stratum-chart-card" aria-labelledby="stratum-chart-title">
      <header>
        <p className="eyebrow">Brecha socioeconómica</p>
        <h2 id="stratum-chart-title">Promedio global por estrato</h2>
        <p>Promedio de las cinco competencias y número de estudiantes en cada estrato.</p>
      </header>
      {error ? (
        <p className="trend-message is-error" role="alert">{error}</p>
      ) : loading ? (
        <p className="trend-message" role="status">Cargando desempeño por estrato...</p>
      ) : data.length === 0 ? (
        <p className="trend-message" role="status">No hay registros con estrato socioeconómico válido.</p>
      ) : (
        <>
          <div className="trend-chart-wrap">
            <svg
              className="stratum-chart"
              viewBox={`0 0 ${width} ${height}`}
              role="img"
              aria-labelledby="stratum-chart-title stratum-chart-description"
            >
              <desc id="stratum-chart-description">
                Gráfico de barras con el promedio global de Saber Pro para los estratos socioeconómicos del uno al seis.
              </desc>
              {[0, 100, 200, 300].map((score) => {
                const y = top + chartHeight - (score / 300) * chartHeight
                return (
                  <g key={score}>
                    <line x1={left} x2={width - right} y1={y} y2={y} className="trend-gridline" />
                    <text x={left - 10} y={y + 4} textAnchor="end" className="trend-axis-label">{score}</text>
                  </g>
                )
              })}
              {data.map((point, index) => {
                const barHeight = (point.promedio_global / 300) * chartHeight
                const x = left + index * slotWidth + (slotWidth - barWidth) / 2
                const y = top + chartHeight - barHeight
                return (
                  <g key={point.estrato}>
                    <rect x={x} y={y} width={barWidth} height={barHeight} rx="3" className="stratum-bar">
                      <title>{`${point.estrato}: ${point.promedio_global.toFixed(2)} puntos; ${point.total_registros.toLocaleString('es-CO')} estudiantes`}</title>
                    </rect>
                    <text x={x + barWidth / 2} y={height - 13} textAnchor="middle" className="trend-axis-label">{point.estrato.replace('Estrato ', '')}</text>
                    <text x={x + barWidth / 2} y={y - 7} textAnchor="middle" className="stratum-value-label">{point.promedio_global.toFixed(1)}</text>
                  </g>
                )
              })}
            </svg>
          </div>
          <div className="trend-table-wrap">
            <table className="trend-table">
              <thead><tr><th>Estrato</th><th>Promedio global</th><th>Estudiantes</th></tr></thead>
              <tbody>
                {data.map((point) => (
                  <tr key={point.estrato}>
                    <td>{point.estrato}</td>
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

const COMPETENCIES = [
  { key: 'razonamiento', label: 'Razonamiento' },
  { key: 'lectura', label: 'Lectura crítica' },
  { key: 'ciudadanas', label: 'Competencias ciudadanas' },
  { key: 'escrita', label: 'Comunicación escrita' },
  { key: 'ingles', label: 'Inglés' },
] as const

function CompetencyComparisonChart() {
  const [institutions, setInstitutions] = useState<string[]>([])
  const [groups, setGroups] = useState<string[]>([])
  const [institution, setInstitution] = useState('')
  const [referenceGroup, setReferenceGroup] = useState('')
  const [comparison, setComparison] = useState<CompetencyComparison | null>(null)
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [loadingComparison, setLoadingComparison] = useState(false)
  const [optionsError, setOptionsError] = useState('')
  const [comparisonError, setComparisonError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    listComparisonOptions(controller.signal)
      .then(({ instituciones, grupos }) => {
        setInstitutions(instituciones)
        setGroups(grupos)
        setInstitution(instituciones[0] ?? '')
        setReferenceGroup(grupos[0] ?? '')
        if (instituciones.length === 0 || grupos.length === 0) {
          setOptionsError('Se requiere al menos una institución y un grupo de referencia.')
        }
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setOptionsError(reason instanceof Error ? reason.message : 'No fue posible cargar las opciones.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingOptions(false)
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (loadingOptions || optionsError || !institution || !referenceGroup) return
    const controller = new AbortController()
    setLoadingComparison(true)
    setComparisonError('')
    getCompetencyComparison(institution, referenceGroup, controller.signal)
      .then(setComparison)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setComparisonError(reason instanceof Error ? reason.message : 'No fue posible calcular la comparación.')
          setComparison(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingComparison(false)
      })
    return () => controller.abort()
  }, [institution, loadingOptions, optionsError, referenceGroup])

  const chartWidth = 720
  const chartHeight = 370
  const centerX = 360
  const centerY = 178
  const radius = 122
  const axes = COMPETENCIES.map((competency, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / COMPETENCIES.length
    const x = centerX + Math.cos(angle) * radius
    const y = centerY + Math.sin(angle) * radius
    const labelX = centerX + Math.cos(angle) * (radius + 34)
    const labelY = centerY + Math.sin(angle) * (radius + 34)
    return { ...competency, angle, x, y, labelX, labelY }
  })
  const getPolygonPoints = (values: Record<string, number>) =>
    COMPETENCIES.map(({ key }, index) => {
      const angle = axes[index].angle
      const value = Math.max(0, Math.min(300, values[key] ?? 0))
      const valueRadius = (value / 300) * radius
      return `${centerX + Math.cos(angle) * valueRadius},${centerY + Math.sin(angle) * valueRadius}`
    }).join(' ')

  return (
    <section className="competency-comparison" aria-labelledby="competency-comparison-title">
      <header>
        <p className="eyebrow">Referencia académica</p>
        <h2 id="competency-comparison-title">Competencias frente al promedio nacional</h2>
        <p>Compara una institución con el total nacional de su grupo de referencia.</p>
      </header>
      <div className="comparison-selectors">
        <label htmlFor="comparison-institution">
          Institución
          <select
            id="comparison-institution"
            value={institution}
            onChange={(event) => setInstitution(event.target.value)}
            disabled={loadingOptions || institutions.length === 0}
          >
            {institutions.map((value) => <option value={value} key={value}>{value}</option>)}
          </select>
        </label>
        <label htmlFor="comparison-reference-group">
          Grupo de referencia
          <select
            id="comparison-reference-group"
            value={referenceGroup}
            onChange={(event) => setReferenceGroup(event.target.value)}
            disabled={loadingOptions || groups.length === 0}
          >
            {groups.map((value) => <option value={value} key={value}>{value}</option>)}
          </select>
        </label>
      </div>
      {optionsError ? (
        <p className="trend-message is-error" role="alert">{optionsError}</p>
      ) : loadingOptions || loadingComparison ? (
        <p className="trend-message" role="status">Calculando promedios por competencia...</p>
      ) : comparisonError ? (
        <p className="trend-message is-error" role="alert">{comparisonError}</p>
      ) : comparison ? (
        <>
          <div className="comparison-legend" aria-label="Leyenda del gráfico">
            <span><i className="legend-institution" />{comparison.institucion}</span>
            <span><i className="legend-national" />Promedio nacional: {comparison.grupo_referencia}</span>
          </div>
          <div className="comparison-chart-wrap">
            <svg
              className="comparison-chart"
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              role="img"
              aria-labelledby="competency-comparison-title competency-comparison-description"
            >
              <desc id="competency-comparison-description">
                Gráfico radar con cinco competencias. Compara los promedios de la institución seleccionada con el promedio nacional del grupo de referencia.
              </desc>
              {[0.25, 0.5, 0.75, 1].map((fraction) => {
                const points = axes.map(({ angle }) =>
                  `${centerX + Math.cos(angle) * radius * fraction},${centerY + Math.sin(angle) * radius * fraction}`,
                ).join(' ')
                return <polygon key={fraction} points={points} className="comparison-grid" />
              })}
              {axes.map((axis) => (
                <g key={axis.key}>
                  <line x1={centerX} y1={centerY} x2={axis.x} y2={axis.y} className="comparison-axis" />
                  <text x={axis.labelX} y={axis.labelY} textAnchor="middle" className="comparison-label">{axis.label}</text>
                </g>
              ))}
              <polygon points={getPolygonPoints(comparison.promedios_nacionales)} className="comparison-polygon national" />
              <polygon points={getPolygonPoints(comparison.promedios_institucion)} className="comparison-polygon institution" />
              {axes.map((axis) => {
                const institutionScore = comparison.promedios_institucion[axis.key] ?? 0
                const nationalScore = comparison.promedios_nacionales[axis.key] ?? 0
                const scoreRadius = (score: number) => (Math.max(0, Math.min(300, score)) / 300) * radius
                return (
                  <g key={`${axis.key}-points`}>
                    <circle
                      cx={centerX + Math.cos(axis.angle) * scoreRadius(nationalScore)}
                      cy={centerY + Math.sin(axis.angle) * scoreRadius(nationalScore)}
                      r="4"
                      className="comparison-point national"
                    >
                      <title>{`Nacional ${axis.label}: ${nationalScore.toFixed(2)}`}</title>
                    </circle>
                    <circle
                      cx={centerX + Math.cos(axis.angle) * scoreRadius(institutionScore)}
                      cy={centerY + Math.sin(axis.angle) * scoreRadius(institutionScore)}
                      r="4"
                      className="comparison-point institution"
                    >
                      <title>{`${comparison.institucion} ${axis.label}: ${institutionScore.toFixed(2)}`}</title>
                    </circle>
                  </g>
                )
              })}
            </svg>
          </div>
          <div className="trend-table-wrap">
            <table className="trend-table">
              <thead><tr><th>Competencia</th><th>{comparison.institucion}</th><th>Promedio nacional</th></tr></thead>
              <tbody>
                {COMPETENCIES.map(({ key, label }) => (
                  <tr key={key}>
                    <td>{label}</td>
                    <td>{comparison.promedios_institucion[key].toFixed(2)}</td>
                    <td>{comparison.promedios_nacionales[key].toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="comparison-records">
            Registros: {comparison.total_institucion.toLocaleString('es-CO')} en la institución · {comparison.total_nacional.toLocaleString('es-CO')} en el grupo nacional.
          </p>
        </>
      ) : null}
    </section>
  )
}

function normalizeDepartment(value: string): string {
  const normalized = value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
  if (normalized.includes('bogota') && normalized.includes('d.c')) return 'bogota d.c.'
  if (normalized.includes('archipielago de san andres')) return 'san andres y providencia'
  return normalized
}

function DepartmentMap() {
  const [filters, setFilters] = useState<TrendFilters>(EMPTY_TREND_FILTERS)
  const [years, setYears] = useState<string[]>([])
  const [data, setData] = useState<DepartmentResult[]>([])
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [loadingMap, setLoadingMap] = useState(false)
  const [optionsError, setOptionsError] = useState('')
  const [mapError, setMapError] = useState('')
  const [selectedDepartment, setSelectedDepartment] = useState('')
  const [zoom, setZoom] = useState(1)

  useEffect(() => {
    const controller = new AbortController()
    listYearOptions(controller.signal)
      .then(setYears)
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
    setLoadingMap(true)
    setMapError('')
    getDepartmentDistribution(filters, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setMapError(reason instanceof Error ? reason.message : 'No fue posible consultar la distribución geográfica.')
          setData([])
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingMap(false)
      })
    return () => controller.abort()
  }, [filters, loadingOptions, optionsError])

  const values = data.map((item) => item.promedio_global)
  const minimum = values.length ? Math.min(...values) : 0
  const maximum = values.length ? Math.max(...values) : 300
  const range = maximum - minimum || 1
  const scoreColor = (score: number) => {
    const ratio = Math.max(0, Math.min(1, (score - minimum) / range))
    if (ratio >= 0.75) return '#1f6a5a'
    if (ratio >= 0.5) return '#4d8b70'
    if (ratio >= 0.25) return '#d2a95f'
    return '#bd6652'
  }
  const byDepartment = new Map(
    data.map((item) => [normalizeDepartment(item.departamento), item]),
  )
  const selected = selectedDepartment
    ? byDepartment.get(normalizeDepartment(selectedDepartment))
    : null

  function updateFilter(key: TrendFilterKey, value: string) {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="department-map" aria-labelledby="department-map-title">
      <header>
        <p className="eyebrow">Disparidades territoriales</p>
        <h2 id="department-map-title">Puntaje promedio por departamento</h2>
        <p>Selecciona una región para consultar su promedio y haz zoom sobre el mapa.</p>
      </header>

      <div className="department-controls">
        <label htmlFor="department-year">
          Año
          <select
            id="department-year"
            value={filters.anio}
            onChange={(event) => updateFilter('anio', event.target.value)}
            disabled={loadingOptions || optionsError !== ''}
          >
            <option value="">Todos los años</option>
            {years.map((year) => <option value={year} key={year}>{year}</option>)}
          </select>
        </label>
      </div>

      <div className="department-map-toolbar" aria-label="Controles del mapa">
        <button type="button" onClick={() => setZoom((current) => Math.max(1, current - 0.25))} disabled={zoom <= 1}>−</button>
        <span>{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => setZoom((current) => Math.min(2, current + 0.25))} disabled={zoom >= 2}>+</button>
        {selectedDepartment && <button type="button" className="department-reset" onClick={() => { setSelectedDepartment(''); setZoom(1) }}>Restablecer</button>}
      </div>

      {optionsError ? (
        <p className="trend-message is-error" role="alert">{optionsError}</p>
      ) : loadingOptions || loadingMap ? (
        <p className="trend-message" role="status">Cargando distribución geográfica...</p>
      ) : (
        <>
          {mapError && <p className="trend-message is-error" role="alert">{mapError}</p>}
          <div className="department-map-layout">
          <div className={`department-map-viewport${zoom >= 1.5 ? ' is-pannable' : ''}`}>
            <ComposableMap
              width={800}
              height={600}
              projection="geoMercator"
              projectionConfig={{ center: [-74, 4], scale: 1900 }}
              role="img"
              aria-label="Mapa de Colombia coloreado por puntaje promedio por departamento"
              className="department-map-svg"
            >
              <ZoomableGroup
                key={zoom}
                center={[-74, 4]}
                zoom={zoom}
                minZoom={1}
                maxZoom={2}
                filterZoomEvent={(event) => !('button' in event) || event.button === 0}
              >
                <Geographies geography="/geo/colombia-departamentos.geojson">
                  {({ geographies }) =>
                    geographies.map((geography) => {
                      const departmentName = normalizeDepartment(
                        String((geography.properties as Record<string, unknown>)?.dpto_nombre ?? ''),
                      )
                      const item = byDepartment.get(departmentName)
                      const isSelected =
                        Boolean(selectedDepartment) &&
                        normalizeDepartment(selectedDepartment) === departmentName
                      return (
                        <Geography
                          key={geography.rsmKey}
                          geography={geography}
                          role="button"
                          tabIndex={item ? 0 : -1}
                          aria-label={
                            item
                              ? `${item.departamento}: ${item.promedio_global.toFixed(2)} puntos`
                              : departmentName
                          }
                          className={`department-geography${isSelected ? ' is-selected' : ''}`}
                          fill={item ? scoreColor(item.promedio_global) : '#e7ebe5'}
                          onClick={() => item && setSelectedDepartment(item.departamento)}
                          onKeyDown={(event) => {
                            if (item && (event.key === 'Enter' || event.key === ' ')) {
                              event.preventDefault()
                              setSelectedDepartment(item.departamento)
                            }
                          }}
                        >
                          {item && (
                            <title>{`${item.departamento}: ${item.promedio_global.toFixed(2)} puntos; ${item.total_registros.toLocaleString('es-CO')} registros`}</title>
                          )}
                        </Geography>
                      )
                    })
                  }
                </Geographies>
              </ZoomableGroup>
            </ComposableMap>
            </div>
          <aside className="department-detail" aria-live="polite">
            <small>Detalle seleccionado</small>
            {selected ? (
              <>
                <strong>{selected.departamento}</strong>
                <span>{selected.promedio_global.toFixed(2)} puntos</span>
                <p>{selected.total_registros.toLocaleString('es-CO')} estudiantes evaluados</p>
              </>
            ) : (
              <>
                <strong>Colombia</strong>
                <span>{values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2) : '—'} puntos</span>
                <p>{data.reduce((sum, item) => sum + item.total_registros, 0).toLocaleString('es-CO')} estudiantes evaluados</p>
              </>
            )}
            <div className="department-scale">
              <span style={{ background: '#bd6652' }} /> Bajo
              <span style={{ background: '#d2a95f' }} /> Medio
              <span style={{ background: '#4d8b70' }} /> Alto
              <span style={{ background: '#1f6a5a' }} /> Sobresaliente
            </div>
          </aside>
          </div>
        </>
      )}
    </section>
  )
}

function InstitutionRankingChart() {
  const [type, setType] = useState<InstitutionRankings['tipo']>('OFICIAL')
  const [rankings, setRankings] = useState<InstitutionRankings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    getInstitutionRankings(type, controller.signal)
      .then(setRankings)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setError(reason instanceof Error ? reason.message : 'No fue posible calcular el ranking.')
          setRankings(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [type])

  const chart = (title: string, entries: InstitutionRanking[]) => {
    const chartWidth = 680
    const labelWidth = 300
    const rowHeight = 34
    const chartHeight = Math.max(70, entries.length * rowHeight + 20)
    return (
      <div className="ranking-panel">
        <h3>{title}</h3>
        {entries.length === 0 ? <p className="trend-message">No hay instituciones para mostrar.</p> : (
          <>
            <div className="ranking-chart-wrap">
              <svg
                className="ranking-chart"
                viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                role="img"
                aria-label={`${title} de instituciones ${type.toLowerCase()}`}
              >
                {entries.map((entry, index) => {
                  const y = index * rowHeight + 20
                  const scoreWidth = Math.max(0, (entry.promedio_global / 300) * (chartWidth - labelWidth - 24))
                  return (
                    <g key={`${entry.institucion}-${index}`}>
                      <text x="0" y={y + 13} className="ranking-label">{`${index + 1}. ${entry.institucion}`}</text>
                      <rect x={labelWidth} y={y} width={scoreWidth} height="20" rx="2" className="ranking-bar">
                        <title>{`${entry.institucion}: ${entry.promedio_global.toFixed(2)} puntos; ${entry.total_registros.toLocaleString('es-CO')} registros`}</title>
                      </rect>
                      <text x={labelWidth + scoreWidth + 6} y={y + 14} className="ranking-value">{entry.promedio_global.toFixed(1)}</text>
                    </g>
                  )
                })}
              </svg>
            </div>
            <div className="trend-table-wrap">
              <table className="trend-table">
                <thead><tr><th>Posición</th><th>Institución</th><th>Promedio</th><th>Registros</th></tr></thead>
                <tbody>{entries.map((entry, index) => (
                  <tr key={`${entry.institucion}-${index}`}>
                    <td>{index + 1}</td>
                    <td>{entry.institucion}</td>
                    <td>{entry.promedio_global.toFixed(2)}</td>
                    <td>{entry.total_registros.toLocaleString('es-CO')}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <section className="institution-ranking" aria-labelledby="institution-ranking-title">
      <header>
        <p className="eyebrow">Panorama institucional</p>
        <h2 id="institution-ranking-title">Top y Bottom 10 por tipo de IES</h2>
        <p>Ranking por promedio global de las cinco competencias, con puntajes ordenados de mayor a menor.</p>
      </header>
      <div className="ranking-type-toggle" role="group" aria-label="Tipo de institución">
        {(['OFICIAL', 'NO OFICIAL'] as const).map((value) => (
          <button
            type="button"
            className={type === value ? 'is-selected' : ''}
            aria-pressed={type === value}
            onClick={() => setType(value)}
            key={value}
          >
            {value === 'OFICIAL' ? 'IES Oficiales' : 'IES No Oficiales'}
          </button>
        ))}
      </div>
      {loading ? <p className="trend-message" role="status">Calculando rankings institucionales...</p> : error ? (
        <p className="trend-message is-error" role="alert">{error}</p>
      ) : rankings ? (
        <div className="ranking-columns">
          {chart('Top 10', rankings.top)}
          {chart('Bottom 10', rankings.bottom)}
        </div>
      ) : null}
    </section>
  )
}

const KPI_VIEWS = [
  { id: 'global', label: 'Promedio', detail: 'Vista general', icon: <FiActivity /> },
  { id: 'historical', label: 'Evolución', detail: 'Tendencia anual', icon: <FiTrendingUp /> },
  { id: 'strata', label: 'Estratos', detail: 'Brecha socioeconómica', icon: <FiPieChart /> },
  { id: 'comparison', label: 'Comparativo', detail: 'IES frente a su grupo', icon: <FiUsers /> },
  { id: 'ranking', label: 'Ranking', detail: 'Desempeño institucional', icon: <FiBarChart2 /> },
  { id: 'departments', label: 'Territorio', detail: 'Mapa por departamento', icon: <FiActivity /> },
] as const

type KpiViewId = (typeof KPI_VIEWS)[number]['id']

function KpiWorkspace({
  activeView,
  onSelectView,
}: {
  activeView: KpiViewId
  onSelectView: (view: KpiViewId) => void
}) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])
  const activeIndex = KPI_VIEWS.findIndex((view) => view.id === activeView)

  function handleTabKeyDown(event: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex = index
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % KPI_VIEWS.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + KPI_VIEWS.length) % KPI_VIEWS.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = KPI_VIEWS.length - 1
    else return

    event.preventDefault()
    onSelectView(KPI_VIEWS[nextIndex].id)
    tabRefs.current[nextIndex]?.focus()
  }

  return (
    <section className="kpi-workspace" aria-labelledby="kpi-workspace-title">
      <header className="kpi-workspace-heading">
        <div>
          <p className="eyebrow">Analítica modular</p>
          <h2 id="kpi-workspace-title">Explora los indicadores</h2>
          <p>Selecciona una vista; solo se consulta el indicador activo.</p>
        </div>
        <div className="kpi-workspace-count" aria-label={`Vista ${activeIndex + 1} de ${KPI_VIEWS.length}`}>
          <strong>{String(activeIndex + 1).padStart(2, '0')}</strong>
          <span>/ {String(KPI_VIEWS.length).padStart(2, '0')}</span>
        </div>
      </header>

      <div className="kpi-tabs" role="tablist" aria-label="Indicadores del dashboard" aria-orientation="horizontal">
        {KPI_VIEWS.map((view, index) => {
          const isSelected = view.id === activeView
          return (
            <button
              ref={(element) => { tabRefs.current[index] = element }}
              className={`kpi-tab${isSelected ? ' is-selected' : ''}`}
              id={`kpi-tab-${view.id}`}
              type="button"
              role="tab"
              aria-selected={isSelected}
              aria-controls="kpi-active-panel"
              tabIndex={isSelected ? 0 : -1}
              onClick={() => onSelectView(view.id)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
              key={view.id}
            >
              <span className="kpi-tab-icon" aria-hidden="true">{view.icon}</span>
              <span className="kpi-tab-copy">
                <strong>{view.label}</strong>
                <small>{view.detail}</small>
              </span>
              <span className="kpi-tab-index" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
            </button>
          )
        })}
      </div>

      <div
        className="kpi-tabpanel"
        id="kpi-active-panel"
        role="tabpanel"
        aria-labelledby={`kpi-tab-${activeView}`}
        tabIndex={0}
      >
        {activeView === 'global' && <GlobalKpiCard />}
        {activeView === 'historical' && <HistoricalTrend />}
        {activeView === 'strata' && <StratumPerformanceChart />}
        {activeView === 'comparison' && <CompetencyComparisonChart />}
        {activeView === 'ranking' && <InstitutionRankingChart />}
        {activeView === 'departments' && <DepartmentMap />}
      </div>
    </section>
  )
}

const INITIAL_PREDICTION_PROFILE: PredictionInput = {
  genero: 'F',
  estrato: 'Estrato 2',
  educacion_padre: 'Educación profesional completa',
  educacion_madre: 'Educación profesional completa',
  tiene_internet: 'Si',
  tiene_computador: 'Si',
  caracter_academico: 'UNIVERSIDAD',
  metodo_programa: 'PRESENCIAL',
  depto_reside: 'VALLE',
  depto_institucion: 'VALLE',
}

function ProbabilityPrediction() {
  const [profile, setProfile] = useState<PredictionInput>(INITIAL_PREDICTION_PROFILE)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [options, setOptions] = useState<PredictionFilterOptions | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listPredictionFilterOptions(controller.signal)
      .then((loadedOptions) => {
        setOptions(loadedOptions)
        setProfile((current) => ({
          ...current,
          educacion_padre: loadedOptions.educacion_padre.includes(current.educacion_padre)
            ? current.educacion_padre
            : loadedOptions.educacion_padre[0] ?? '',
          educacion_madre: loadedOptions.educacion_madre.includes(current.educacion_madre)
            ? current.educacion_madre
            : loadedOptions.educacion_madre[0] ?? '',
          caracter_academico: loadedOptions.caracter_academico.includes(current.caracter_academico)
            ? current.caracter_academico
            : loadedOptions.caracter_academico[0] ?? '',
          metodo_programa: loadedOptions.metodo_programa.includes(current.metodo_programa)
            ? current.metodo_programa
            : loadedOptions.metodo_programa[0] ?? '',
          depto_reside: loadedOptions.depto_reside.includes(current.depto_reside)
            ? current.depto_reside
            : loadedOptions.depto_reside[0] ?? '',
          depto_institucion: loadedOptions.depto_institucion.includes(current.depto_institucion)
            ? current.depto_institucion
            : loadedOptions.depto_institucion[0] ?? '',
        }))
      })
      .catch((reason) => {
        if (
          reason instanceof DOMException && reason.name === 'AbortError'
          || typeof reason === 'object'
          && reason !== null
          && 'name' in reason
          && reason.name === 'AbortError'
        ) return
        setError(reason instanceof Error ? reason.message : 'No fue posible cargar las opciones.')
      })
      .finally(() => setOptionsLoading(false))
    return () => controller.abort()
  }, [])

  function updateField(field: keyof PredictionInput, value: string) {
    setProfile((current) => ({ ...current, [field]: value }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      setResult(await predictPerformance(profile))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No fue posible calcular la probabilidad.')
    } finally {
      setLoading(false)
    }
  }

  const probability = result?.probabilidad_superar_media_nacional ?? 0

  return (
    <section className="probability-workspace" aria-labelledby="probability-title">
      <div className="probability-heading">
        <div>
          <p className="eyebrow">Inferencia probabilística</p>
          <h2 id="probability-title">Probabilidad de superar la media nacional</h2>
          <p>Define el perfil de la cohorte para estimar su riesgo y oportunidad antes de la prueba.</p>
        </div>
      </div>
      <div className="probability-layout">
        <form className="probability-form" onSubmit={submit}>
          <label>Género<select value={profile.genero} onChange={(event) => updateField('genero', event.target.value)}><option>F</option><option>M</option></select></label>
          <label>Estrato<select value={profile.estrato} onChange={(event) => updateField('estrato', event.target.value)}>{[1, 2, 3, 4, 5, 6].map((value) => <option key={value}>Estrato {value}</option>)}</select></label>
          <label>Educación del padre<select value={profile.educacion_padre} onChange={(event) => updateField('educacion_padre', event.target.value)} disabled={optionsLoading} required>{(options?.educacion_padre ?? []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Educación de la madre<select value={profile.educacion_madre} onChange={(event) => updateField('educacion_madre', event.target.value)} disabled={optionsLoading} required>{(options?.educacion_madre ?? []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Internet<select value={profile.tiene_internet} onChange={(event) => updateField('tiene_internet', event.target.value)}><option>Si</option><option>No</option></select></label>
          <label>Computador<select value={profile.tiene_computador} onChange={(event) => updateField('tiene_computador', event.target.value)}><option>Si</option><option>No</option></select></label>
          <label>Carácter académico<select value={profile.caracter_academico} onChange={(event) => updateField('caracter_academico', event.target.value)} disabled={optionsLoading} required>{(options?.caracter_academico ?? []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Metodología<select value={profile.metodo_programa} onChange={(event) => updateField('metodo_programa', event.target.value)} disabled={optionsLoading} required>{(options?.metodo_programa ?? []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Departamento de residencia<select value={profile.depto_reside} onChange={(event) => updateField('depto_reside', event.target.value)} disabled={optionsLoading} required>{(options?.depto_reside ?? []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Departamento de la institución<select value={profile.depto_institucion} onChange={(event) => updateField('depto_institucion', event.target.value)} disabled={optionsLoading} required>{(options?.depto_institucion ?? []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <button className="probability-submit" type="submit" disabled={loading || optionsLoading}>
            {loading ? <><FiLoader className="export-spinner" /> Calculando...</> : <>Estimar probabilidad <FiArrowRight /></>}
          </button>
        </form>
        <aside className="probability-result" aria-live="polite">
          {error ? (
            <p className="probability-error" role="alert"><FiAlertCircle />{error}</p>
          ) : result ? (
            <>
              <p className="probability-label">Probabilidad estimada</p>
              <strong className="probability-number">{probability.toFixed(1)}%</strong>
              <div className="probability-track" aria-hidden="true"><span style={{ width: `${probability}%` }} /></div>
              <dl>
                <div><dt>Puntaje previsto</dt><dd>{result.puntaje_predicho.toFixed(1)}</dd></div>
                <div><dt>Media nacional</dt><dd>{result.media_nacional.toFixed(1)}</dd></div>
                <div><dt>Desempeño</dt><dd>{result.nivel_desempeno}</dd></div>
              </dl>
              <p className="probability-guidance">
                {probability >= 60
                  ? 'Señal favorable. Mantén el seguimiento y refuerza las competencias con menor desempeño.'
                  : 'Señal preventiva. Prioriza refuerzo pedagógico y seguimiento cercano a esta cohorte.'}
              </p>
            </>
          ) : (
            <div className="probability-empty"><FiTrendingUp /><p>Selecciona los filtros y estima la probabilidad.</p></div>
          )}
        </aside>
      </div>
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
  const [activeKpiView, setActiveKpiView] = useState<KpiViewId>('global')
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
            <KpiWorkspace activeView={activeKpiView} onSelectView={setActiveKpiView} />
          ) : activeView === 'predictions' ? (
            <ProbabilityPrediction />
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
