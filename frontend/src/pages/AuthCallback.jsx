import React, { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LoaderSpinner } from '../components/Loader'

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
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 bg-[#5C6E43] px-6 text-center text-[#F2CEC2]"
      role="status"
      aria-busy="true"
      aria-live="polite"
      aria-label="Authenticating with Google"
    >
      <h2 className="text-xl font-semibold sm:text-2xl">Authenticating with Google...</h2>
      <LoaderSpinner size="md" color="#F2CEC2" />
      <p className="max-w-md text-sm text-[#F2CEC2]/90 sm:text-base">
        Please wait while we complete your login.
      </p>
    </div>
  )
}

export default AuthCallback
