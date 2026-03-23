import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Loader from './Loader'

const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <Loader fullscreen />
  }

  return isAuthenticated ? children : <Navigate to="/signin" replace />
}

export default PrivateRoute
