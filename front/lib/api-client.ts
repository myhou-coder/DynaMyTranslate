import axios from "axios"

// 智能检测API地址
function getApiBaseUrl() {
  if (typeof window === 'undefined') {
    // 服务端渲染时使用默认地址
    return "http://localhost:5000/api"
  }
  
  const hostname = window.location.hostname
  
  // 根据当前访问地址智能选择API地址
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return "http://localhost:5000/api"
  } else if (hostname === '100.88.126.48') {
    return "http://100.88.126.48:5000/api"
  } else {
    // 使用环境变量或当前域名
    return process.env.NEXT_PUBLIC_API_BASE_URL || `http://${hostname}:5000/api`
  }
}

const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
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
      // 清除localStorage
      localStorage.removeItem("token")
      localStorage.removeItem("email")
      
      // 清除cookies - 防止middleware与拦截器冲突
      if (typeof document !== 'undefined') {
        document.cookie = "token=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/"
        document.cookie = "email=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/"
      }
      
      // 重定向到登录页
      window.location.href = "/login"
    }
    return Promise.reject(error)
  },
)

export default apiClient

