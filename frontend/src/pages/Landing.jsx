import React from 'react'
import { Link } from 'react-router-dom'
import landingImage from '../assets/landing.svg'

const Landing = () => {
  return (
    <div className='overflow-x-hidden bg-[#5C6E43]'>
      <section className='relative overflow-hidden'>
        <img
          src={landingImage}
          alt=""
          className='min-h-screen min-w-full w-full h-full object-cover object-center -mt-2'
          aria-hidden
        />
        <div className='absolute inset-0 z-10 flex flex-col justify-center min-h-screen px-8 md:px-12 lg:px-24 -mt-[23rem] md:-mt-[30rem] lg:-mt-[53rem] max-w-xl'>
          <h1
            className='text-4xl sm:text-[100px] lg:text-[140px] font-bold text-[#5C6E43] mb-3'
            style={{ fontFamily: "'Flavors', cursive" }}
          >
            Kitchenmate
          </h1>
          <p className='text-black text-sm sm:text-lg md:text-xl mb-6 sm:mb-18 max-w-md font-medium'>
            Turn your ingredients into a meal
          </p>
          <div className='flex flex-col sm:flex-row flex-wrap gap-6'>
            <Link
              to='/signup'
              className='sm:px-6 px-2 py-0.5 sm:py-2 rounded-full w-fit sm:text-base text-sm font-medium sm:font-semibold bg-[#5C6E43] text-[#F7E6C8] hover:bg-[#5C6E43]/80 transition-colors'
            >
              Sign Up
            </Link>
            <Link
              to='/signin'
              className='sm:px-6 px-2 py-0.5 sm:py-2 rounded-full w-fit sm:text-base text-sm font-medium sm:font-semibold bg-[#5C6E43] text-[#F7E6C8] hover:bg-[#5C6E43]/80 transition-colors'
            >
              Login
            </Link>
          </div>
        </div>
      </section>

      <section className=' text-[#F5F0E8] px-8 md:px-12 lg:px-16 -mt-[20rem] mb-12 flex items-center justify-center'>
        <p className='max-w-2xl text-left text-base md:text-lg leading-relaxed'>
          Not sure what to cook with what you have at home? We can help you find
          recipes using the ingredients in your kitchen. Just add what you have,
          and we'll suggest recipes you can make. You'll also see which
          ingredients you already have and what you might be missing. It's a
          simple way to get meal ideas and make the most of what's in your
          kitchen.
        </p>
      </section>
    </div>
  )
}

export default Landing
