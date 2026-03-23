import React, { useState } from 'react'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { FiEye, FiEyeOff } from 'react-icons/fi'
import { FaGoogle } from 'react-icons/fa'
import loginImage from '../assets/login.svg'
import { useAuth } from '../context/AuthContext'
import Loader, { LoaderSpinner } from '../components/Loader'

const SignIn = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const navigate = useNavigate()
  const { login, loginWithGoogle, isAuthenticated, loading: authLoading } = useAuth()

  if (authLoading) return <Loader fullscreen />
  if (isAuthenticated) return <Navigate to="/inventory" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const result = await login(username.trim(), password)
    setLoading(false)
    if (result.success) {
      navigate('/inventory', { replace: true })
    } else {
      setError(result.error || 'Login failed')
    }
  }

  const handleGoogleLogin = () => {
    loginWithGoogle()
  }

  return (
    <div className='fixed inset-0 overflow-hidden'>
      <img
        src={loginImage}
        alt="login"
        className='h-full w-full min-h-full min-w-full object-cover object-center'
      />
      <div className='absolute inset-0 z-10 flex items-center'>
        <div className='w-full max-w-lg px-10 md:px-14 -ml-6 lg:ml-16'>
          <h1 className='text-[#F2CEC2] text-2xl md:text-3xl font-semibold mb-1'>
            Welcome back!
          </h1>
          <p className='text-[#F2CEC2] text-2xl md:text-3xl mb-8'>
            Glad to see you again :)
          </p>
          {error && (
            <p className='mb-4 text-red-200 text-sm bg-red-900/40 px-4 py-2 rounded-lg'>
              {error}
            </p>
          )}
          <form className='flex flex-col gap-5' onSubmit={handleSubmit}>
            <div>
              <label htmlFor='username' className='block text-[#F2CEC2] text-base font-medium mb-2 ml-4'>
                Email / Username
              </label>
              <input
                id='username'
                type='text'
                placeholder='Enter your email or username'
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete='username'
                disabled={loading}
                className='w-full px-4 py-2 rounded-full border border-[#F2CEC2] text-[#F2CEC2] placeholder-[#F2CEC2]/80 focus:outline-none focus:ring-2 focus:ring-[#F2CEC2]/50 bg-transparent'
              />
            </div>
            <div>
              <label htmlFor='password' className='block text-[#F2CEC2] text-base font-medium mb-2 ml-4'>
                Password
              </label>
              <div className='relative'>
                <input
                  id='password'
                  type={showPassword ? 'text' : 'password'}
                  placeholder='Enter your password'
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete='current-password'
                  disabled={loading}
                  className='w-full px-4 py-2 pr-12 rounded-full border border-[#F2CEC2] text-[#F2CEC2] placeholder-[#F2CEC2]/80 focus:outline-none focus:ring-2 focus:ring-[#F2CEC2]/50 bg-transparent'
                />
                <button
                  type='button'
                  onClick={() => setShowPassword((prev) => !prev)}
                  className='absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#F2CEC2] hover:text-[#f2cec2]/80 focus:outline-none rounded cursor-pointer'
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
                </button>
              </div>
            </div>
            <button
              type='submit'
              disabled={loading}
              className='w-full max-w-[150px] mx-auto py-3 rounded-full font-semibold text-[#5C6E43] bg-gradient-to-r from-[#F3BD8C] to-[#E69695] hover:opacity-95 transition-opacity cursor-pointer disabled:opacity-70 inline-flex items-center justify-center gap-2 min-h-[48px]'
            >
              {loading ? (
                <>
                  <span className="inline-flex scale-[0.72] origin-center" aria-hidden>
                    <LoaderSpinner size="xs" color="#1a1a1a" />
                  </span>
                  <span>Logging In</span>
                </>
              ) : (
                'Log In'
              )}
            </button>
          </form>
          <div className='flex items-center gap-3 my-5'>
            <span className='flex-1 h-px bg-[#F2CEC2]/60' />
            <span className='text-[#F2CEC2] text-sm'>or</span>
            <span className='flex-1 h-px bg-[#F2CEC2]/60' />
          </div>
          <button
            type='button'
            onClick={handleGoogleLogin}
            disabled={loading}
            className='w-full py-3 rounded-full font-semibold text-[#637848] bg-[#C4D3B6] hover:opacity-95 border border-[#a9c4a8]/80 cursor-pointer flex items-center justify-center gap-2 disabled:opacity-70'
          >
            <FaGoogle size={20} /> Continue with Google
          </button>
          <p className='text-[#F2CEC2] text-sm mt-6 text-center mx-auto'>
            Don&apos;t have an account?{' '}
            <Link to='/signup' className='hover:underline font-medium hover:text-[#F3BD8C]'>
              Sign Up
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default SignIn
