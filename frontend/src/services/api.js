import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/signin'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  register: (username, password) =>
    api.post('/auth/register', { username, password }),
  login: (username, password) =>
    api.post('/auth/login', { username, password }),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
  verifyToken: () => api.get('/auth/verify-token'),
  googleLogin: () => {
    window.location.href = `${API_BASE_URL}/auth/google/login`
  },
  verifyGoogleToken: (token) => api.post('/auth/google/verify', { token }),
}

export const inventoryAPI = {
  createItem: (itemData) => api.post('/inventory/items', itemData),
  parseQuickInput: (text) => api.post('/inventory/parse-input', { text }),
  getAllItems: () => api.get('/inventory/items'),
  getItemById: (itemId) => api.get(`/inventory/items/${itemId}`),
  updateItem: (itemId, itemData) =>
    api.put(`/inventory/items/${itemId}`, itemData),
  deleteItem: (itemId) => api.delete(`/inventory/items/${itemId}`),
  getStats: () => api.get('/inventory/stats'),
}

export const healthAPI = {
  checkHealth: () => api.get('/health'),
  root: () => api.get('/'),
}

export const recipesAPI = {
  list: ({ limit = 20, offset } = {}) =>
    api.get('/recipes', {
      params: {
        limit,
        ...(offset != null && offset !== '' ? { offset } : {}),
      },
    }),
}

export const chatAPI = {
  sendMessage: (body) => api.post('/chat/message', body),
  rateRecipe: (body) => api.post('/chat/rate', body),
}

export const chatSessionsAPI = {
  list: () => api.get('/chat-sessions'),
  get: (sessionId, requestConfig = {}) =>
    api.get(`/chat-sessions/${sessionId}`, requestConfig),
  create: (body = {}) => api.post('/chat-sessions', body),
  save: (sessionId, body) => api.put(`/chat-sessions/${sessionId}`, body),
  patch: (sessionId, body) => api.patch(`/chat-sessions/${sessionId}`, body),
  delete: (sessionId) => api.delete(`/chat-sessions/${sessionId}`),
}

export default api
