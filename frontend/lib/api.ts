// frontend/lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/b',
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
});

// optional: normalize trailing slash on /api/... paths
api.interceptors.request.use((config) => {
  if (config.url?.startsWith('/api/') && !config.url.endsWith('/')) {
    const [path, qs] = config.url.split('?');
    config.url = path + '/' + (qs ? `?${qs}` : '');
  }
  return config;
});

export default api;
