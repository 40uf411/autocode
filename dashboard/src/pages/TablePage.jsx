import { useEffect, useMemo, useRef, useState } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import { API_BASE_URL } from '../config/api'
import { useAuth } from '../context/AuthContext'
import { humanizeResource } from '../utils/text'

const PAGE_SIZE = 50
const RELATION_PAGE_SIZE = 100
const RELATION_LOADING_LABEL = '__RELATION_LOADING__'

const getInputType = (columnType = '') => {
  const normalized = columnType.toLowerCase()
  if (normalized.includes('bool')) {
    return 'checkbox'
  }

  if (
    normalized.includes('int') ||
    normalized.includes('num') ||
    normalized.includes('decimal') ||
    normalized.includes('double') ||
    normalized.includes('float')
  ) {
    return 'number'
  }

  if (normalized.includes('date') || normalized.includes('time')) {
    return 'datetime-local'
  }

  if (normalized.includes('text') && !normalized.includes('varchar')) {
    return 'textarea'
  }

  return 'text'
}

const formatCellValue = (value) => {
  if (value === null || value === undefined) {
    return '--'
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }

  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch (error) {
      return String(value)
    }
  }

  return String(value)
}

const TablePage = () => {
  const { tableName } = useParams()
  const isMountedRef = useRef(true)
  const previousTableSlugRef = useRef(null)
  const { token } = useAuth()
  const outletContext = useOutletContext() || {}
  const tableMap = outletContext.tableMap || {}
  const table = tableMap[tableName]

  const columns = table?.columns ?? []
  const relationColumns = useMemo(() => {
    if (!columns.length) {
      return []
    }

    return columns
      .map((column) => {
        const foreignKeys = column?.foreign_keys
        if (!Array.isArray(foreignKeys) || foreignKeys.length === 0) {
          return null
        }

        const [targetSlugRaw = ''] = foreignKeys[0].split('.')
        const targetSlug = targetSlugRaw.trim()
        if (!targetSlug) {
          return null
        }

        const targetTable = tableMap[targetSlug]
        const targetColumns = targetTable?.columns ?? []
        const primaryIndex = targetColumns.findIndex((targetColumn) => targetColumn.primary_key || targetColumn.name === 'id')
        const primaryColumn = primaryIndex >= 0 ? targetColumns[primaryIndex] : targetColumns[0]
        const displayColumn =
          primaryIndex >= 0 && targetColumns[primaryIndex + 1]
            ? targetColumns[primaryIndex + 1]
            : targetColumns.find((targetColumn) => !targetColumn.primary_key && targetColumn.name !== primaryColumn?.name) ??
              primaryColumn

        return {
          columnName: column.name,
          column,
          targetSlug,
          targetPrimaryKey: primaryColumn?.name || 'id',
          targetDisplayColumn: displayColumn?.name || primaryColumn?.name || 'id',
        }
      })
      .filter(Boolean)
  }, [columns, tableMap])

  const relationColumnMap = useMemo(() => {
    return relationColumns.reduce((acc, relation) => {
      acc[relation.columnName] = relation
      return acc
    }, {})
  }, [relationColumns])

  const editableColumns = useMemo(() => {
    return columns.filter((column) => {
      if (column.primary_key) return false
      if (column.autoincrement) return false
      if (column.server_default !== null && column.server_default !== undefined) return false
      if (column.default !== null && column.default !== undefined) return false
      if (['created_at', 'updated_at', 'deleted_at'].includes(column.name)) return false
      return true
    })
  }, [columns])

  const defaultFormState = useMemo(() => {
    return editableColumns.reduce((acc, column) => {
      const inputType = getInputType(column.type)
      if (inputType === 'checkbox') {
        acc[column.name] = false
      } else {
        acc[column.name] = ''
      }
      return acc
    }, {})
  }, [editableColumns])

  const [formValues, setFormValues] = useState(defaultFormState)
  const [formOpen, setFormOpen] = useState(true)
  const [records, setRecords] = useState([])
  const [count, setCount] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [creating, setCreating] = useState(false)
  const [refreshIndex, setRefreshIndex] = useState(0)
  const [relationOptions, setRelationOptions] = useState({})
  const [relationOptionErrors, setRelationOptionErrors] = useState({})
  const [relationValueLabels, setRelationValueLabels] = useState({})

  useEffect(() => {
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    setRelationValueLabels({})
  }, [table?.slug])

  useEffect(() => {
    if (!table?.slug) {
      return
    }

    if (previousTableSlugRef.current === table.slug) {
      return
    }

    previousTableSlugRef.current = table.slug
    setRecords([])
    setCount(null)
    setRefreshIndex((index) => index + 1)
  }, [table?.slug])

  useEffect(() => {
    setFormValues(defaultFormState)
  }, [defaultFormState])

  const primaryKeyColumn = useMemo(() => {
    return columns.find((column) => column.primary_key) || columns.find((column) => column.name === 'id')
  }, [columns])

  useEffect(() => {
    if (!token || !relationColumns.length) {
      setRelationOptions({})
      setRelationOptionErrors({})
      return
    }

    const headers = { Authorization: `Bearer ${token}` }

    const fetchOptions = async () => {
      const nextOptions = {}
      const nextErrors = {}

      await Promise.all(
        relationColumns.map(async (relation) => {
          try {
            const response = await fetch(
              `${API_BASE_URL}/${relation.targetSlug}/?page=1&per_page=${RELATION_PAGE_SIZE}`,
              {
                method: 'GET',
                headers,
              }
            )
            if (!response.ok) {
              throw new Error(`Unable to load related records for ${relation.targetSlug}`)
            }

            let payload = []
            try {
              payload = await response.json()
            } catch (parseError) {
              payload = []
            }

            const parsedItems =
              Array.isArray(payload) ?
                payload :
                payload.items ??
                payload.data ??
                payload.results ??
                []

            nextOptions[relation.columnName] = parsedItems
              .map((item) => {
                if (!item || typeof item !== 'object') {
                  return null
                }
                const value = item[relation.targetPrimaryKey]
                if (value === undefined || value === null) {
                  return null
                }
                const labelRaw = item[relation.targetDisplayColumn]
                const label = labelRaw === undefined || labelRaw === null ? `#${value}` : String(labelRaw)
                return { value, label }
              })
              .filter(Boolean)
          } catch (optionError) {
            nextOptions[relation.columnName] = []
            nextErrors[relation.columnName] = 'Unable to load related records.'
          }
        })
      )

      if (!isMountedRef.current) {
        return
      }
      setRelationOptions(nextOptions)
      setRelationOptionErrors(nextErrors)
    }

    fetchOptions()
  }, [relationColumns, token, table?.slug])

  useEffect(() => {
    if (!token || !relationColumns.length || !records.length) {
      return
    }

    const headers = { Authorization: `Bearer ${token}` }
    const requests = []
    const seen = new Set()

    records.forEach((record) => {
      relationColumns.forEach((relation) => {
        const value = record?.[relation.columnName]
        if (value === null || value === undefined) {
          return
        }

        const key = `${relation.targetSlug}:${value}`
        if (seen.has(key)) {
          return
        }
        seen.add(key)

        if (relationValueLabels[key] !== undefined) {
          return
        }

        requests.push({ key, relation, value })
      })
    })

    if (!requests.length) {
      return
    }

    setRelationValueLabels((prev) => {
      const next = { ...prev }
      requests.forEach(({ key }) => {
        next[key] = RELATION_LOADING_LABEL
      })
      return next
    })

    const fetchRelationValues = async () => {
      const updates = {}

      await Promise.all(
        requests.map(async ({ key, relation, value }) => {
          try {
            const response = await fetch(`${API_BASE_URL}/${relation.targetSlug}/${value}`, {
              method: 'GET',
              headers,
            })

            if (!response.ok) {
              throw new Error('Unable to load related record.')
            }

            let payload = null
            try {
              payload = await response.json()
            } catch (parseError) {
              payload = null
            }

            const normalizedPayload =
              payload && typeof payload === 'object'
                ? payload.data ?? payload.item ?? payload.result ?? payload
                : payload

            const labelCandidate =
              normalizedPayload && typeof normalizedPayload === 'object'
                ? normalizedPayload[relation.targetDisplayColumn]
                : null
            const label =
              labelCandidate === undefined || labelCandidate === null ? `#${value}` : String(labelCandidate)

            updates[key] = label
          } catch (relationError) {
            updates[key] = `#${value}`
          }
        })
      )

      if (!isMountedRef.current) {
        return
      }
      setRelationValueLabels((prev) => ({
        ...prev,
        ...updates,
      }))
    }

    fetchRelationValues()
  }, [records, relationColumns, token])

  useEffect(() => {
    if (!table || !token || refreshIndex === 0) {
      return
    }

    const controller = new AbortController()
    const loadRecords = async () => {
      try {
        setLoading(true)
        setError('')
        const headers = { Authorization: `Bearer ${token}` }
        const [listResponse, countResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/${table.slug}/?page=1&per_page=${PAGE_SIZE}`, {
            method: 'GET',
            headers,
            signal: controller.signal,
          }),
          fetch(`${API_BASE_URL}/${table.slug}/count`, {
            method: 'GET',
            headers,
            signal: controller.signal,
          }),
        ])

        if (!listResponse.ok) {
          throw new Error(`Unable to load ${table.displayName} records.`)
        }
        if (!countResponse.ok) {
          throw new Error(`Unable to load ${table.displayName} count.`)
        }

        let payload = []
        try {
          payload = await listResponse.json()
        } catch (parseError) {
          payload = []
        }

        const parsedRecords =
          Array.isArray(payload) ?
            payload :
            payload.items ??
            payload.data ??
            payload.results ??
            []
        setRecords(Array.isArray(parsedRecords) ? parsedRecords : [])

        let countPayload = null
        try {
          countPayload = await countResponse.json()
        } catch (parseCountError) {
          countPayload = null
        }
        if (typeof countPayload === 'number') {
          setCount(countPayload)
        } else if (typeof countPayload?.count === 'number') {
          setCount(countPayload.count)
        } else if (countPayload?.total) {
          setCount(countPayload.total)
        } else {
          setCount(null)
        }
      } catch (recordError) {
        if (recordError.name === 'AbortError') return
        setError(recordError.message)
        setRecords([])
      } finally {
        setLoading(false)
      }
    }

    loadRecords()
    return () => controller.abort()
  }, [table, token, refreshIndex])

  const handleFieldChange = (columnName, inputType, value, checked) => {
    setFormValues((prev) => ({
      ...prev,
      [columnName]: inputType === 'checkbox' ? checked : value,
    }))
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!table || !token) return
    setCreating(true)
    setActionMessage('')

    try {
      const payload = {}
      editableColumns.forEach((column) => {
        const inputType = getInputType(column.type)
        let value = formValues[column.name]
        if (inputType === 'number' && value !== '') {
          value = Number(value)
        }

        if (inputType === 'checkbox') {
          payload[column.name] = Boolean(value)
          return
        }

        if (value !== '' && value !== null && value !== undefined) {
          payload[column.name] = value
        }
      })

      const response = await fetch(`${API_BASE_URL}/${table.slug}/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        let errorDetails = null
        try {
          errorDetails = await response.json()
        } catch (parseError) {
          errorDetails = null
        }
        const detailMessage =
          errorDetails?.message ||
          errorDetails?.detail ||
          `Unable to create ${table.displayName} record.`
        throw new Error(detailMessage)
      }

      setActionMessage(`${table.displayName} record created.`)
      setFormValues(defaultFormState)
      setRefreshIndex((index) => index + 1)
    } catch (createError) {
      setActionMessage(createError.message)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (record) => {
    if (!table || !token || !primaryKeyColumn) return
    const recordId = record?.[primaryKeyColumn.name]
    if (recordId === undefined || recordId === null) {
      setActionMessage('Unable to determine record identifier for deletion.')
      return
    }

    const proceed = window.confirm(`Delete ${table.displayName} record #${recordId}?`)
    if (!proceed) {
      return
    }

    setActionMessage('')
    try {
      const response = await fetch(`${API_BASE_URL}/${table.slug}/${recordId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!response.ok) {
        throw new Error('Unable to delete the selected record.')
      }

      setActionMessage('Record deleted.')
      setRefreshIndex((index) => index + 1)
    } catch (deleteError) {
      setActionMessage(deleteError.message)
    }
  }

  const getRelationDisplayValue = (columnName, rawValue) => {
    const relation = relationColumnMap[columnName]
    if (!relation) {
      return null
    }

    if (rawValue === null || rawValue === undefined) {
      return '--'
    }

    const key = `${relation.targetSlug}:${rawValue}`
    const label = relationValueLabels[key]
    if (label === RELATION_LOADING_LABEL) {
      return `Loading #${rawValue}...`
    }
    if (label) {
      return label === `#${rawValue}` ? label : `${label} (#${rawValue})`
    }

    return `#${rawValue}`
  }

  if (!table) {
    return (
      <section className="resource-shell">
        <header className="resource-headline">
          <p className="eyebrow">Unknown resource</p>
          <h1>We could not find this table.</h1>
          <p className="lede">Select another entry from the sidebar to continue.</p>
        </header>
      </section>
    )
  }

  const recordCountLabel =
    count !== null ? `${count} total record${count === 1 ? '' : 's'}` : 'Total count unavailable'

  return (
    <>
      {(loading || creating) && (
        <div className="dashboard-toast" role="status" aria-live="polite">
          <span className="toast-spinner" aria-hidden="true" />
          <span>Loading...</span>
        </div>
      )}
      <section className="resource-shell">
        <header className="resource-headline">
          <p className="eyebrow">Database table</p>
          <h1>{table.displayName}</h1>
        <p className="lede">{table.description}</p>
        <div className="resource-meta">
          <span>{columns.length} column{columns.length === 1 ? '' : 's'}</span>
          <span>Page size: {PAGE_SIZE}</span>
          <span>{recordCountLabel}</span>
        </div>
      </header>

      <div className={`collapsible-card ${formOpen ? 'open' : 'collapsed'}`}>
        <div className="collapsible-head">
          <div>
            <p className="eyebrow">Create entry</p>
            <h2>Add a new {table.displayName} record</h2>
          </div>
          <button type="button" className="ghost-button" onClick={() => setFormOpen((state) => !state)}>
            {formOpen ? 'Hide panel' : 'Show panel'}
          </button>
        </div>
        {formOpen && (
          <form className="resource-form" onSubmit={handleCreate}>
            {editableColumns.length === 0 && (
              <p className="form-empty">No editable columns were detected for this table.</p>
            )}
            {editableColumns.map((column) => {
              const inputType = getInputType(column.type)
              const value = formValues[column.name]
              const relation = relationColumnMap[column.name]
              const relationOptionsForColumn = relation ? relationOptions[column.name] ?? [] : []
              const relationOptionError = relationOptionErrors[column.name]
              const hasLoadedRelationOptions =
                relation && Object.prototype.hasOwnProperty.call(relationOptions, column.name)
              const selectValue = value === '' || value === null || value === undefined ? '' : String(value)
              return (
                <label key={column.name} className="form-field">
                  <span className="form-label">
                    {humanizeResource(column.name)}
                    <small>{column.type}</small>
                  </span>
                  {relation ? (
                    <>
                      <select
                        name={column.name}
                        value={selectValue}
                        onChange={(event) => handleFieldChange(column.name, inputType, event.target.value)}
                        disabled={!hasLoadedRelationOptions && !relationOptionError}
                      >
                        <option value="">Select {humanizeResource(relation.targetSlug).toLowerCase()}</option>
                        {relationOptionsForColumn.map((option) => (
                          <option key={`${column.name}-${option.value}`} value={String(option.value)}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      {!relationOptionError && !hasLoadedRelationOptions && (
                        <small className="form-hint">Loading related records...</small>
                      )}
                      {relationOptionError && <small className="form-hint error">{relationOptionError}</small>}
                      {!relationOptionError && hasLoadedRelationOptions && relationOptionsForColumn.length === 0 && (
                        <small className="form-hint">No related records available.</small>
                      )}
                    </>
                  ) : inputType === 'textarea' ? (
                    <textarea
                      name={column.name}
                      value={value}
                      onChange={(event) => handleFieldChange(column.name, inputType, event.target.value)}
                      rows={3}
                      placeholder={`Enter ${humanizeResource(column.name).toLowerCase()}`}
                    />
                  ) : inputType === 'checkbox' ? (
                    <input
                      type="checkbox"
                      name={column.name}
                      checked={Boolean(value)}
                      onChange={(event) =>
                        handleFieldChange(column.name, inputType, event.target.value, event.target.checked)
                      }
                    />
                  ) : (
                    <input
                      type={inputType}
                      name={column.name}
                      value={value}
                      onChange={(event) => handleFieldChange(column.name, inputType, event.target.value)}
                      placeholder={`Enter ${humanizeResource(column.name).toLowerCase()}`}
                    />
                  )}
                </label>
              )
            })}

            <div className="form-footer">
              <button type="submit" className="primary-button" disabled={creating || editableColumns.length === 0}>
                {creating ? 'Adding...' : 'Add record'}
              </button>
              {actionMessage && <p className="form-status">{actionMessage}</p>}
            </div>
          </form>
        )}
      </div>

      <div className="records-card">
        <div className="records-head">
          <div>
            <p className="eyebrow">Records</p>
            <h2>Existing entries</h2>
          </div>
          <button className="ghost-button" type="button" onClick={() => setRefreshIndex((index) => index + 1)}>
            Refresh
          </button>
        </div>

        {error && <p className="records-error">{error}</p>}
        {loading && <p className="records-state">Loading records...</p>}
        {!loading && !records.length && !error && (
          <p className="records-state">No records found for this table.</p>
        )}

        {!loading && records.length > 0 && (
          <div className="records-table-wrapper">
            <table className="records-table">
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column.name}>
                      <span>{humanizeResource(column.name)}</span>
                      <small>{column.type}</small>
                    </th>
                  ))}
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {records.map((record, index) => {
                  const rowKey =
                    (primaryKeyColumn && record?.[primaryKeyColumn.name]) ?? `${table.slug}-${index}`
                  return (
                    <tr key={rowKey} className="records-row">
                      {columns.map((column) => {
                        const relationDisplay = getRelationDisplayValue(column.name, record[column.name])
                        return (
                          <td key={`${rowKey}-${column.name}`}>
                            {relationDisplay !== null ? relationDisplay : formatCellValue(record[column.name])}
                          </td>
                        )
                      })}
                      <td className="row-actions-cell">
                        <div className="row-actions">
                          <button type="button" className="ghost-button small" disabled>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="danger-button small"
                            onClick={() => handleDelete(record)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
    </>
  )
}

export default TablePage
