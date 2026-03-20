import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#5C6E43]/90 text-[#F2CEC2]">
        <p>Loading...</p>
      </div>
    )
  }

  return isAuthenticated ? children : <Navigate to="/signin" replace />
}

export default PrivateRoute
