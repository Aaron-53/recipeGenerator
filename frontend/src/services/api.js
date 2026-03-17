import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Handle response errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

// Auth API
export const authAPI = {
  register: (username, password) =>
    api.post("/auth/register", { username, password }),

  login: (username, password) =>
    api.post("/auth/login", { username, password }),

  logout: () => api.post("/auth/logout"),

  getCurrentUser: () => api.get("/auth/me"),

  verifyToken: () => api.get("/auth/verify-token"),

  googleLogin: () => {
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  },

  verifyGoogleToken: (token) => api.post("/auth/google/verify", { token }),
};

// Inventory API
export const inventoryAPI = {
  // Create new inventory item
  createItem: (itemData) => api.post("/inventory/items", itemData),

  // Get all inventory items (with optional category filter)
  getAllItems: (category = null) => {
    const params = category ? { category } : {};
    return api.get("/inventory/items", { params });
  },

  // Get single inventory item by ID
  getItemById: (itemId) => api.get(`/inventory/items/${itemId}`),

  // Update inventory item
  updateItem: (itemId, itemData) =>
    api.put(`/inventory/items/${itemId}`, itemData),

  // Delete inventory item
  deleteItem: (itemId) => api.delete(`/inventory/items/${itemId}`),

  // Get inventory statistics
  getStats: () => api.get("/inventory/stats"),
};

// Health check API
export const healthAPI = {
  checkHealth: () => api.get("/health"),

  root: () => api.get("/"),
};

export default api;
