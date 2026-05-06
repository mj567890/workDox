import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const instance: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      // 格式化错误消息：FastAPI 422 验证错误返回的 detail 是数组
      const msg = (d: any): string => {
        if (!d) return ''
        if (typeof d === 'string') return d
        if (Array.isArray(d)) return d.map((e: any) => e.msg || JSON.stringify(e)).join('; ')
        return String(d)
      }
      switch (status) {
        case 401:
          localStorage.removeItem('token')
          router.push('/login')
          break
        case 403:
          ElMessage.error(msg(data.detail) || '权限不足')
          break
        case 404:
          ElMessage.error(msg(data.detail) || '资源不存在')
          break
        case 409:
          ElMessage.warning(msg(data.detail) || '资源冲突')
          break
        case 422:
          ElMessage.warning(msg(data.detail) || '请求参数错误')
          break
        default:
          ElMessage.error(msg(data.detail) || '请求失败')
      }
    } else {
      ElMessage.error('网络错误')
    }
    return Promise.reject(error)
  }
)

export default instance

export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.get(url, { params, ...config })
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.post(url, data, config)
}

export function put<T = any>(url: string, data?: any): Promise<T> {
  return instance.put(url, data)
}

export function del<T = any>(url: string): Promise<T> {
  return instance.delete(url)
}

// ---------- Public API (no auth, no login redirect) ----------

const publicInstance: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

publicInstance.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    // Silently fail for public endpoints
    return Promise.reject(error)
  }
)

export function getPublic<T = any>(url: string, params?: any): Promise<T> {
  return publicInstance.get(url, { params })
}
