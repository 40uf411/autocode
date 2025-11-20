import PropTypes from 'prop-types'
import { createContext, useContext, useMemo, useState } from 'react'
import { API_BASE_URL, LOGIN_ENDPOINT } from '../config/api'

const STORAGE_TOKEN_KEY = 'dashboard-auth-token'
const STORAGE_USER_KEY = 'dashboard-auth-user'

const AuthContext = createContext()

const getStoredToken = () => {
  if (typeof window === 'undefined') {
    return null
  }

  return window.localStorage.getItem(STORAGE_TOKEN_KEY)
}

const getStoredEmail = () => {
  if (typeof window === 'undefined') {
    return null
  }

  return window.localStorage.getItem(STORAGE_USER_KEY)
}

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => getStoredToken())
  const [userEmail, setUserEmail] = useState(() => getStoredEmail())

  const persistToken = (nextToken) => {
    setToken(nextToken)
    if (typeof window !== 'undefined') {
      if (nextToken) {
        window.localStorage.setItem(STORAGE_TOKEN_KEY, nextToken)
      } else {
        window.localStorage.removeItem(STORAGE_TOKEN_KEY)
      }
    }
  }

  const persistUserEmail = (nextEmail) => {
    setUserEmail(nextEmail)
    if (typeof window !== 'undefined') {
      if (nextEmail) {
        window.localStorage.setItem(STORAGE_USER_KEY, nextEmail)
      } else {
        window.localStorage.removeItem(STORAGE_USER_KEY)
      }
    }
  }

  const login = async (email, password) => {
    const normalizedEmail = email?.trim()
    const response = await fetch(`${API_BASE_URL}${LOGIN_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ username: normalizedEmail, password }),
    })

    let payload = null
    try {
      payload = await response.json()
    } catch (error) {
      // Ignore JSON parse errors because some backends might return empty bodies.
    }

    if (!response.ok) {
      const message =
        payload?.message || payload?.detail || 'Unable to sign in. Please try again.'
      throw new Error(message)
    }

    const issuedToken =
      payload?.token || payload?.accessToken || payload?.access_token || 'authenticated'
    persistToken(issuedToken)
    persistUserEmail(normalizedEmail)
    return issuedToken
  }

  const logout = () => {
    persistToken(null)
    persistUserEmail(null)
  }

  const value = useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      token,
      user: userEmail ? { email: userEmail } : null,
      login,
      logout,
    }),
    [token, userEmail]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return ctx
}
