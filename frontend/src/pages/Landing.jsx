import React from 'react'
import { Link } from 'react-router-dom'
import landingImage from '../assets/landing.svg'

const Landing = () => {
  return (
    <div className='overflow-x-hidden bg-[#5C6E43]'>
      <section className='relative h-screen min-h-[100dvh] overflow-hidden'>
        <img
          src={landingImage}
          alt=""
          className='absolute inset-0 min-h-full min-w-full object-cover object-center'
          aria-hidden
        />
        <div className='relative z-10 flex h-full items-center pl-8 sm:pl-12 md:pl-16 lg:pl-48 pr-6'>
          <div className='max-w-md space-y-6 sm:max-w-md sm:space-y-8'>
            <h1
              className='text-4xl text-[#764441] drop-shadow-sm sm:text-5xl md:text-6xl'
              style={{ fontFamily: '"Londrina Solid", sans-serif' }}
            >
              Kitchen Mate
            </h1>
            <p className='text-sm leading-relaxed text-[#764441] sm:text-base px-2'>
              Not sure what to cook with what you have at home? We can help you find recipes using
              the ingredients in your kitchen. Just add what you have, and we&apos;ll suggest
              recipes you can make.
            </p>
            <div className='flex flex-wrap items-center gap-8 pt-1 justify-center'>
              <Link
                to='/signup'
                className='inline-flex items-center justify-center rounded-full bg-[#764441] px-10 py-2 text-center text-sm font-semibold text-[#F7E7C4] shadow-sm transition-opacity hover:brightness-115'
              >
                SIGN UP
              </Link>
              <Link
                to='/signin'
                className='inline-flex items-center justify-center rounded-full px-10 py-2 text-center text-sm font-semibold text-[#F7E7C4] bg-[#764441] transition-colors hover:brightness-115'
              >
                SIGN IN
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Landing
