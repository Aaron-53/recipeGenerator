import React, { useState } from 'react'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { FiEye, FiEyeOff } from 'react-icons/fi'
import signupImage from '../assets/signup_bg.svg'
import { FaGoogle } from 'react-icons/fa'
import { useAuth } from '../context/AuthContext'
import Loader, { LoaderSpinner } from '../components/Loader'
import ErrorBanner from '../components/ErrorBanner'

const SignUp = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showRepeatPassword, setShowRepeatPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const navigate = useNavigate()
  const { register, loginWithGoogle, isAuthenticated, loading: authLoading } = useAuth()

  if (authLoading) return <Loader fullscreen />
  if (isAuthenticated) return <Navigate to="/inventory" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== repeatPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    const result = await register(username.trim(), password)
    setLoading(false)
    if (result.success) {
      navigate('/inventory', { replace: true })
    } else {
      setError(result.error || 'Registration failed')
    }
  }

  const handleGoogleSignUp = () => {
    loginWithGoogle()
  }

  return (
    <div className='fixed inset-0 overflow-x-hidden'>
      <img
        src={signupImage}
        alt="signup"
        className='h-full w-full min-h-full min-w-full object-cover object-center -ml-24'
      />
      <div className='absolute min-h-screen inset-0 z-10 flex items-center justify-end pt-70 md:pt-0'>
        <div className='w-full max-w-[600px] px-6 md:px-14 lg:px-16 lg:mr-16'>
          <h1 className='text-[#F2CEC2] text-2xl md:text-3xl font-semibold mb-1'>
            Hello!
          </h1>
          <p className='text-[#F2CEC2] text-2xl md:text-3xl mb-12'>
            We are glad to see you :)
          </p>
          <ErrorBanner
            message={error}
            onDismiss={() => setError('')}
            variant="auth"
            className="mb-4 px-4"
          />
          <form className='flex flex-col gap-5' onSubmit={handleSubmit}>
            <button
              type='button'
              onClick={handleGoogleSignUp}
              disabled={loading}
              className='w-full mx-auto py-3 rounded-full font-semibold text-[#637848] bg-[#C4D3B6] hover:opacity-95 transition-opacity border border-[#a9c4a8]/80 cursor-pointer flex items-center justify-center gap-2 shadow-md disabled:opacity-70'
            >
              <FaGoogle size={20} /> Sign up with Google
            </button>
            <div className='flex items-center gap-3'>
              <span className='flex-1 h-px bg-[#F2CEC2]' />
              <span className='text-[#F2CEC2] text-base'>or</span>
              <span className='flex-1 h-px bg-[#F2CEC2]' />
            </div>
            <div className='grid grid-cols-1 sm:grid-cols-2 gap-5'>
              <div className='sm:col-span-2'>
                <label htmlFor='email' className='block text-[#F2CEC2] text-base font-medium mb-2 ml-4'>
                  Email / Username
                </label>
                <input
                  id='email'
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
                    placeholder='Enter password'
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete='new-password'
                    disabled={loading}
                    className='w-full px-4 py-2 pr-12 rounded-full border border-[#F2CEC2] text-[#F2CEC2] placeholder-[#F2CEC2]/80 focus:outline-none focus:ring-2 focus:ring-[#F2CEC2]/50 bg-transparent'
                  />
                  <button
                    type='button'
                    onClick={() => setShowPassword((p) => !p)}
                    className='absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#F2CEC2] hover:text-[#f2cec2]/80 focus:outline-none rounded cursor-pointer'
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor='repeat-password' className='block text-[#F2CEC2] text-base font-medium mb-2 ml-4'>
                  Repeat Password
                </label>
                <div className='relative'>
                  <input
                    id='repeat-password'
                    type={showRepeatPassword ? 'text' : 'password'}
                    placeholder='Repeat password'
                    value={repeatPassword}
                    onChange={(e) => setRepeatPassword(e.target.value)}
                    required
                    autoComplete='new-password'
                    disabled={loading}
                    className='w-full px-4 py-2 pr-12 rounded-full border border-[#F2CEC2] text-[#F2CEC2] placeholder-[#F2CEC2]/80 focus:outline-none focus:ring-2 focus:ring-[#F2CEC2]/50 bg-transparent'
                  />
                  <button
                    type='button'
                    onClick={() => setShowRepeatPassword((p) => !p)}
                    className='absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#F2CEC2] hover:text-[#f2cec2]/80 focus:outline-none rounded cursor-pointer'
                    aria-label={showRepeatPassword ? 'Hide password' : 'Show password'}
                  >
                    {showRepeatPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
                  </button>
                </div>
                {repeatPassword.length > 0 && (
                  <p
                    className={`text-xs mt-1.5 ml-4 ${password === repeatPassword ? 'text-green-300' : 'text-amber-200'}`}
                    role='status'
                  >
                    {password === repeatPassword ? 'Passwords match' : 'Password does not match'}
                  </p>
                )}
              </div>
            </div>
            <button
              type='submit'
              disabled={loading || password !== repeatPassword}
              className='w-full max-w-[150px] mx-auto py-3 rounded-full font-semibold text-[#5C6E43] bg-gradient-to-r from-[#F3BD8C] to-[#E69695] hover:opacity-95 transition-opacity cursor-pointer mt-2 disabled:opacity-70 inline-flex items-center justify-center gap-2 min-h-[48px]'
            >
              {loading ? (
                <>
                  <span className="inline-flex scale-[0.72] origin-center" aria-hidden>
                    <LoaderSpinner size="xs" color="#1a1a1a" />
                  </span>
                  <span>Signing up…</span>
                </>
              ) : (
                'Sign Up'
              )}
            </button>
          </form>
          <p className='text-[#F2CEC2] text-sm mt-2 text-center mx-auto mb-24 md:mb-0'>
            Already have an account?{' '}
            <Link to='/signin' className='hover:underline font-medium hover:text-[#F3BD8C]'>
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default SignUp
