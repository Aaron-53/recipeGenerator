import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Navbar from '../components/Navbar'
import RecipeListingCard from '../components/RecipeListingCard'
import Loader from '../components/Loader'
import ErrorBanner from '../components/ErrorBanner'
import { recipesAPI } from '../services/api'
import { resolveRecipeImageFileName } from '../utils/recipeImages'
import { formatApiError } from '../utils/formatApiError'

const INVENTORY_LINE_BG = {
  backgroundColor: '#5b6d44',
  backgroundImage: [
    'repeating-linear-gradient(0deg, transparent 0, transparent 200px, #3d4a32 200px, #3d4a32 205px)',
    'repeating-linear-gradient(90deg, transparent 0, transparent 200px, #3d4a32 200px, #3d4a32 205px)',
  ].join(', '),
}

const PAGE_SIZE = 120
const TARGET_VISIBLE_MIN = 24
const MAX_AUTO_EXTRA_PAGES = 12

function payloadField(payload, ...keys) {
  if (!payload || typeof payload !== 'object') return undefined
  for (const k of keys) {
    if (payload[k] != null && payload[k] !== '') return payload[k]
  }
  return undefined
}

function hasRecipeDescriptionPayload(payload) {
  const d = payloadField(payload, 'description', 'desc', 'summary')
  if (d == null) return false
  return String(d).trim() !== ''
}

function rowHasManifestImage(row, manifestSet) {
  const stem = payloadField(
    row.payload || {},
    'image_filename',
    'image',
    'image_name'
  )
  if (stem == null || String(stem).trim() === '') return false
  const fileName = resolveRecipeImageFileName(stem)
  if (!fileName) return false
  return manifestSet.has(fileName)
}

function rowPassesHomeFilters(row, manifestSet) {
  if (!hasRecipeDescriptionPayload(row.payload)) return false
  if (manifestSet instanceof Set) {
    return rowHasManifestImage(row, manifestSet)
  }
  const stem = payloadField(
    row.payload || {},
    'image_filename',
    'image',
    'image_name'
  )
  return stem != null && String(stem).trim() !== ''
}

function sortListingById(items) {
  return [...items].sort((a, b) =>
    String(a.id).localeCompare(String(b.id), undefined, { numeric: true })
  )
}

/** One row per display title — Qdrant can hold multiple points with the same recipe name. */
function dedupeListingByTitle(items) {
  const seen = new Set()
  const out = []
  for (const row of items) {
    const p = row.payload || {}
    const title = payloadField(p, 'title', 'recipe_name', 'name')
    const raw = String(title || '').trim()
    const key = raw ? raw.toLowerCase() : `__id:${row.id}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(row)
  }
  return out
}

const Home = () => {
  const [rawItems, setRawItems] = useState([])
  const [imageManifest, setImageManifest] = useState(undefined)
  const [nextOffset, setNextOffset] = useState(null)
  const [hasMore, setHasMore] = useState(false)
  const [recipesLoading, setRecipesLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const autoExtraPagesRef = useRef(0)

  useEffect(() => {
    let cancelled = false
    const base = import.meta.env.BASE_URL || '/'
    const root = base.endsWith('/') ? base : `${base}/`
    fetch(`${root}recipe-images-manifest.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => {
        if (cancelled) return
        if (json && Array.isArray(json.filenames)) {
          setImageManifest(new Set(json.filenames))
        } else {
          setImageManifest(null)
        }
      })
      .catch(() => {
        if (!cancelled) setImageManifest(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const visibleItems = useMemo(() => {
    if (imageManifest === undefined) return []
    const filtered = rawItems.filter((row) =>
      rowPassesHomeFilters(row, imageManifest)
    )
    return dedupeListingByTitle(sortListingById(filtered))
  }, [rawItems, imageManifest])

  const pageLoading = recipesLoading || imageManifest === undefined

  const fetchPage = useCallback(async (offset) => {
    const isFirst = offset == null || offset === ''
    if (isFirst) {
      setRecipesLoading(true)
    } else {
      setLoadingMore(true)
    }
    setError(null)
    try {
      const { data } = await recipesAPI.list({ limit: PAGE_SIZE, offset: offset || undefined })
      const batch = Array.isArray(data?.items) ? data.items : []
      setRawItems((prev) => (isFirst ? batch : [...prev, ...batch]))
      setNextOffset(data?.next_offset ?? null)
      setHasMore(Boolean(data?.has_more))
    } catch (e) {
      setError(formatApiError(e, e.message || 'Could not load recipes.'))
      if (isFirst) setRawItems([])
    } finally {
      setRecipesLoading(false)
      setLoadingMore(false)
    }
  }, [])

  useEffect(() => {
    fetchPage(null)
  }, [fetchPage])

  useEffect(() => {
    if (pageLoading || loadingMore) return
    if (imageManifest === undefined) return
    if (!hasMore || nextOffset == null) return
    if (visibleItems.length >= TARGET_VISIBLE_MIN) {
      autoExtraPagesRef.current = 0
      return
    }
    if (autoExtraPagesRef.current >= MAX_AUTO_EXTRA_PAGES) return
    autoExtraPagesRef.current += 1
    fetchPage(nextOffset)
  }, [
    pageLoading,
    loadingMore,
    imageManifest,
    visibleItems.length,
    hasMore,
    nextOffset,
    fetchPage,
  ])

  const loadMore = () => {
    if (!hasMore || loadingMore || nextOffset == null) return
    fetchPage(nextOffset)
  }

  return (
    <div className="relative flex min-h-screen flex-col py-6 lg:py-0">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0 opacity-40"
        style={INVENTORY_LINE_BG}
      />
      <div className="relative z-10">
        <Navbar />
      </div>
      <main className="relative z-10 mx-auto w-full max-w-[1600px] flex-1 px-4 pb-12 pt-2 sm:px-6 lg:px-10">
        <div className="mb-6 text-center sm:mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-[#F2CEC2] sm:text-4xl">
            Recipe collection
          </h1>
          <p className="mt-2 text-sm text-[#f5e8c7]/80 sm:text-base">
            Browse recipes from our catalog
          </p>
        </div>

        <ErrorBanner
          message={error}
          onDismiss={() => setError(null)}
          variant="default"
          className="mb-6 px-4"
          centerMessage
        />

        {pageLoading ? (
          <Loader className="min-h-[40vh] py-12" color="#f5e8c7" />
        ) : (
          <>
            <ul className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-3">
              {visibleItems.map((row, index) => {
                const p = row.payload || {}
                const title = payloadField(p, 'title', 'recipe_name', 'name')
                const description = payloadField(p, 'description', 'desc', 'summary')
                const imageFilename = payloadField(p, 'image_filename', 'image', 'image_name')
                return (
                  <li key={row.id} className="min-w-0">
                    <RecipeListingCard
                      title={title}
                      description={description}
                      imageFilename={imageFilename}
                      listIndex={index}
                    />
                  </li>
                )
              })}
            </ul>

            {visibleItems.length === 0 && !error && (
              <p className="py-16 text-center text-[#f5e8c7]/90">
                No recipes match a local image in{' '}
                <code className="rounded bg-black/20 px-1">recipe-images-manifest.json</code> and have a description.
                Images go in <code className="rounded bg-black/20 px-1">public/recipe-images</code>; names must match{' '}
                <code className="rounded bg-black/20 px-1">image_filename</code> (add{' '}
                <code className="rounded bg-black/20 px-1">.jpg</code> when the API has no extension).
              </p>
            )}

            {hasMore && (
              <div className="mt-10 flex justify-center">
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="rounded-full border border-[#f5e8c7]/40 bg-[#f5e8c7]/10 px-8 py-2.5 text-sm font-semibold text-[#f5e8c7] transition-colors hover:bg-[#f5e8c7]/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loadingMore ? 'Loading…' : 'Load more'}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default Home