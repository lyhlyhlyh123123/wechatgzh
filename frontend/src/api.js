import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const msg = err?.response?.data?.detail || err.message || '请求失败'
    if (window.__elMessage) window.__elMessage.error(String(msg))
    return Promise.reject(err)
  },
)

export const fileUrl = (p) => `/files/${p}`
