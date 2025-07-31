import axios from 'axios';

// API versioning configuration
export const API_VERSION = 'v1';
export const API_BASE_URL = `/api/${API_VERSION}`;

// Create axios instance with standardized configuration
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds (1 minute)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error type for consistent error handling
export interface APIError {
  message: string;
  code?: string;
  field?: string;
  details?: any;
}

// Transform error responses to consistent format
export function transformError(error: any): APIError {
  if (error.response?.data?.error) {
    return {
      message: error.response.data.error,
      details: error.response.data.details,
    };
  }
  return {
    message: error.message || 'An unknown error occurred',
    code: error.code,
  };
}

// Request interceptor
api.interceptors.request.use(
  config => {
    console.log(
      `API Request: ${config.method?.toUpperCase()} ${config.url}`,
      config.params
    );
    return config;
  },
  error => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  response => {
    console.log(
      `API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`,
      response.data
    );
    return response;
  },
  error => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
    });
    return Promise.reject(error);
  }
);