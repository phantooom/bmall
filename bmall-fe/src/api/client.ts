import axios from 'axios'
import { API_BASE_URL } from '../config'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 添加响应拦截器统一处理错误
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      console.error('API Error:', {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url,
        method: error.config?.method
      })
    } else if (error.request) {
      console.error('API Request Error:', {
        request: error.request,
        url: error.config?.url,
        method: error.config?.method
      })
    } else {
      console.error('API Error:', error.message)
    }
    return Promise.reject(error)
  }
) 