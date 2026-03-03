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
    'Cache-Control': 'no-cache',
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

// --- Auth token injection ---

type AuthTokenGetter = () => Promise<string | null>;
let _tokenGetter: AuthTokenGetter | null = null;

/**
 * Set the function that returns the current auth token.
 * Called once by the auth store during initialization.
 */
export function setAuthTokenGetter(getter: AuthTokenGetter): void {
  _tokenGetter = getter;
}

/**
 * Get the current auth token (for use outside axios, e.g. SSE).
 */
export async function getAuthToken(): Promise<string | null> {
  if (!_tokenGetter) return null;
  return _tokenGetter();
}

// Request interceptor — inject Bearer token
api.interceptors.request.use(
  async config => {
    logger.debug(
      `API Request: ${config.method?.toUpperCase()} ${config.url}`,
      config.params
    );

    // Inject auth token if available
    if (_tokenGetter) {
      try {
        const token = await _tokenGetter();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch {
        // Silent failure — request proceeds without auth
      }
    }

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

    // Dispatch auth:required event on 401 for login redirect
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:required'));
    }

    return Promise.reject(error);
  }
);
