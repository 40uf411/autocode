const getDefaultBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  // Use the dev proxy prefix in development to avoid browser CORS failures.
  if (import.meta.env.DEV) {
    return '/api'
  }

  return 'http://127.0.0.1:8000'
}

export const API_BASE_URL = getDefaultBaseUrl()

export const LOGIN_ENDPOINT = import.meta.env.VITE_LOGIN_ENDPOINT ?? '/auth/token'
export const PING_ENDPOINT = import.meta.env.VITE_PING_ENDPOINT ?? '/system/ping'
export const SCHEMA_ENDPOINT = import.meta.env.VITE_SCHEMA_ENDPOINT ?? '/system/schema'
