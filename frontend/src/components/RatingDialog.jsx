import React, { useEffect, useState } from 'react'
import { FaRegStar, FaStar } from 'react-icons/fa'
import ErrorBanner from './ErrorBanner'

const STAR_LABELS = ['Poor', 'Fair', 'OK', 'Good', 'Excellent']

function RatingDialogPanel({
  onClose,
  onSubmit,
  isSubmitting = false,
  error = null,
  onDismissError,
}) {
  const [rating, setRating] = useState(null)
  const [review, setReview] = useState('')

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && !isSubmitting) onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isSubmitting, onClose])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (rating == null) return
    onSubmit?.(rating, review.trim())
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      role="presentation"
      onClick={(e) => e.target === e.currentTarget && !isSubmitting && onClose?.()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="rating-dialog-title"
        className="w-full max-w-xl rounded-3xl border border-[#5A6A44]/12 bg-[#F5E6C4] p-7 px-16 shadow-2xl text-[#3d2b1f]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="rating-dialog-title"
          className="text-center text-2xl font-bold tracking-tight text-[#5A6A44] sm:text-[1.65rem]"
        >
          Rate this recipe
        </h2>
        <p className="mt-3 text-center text-base font-medium leading-relaxed text-[#3d2b1f]/80">
          How would you score it? Your feedback improves future suggestions.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <fieldset className="border-0 p-0">
            <legend className="sr-only">Star rating</legend>
            <div
              className="flex justify-center gap-2 sm:gap-3"
              role="radiogroup"
              aria-labelledby="rating-dialog-title"
            >
              {[1, 2, 3, 4, 5].map((n) => {
                const filled = rating != null && n <= rating
                return (
                  <button
                    key={n}
                    type="button"
                    role="radio"
                    aria-checked={rating === n}
                    aria-label={`${STAR_LABELS[n - 1]} — ${n} of 5 stars`}
                    disabled={isSubmitting}
                    onClick={() => setRating(n)}
                    className="cursor-pointer rounded-lg p-1 text-[#E69695] transition-transform hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#5A6A44]/45 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {filled ? (
                      <FaStar className="h-9 w-9 sm:h-10 sm:w-10 drop-shadow-sm" aria-hidden />
                    ) : (
                      <FaRegStar
                        strokeWidth={1}
                        className="h-9 w-9 sm:h-10 sm:w-10"
                        aria-hidden
                      />
                    )}
                  </button>
                )
              })}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor="rating-review"
              className="mb-2 block text-left text-sm text-[#3d2b1f]/90"
            >
              Review (optional)
            </label>
            <textarea
              id="rating-review"
              rows={4}
              value={review}
              onChange={(e) => setReview(e.target.value)}
              placeholder="What worked or what would you change?"
              className="w-full resize-y rounded-xl border border-[#5A6A44]/15 bg-[#FCFAE6] px-4 py-3 text-sm text-[#3d2b1f] shadow-inner placeholder:text-[#3d2b1f]/40 focus:border-[#5A6A44]/35 focus:outline-none focus:ring-2 focus:ring-[#5A6A44]/20 min-h-[5.5rem]"
            />
          </div>

          <ErrorBanner
            message={error}
            onDismiss={onDismissError}
            variant="light"
            className="px-3"
            centerMessage
          />

          <div className="flex flex-col items-center gap-4 pt-1">
            <button
              type="submit"
              disabled={isSubmitting || rating == null}
              className="w-fit rounded-2xl bg-[#5A6A44] cursor-pointer px-8 py-2.5 text-center text-sm font-semibold uppercase tracking-[0.12em] text-[#F6E7C8] shadow-md transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-45"
            >
              {isSubmitting ? 'Saving…' : 'Rate now'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-sm text-[#3d2b1f]/75 cursor-pointer hover:text-[#3d2b1f] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RatingDialog({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting = false,
  error = null,
  onDismissError,
}) {
  if (!isOpen) return null
  return (
    <RatingDialogPanel
      onClose={onClose}
      onSubmit={onSubmit}
      isSubmitting={isSubmitting}
      error={error}
      onDismissError={onDismissError}
    />
  )
}
