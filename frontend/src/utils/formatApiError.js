export function isRequestAbortError(err) {
  return err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError'
}

export function formatApiError(err, fallback) {
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => e.msg || JSON.stringify(e)).join(' ')
  }
  return fallback
}
