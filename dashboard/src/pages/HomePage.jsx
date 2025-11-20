import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { API_BASE_URL, PING_ENDPOINT, SCHEMA_ENDPOINT } from '../config/api'
import { useAuth } from '../context/AuthContext'
import { humanizeResource } from '../utils/text'
import './HomePage.css'

const createFallbackTable = (slug, description) => ({
  slug,
  displayName: humanizeResource(slug),
  description,
  columns: [],
  indexes: [],
})

const FALLBACK_TABLES = [
  createFallbackTable('users', 'Manage user accounts, access levels, and lifecycle.'),
  createFallbackTable('roles', 'Control fine-grained permissions for each role.'),
  createFallbackTable('privileges', 'Audit and adjust privilege matrices.'),
]

const HomePage = () => {
  const navigate = useNavigate()
  const { token, user, logout } = useAuth()
  const [tables, setTables] = useState(FALLBACK_TABLES)
  const [loading, setLoading] = useState(true)
  const [schemaError, setSchemaError] = useState('')
  const [tableCount, setTableCount] = useState(null)
  const [ping, setPing] = useState(null)
  const [pingTime, setPingTime] = useState(null)
  const [pingError, setPingError] = useState('')
  const userEmail = user?.email ?? 'admin@example.com'
  const initials = useMemo(() => {
    if (!userEmail) return 'A'
    const [namePart] = userEmail.split('@')
    return (
      namePart
        .split(/[._-]/)
        .filter(Boolean)
        .slice(0, 2)
        .map((chunk) => chunk[0]?.toUpperCase())
        .join('') || userEmail[0].toUpperCase()
    )
  }, [userEmail])

  useEffect(() => {
    if (!token) {
      return
    }

    let ignore = false
    const controller = new AbortController()

    const loadSchema = async () => {
      try {
        setLoading(true)
        setSchemaError('')
        const response = await fetch(`${API_BASE_URL}${SCHEMA_ENDPOINT}`, {
          method: 'GET',
          signal: controller.signal,
          headers: { Authorization: `Bearer ${token}` },
        })

        if (!response.ok) {
          throw new Error(`Unable to load schema (status ${response.status})`)
        }

        const payload = await response.json()
        if (ignore) return

        const tablesPayload = Array.isArray(payload.tables) ? payload.tables : []
        const mappedTables = tablesPayload.map((table) => {
          const columnCount = table.columns?.length ?? 0
          const indexCount = table.indexes?.length ?? 0
          const friendlyName = humanizeResource(table.name)
          return {
            slug: table.name,
            displayName: friendlyName,
            description: `${columnCount} column${columnCount === 1 ? '' : 's'} | ${indexCount} index${
              indexCount === 1 ? '' : 'es'
            }`,
            columns: table.columns ?? [],
            indexes: table.indexes ?? [],
            raw: table,
          }
        })

        setTables(mappedTables.length ? mappedTables : FALLBACK_TABLES)
        setTableCount(payload.table_count ?? tablesPayload.length ?? FALLBACK_TABLES.length)
      } catch (specError) {
        if (ignore || specError.name === 'AbortError') return
        setSchemaError(specError.message)
        setTables(FALLBACK_TABLES)
        setTableCount(null)
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    loadSchema()

    return () => {
      ignore = true
      controller.abort()
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      return
    }

    let ignore = false
    const controller = new AbortController()

    const requestPing = async () => {
      try {
        setPingError('')
        const start = typeof performance !== 'undefined' ? performance.now() : Date.now()
        const response = await fetch(`${API_BASE_URL}${PING_ENDPOINT}`, {
          method: 'GET',
          signal: controller.signal,
          headers: { Authorization: `Bearer ${token}` },
        })
        const end = typeof performance !== 'undefined' ? performance.now() : Date.now()
        if (!response.ok) {
          throw new Error(`Ping failed with status ${response.status}`)
        }

        const payload = await response.json()
        if (ignore) return
        setPing(payload)
        setPingTime(Math.max(0, Math.round(end - start)))
      } catch (pingErr) {
        if (ignore || pingErr.name === 'AbortError') return
        setPing(null)
        setPingError('Unable to reach server ping endpoint.')
        setPingTime(null)
      }
    }
    requestPing()

    return () => {
      ignore = true
      controller.abort()
    }
  }, [token])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const tableMap = useMemo(() => {
    return tables.reduce((acc, table) => {
      acc[table.slug] = table
      return acc
    }, {})
  }, [tables])

  const outletContextValue = useMemo(
    () => ({
      tables,
      tableMap,
      tableCount,
      ping,
      pingTime,
      pingError,
    }),
    [tables, tableMap, tableCount, ping, pingError, pingTime]
  )

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="sidebar-header">
          <p className="sidebar-eyebrow">Administration</p>
          <h2>Control Center</h2>
        </div>

        <div className="sidebar-list">
          {loading && <p className="sidebar-state">Loading tables...</p>}
          {!loading && schemaError && <p className="sidebar-error">{schemaError}</p>}
          {!loading &&
            !schemaError &&
            tables.map((table) => (
              <NavLink
                key={table.slug}
                to={`/tables/${table.slug}`}
                className={({ isActive }) =>
                  ['sidebar-item', isActive ? 'sidebar-item-active' : ''].filter(Boolean).join(' ')
                }
              >
                <div className="dot" />
                <div>
                  <p className="item-title">{table.displayName}</p>
                  <p className="item-description">{table.description}</p>
                </div>
              </NavLink>
            ))}
        </div>

        <button type="button" className="sidebar-footer" onClick={handleLogout}>
          <div className="avatar">{initials}</div>
          <div>
            <p className="footer-label">Signed in as</p>
            <div className="footer-text">
              <p className="footer-email">{userEmail}</p>
              <p className="footer-logout">Logout</p>
            </div>
          </div>
        </button>
      </aside>

      <main className="dashboard-content">
        <Outlet context={outletContextValue} />
      </main>
    </div>
  )
}

export default HomePage
