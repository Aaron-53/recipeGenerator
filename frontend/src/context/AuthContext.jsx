import React, { createContext, useState, useContext, useEffect } from 'react'
import { authAPI } from '../services/api'
import { formatApiError } from '../utils/formatApiError'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }
    try {
      const response = await authAPI.getCurrentUser()
      setUser(response.data)
      setError(null)
    } catch (err) {
      console.error('Auth check failed:', err)
      localStorage.removeItem('token')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (username, password) => {
    try {
      setError(null)
      const response = await authAPI.login(username, password)
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      const userResponse = await authAPI.getCurrentUser()
      setUser(userResponse.data)
      return { success: true }
    } catch (err) {
      const message = formatApiError(err, 'Login failed')
      setError(message)
      return { success: false, error: message }
    }
  }

  const register = async (username, password) => {
    try {
      setError(null)
      await authAPI.register(username, password)
      return await login(username, password)
    } catch (err) {
      const message = formatApiError(err, 'Registration failed')
      setError(message)
      return { success: false, error: message }
    }
  }

  const logout = async () => {
    try {
      await authAPI.logout()
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      localStorage.removeItem('token')
      setUser(null)
      setError(null)
    }
  }

  const loginWithGoogle = () => {
    authAPI.googleLogin()
  }

  const handleGoogleCallback = async (token) => {
    try {
      localStorage.setItem('token', token)
      const userResponse = await authAPI.getCurrentUser()
      setUser(userResponse.data)
      return { success: true }
    } catch (err) {
      const message = formatApiError(err, 'Google login failed')
      setError(message)
      return { success: false, error: message }
    }
  }

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    loginWithGoogle,
    handleGoogleCallback,
    isAuthenticated: !!user,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
