import React, { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const AuthCallback = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { handleGoogleCallback } = useAuth()

  useEffect(() => {
    const token = searchParams.get('token')

    if (token) {
      handleGoogleCallback(token).then((result) => {
        if (result.success) {
          navigate('/inventory', { replace: true })
        } else {
          navigate('/signin?error=google_auth_failed', { replace: true })
        }
      })
    } else {
      navigate('/signin?error=no_token', { replace: true })
    }
  }, [searchParams, navigate, handleGoogleCallback])

  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center gap-6 bg-[#5C6E43] text-[#F2CEC2]">
      <h2 className="text-xl font-semibold">Authenticating with Google...</h2>
      <div
        className="w-12 h-12 rounded-full border-4 border-[#F2CEC2]/30 border-t-[#F2CEC2] animate-spin"
        aria-hidden
      />
      <p className="text-[#F2CEC2]/90">Please wait while we complete your login.</p>
    </div>
  )
}

export default AuthCallback
