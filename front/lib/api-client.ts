import axios from "axios"

const apiClient = axios.create({
  baseURL: "http://localhost:5000/api",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // 确保请求包含cookie
})

// 添加请求拦截器以包含认证令牌
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// 添加响应拦截器以处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 处理 401 错误（未授权）
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("token")
      localStorage.removeItem("email")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  },
)

export default apiClient

