import { useEffect } from 'react'

export function useBodyScrollLock(locked) {
  useEffect(() => {
    if (typeof document === 'undefined' || !locked) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [locked])
}
