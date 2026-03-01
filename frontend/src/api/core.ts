import axios from 'axios';
import { logger } from '@/utils/logger';

// API versioning configuration
export const API_VERSION = 'v1';
export const API_BASE_URL = `${import.meta.env.BASE_URL}api/${API_VERSION}`;

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
export function transformError(error: unknown): APIError {
  if (error instanceof Error && 'response' in error) {
    const axiosError = error as { response?: { data?: { error?: string; details?: any } }; code?: string };
    if (axiosError.response?.data?.error) {
      return {
        message: axiosError.response.data.error,
        details: axiosError.response.data.details,
      };
    }
    return {
      message: error.message || 'An unknown error occurred',
      code: axiosError.code,
    };
  }
  if (error instanceof Error) {
    return { message: error.message };
  }
  return { message: 'An unknown error occurred' };
}

// Request interceptor
api.interceptors.request.use(
  config => {
    logger.debug(
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
    logger.debug(
      `API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`,
      response.data
    );
    return response;
  },
  error => {
    logger.error('API Error:', {
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