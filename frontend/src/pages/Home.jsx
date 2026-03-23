import React from 'react'
import Navbar from '../components/Navbar'

const Home = () => {
  return (
    <div className="min-h-screen bg-[#5b6d44] flex flex-col">
      <Navbar />
      <main className="flex-1 px-4 pb-8 max-w-6xl mx-auto w-full flex items-center justify-center">
        <p className="text-[#f5e8c7] text-lg md:text-xl font-medium text-center">
          Home
        </p>
      </main>
    </div>
  )
}

export default Home
