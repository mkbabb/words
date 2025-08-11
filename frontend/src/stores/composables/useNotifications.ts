import { ref, readonly } from 'vue'

export interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  duration?: number
  timestamp: number
}

// Generate simple ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

// Shared state across all composable instances
const notifications = ref<Notification[]>([])
const maxNotifications = ref(5)

/**
 * useNotifications composable - Lightweight notification system
 * Replaces the Pinia store with a simpler composable pattern
 */
export function useNotifications() {
  const showNotification = (notification: {
    type: 'success' | 'error' | 'info' | 'warning'
    message: string
    duration?: number
  }) => {
    const id = generateId()
    const newNotification: Notification = {
      id,
      ...notification,
      timestamp: Date.now()
    }

    notifications.value.push(newNotification)

    // Enforce maximum number of notifications
    if (notifications.value.length > maxNotifications.value) {
      notifications.value = notifications.value.slice(-maxNotifications.value)
    }

    // Auto-remove after duration (default 5 seconds)
    const duration = notification.duration || 5000
    setTimeout(() => {
      removeNotification(id)
    }, duration)

    return id
  }

  const removeNotification = (id: string) => {
    notifications.value = notifications.value.filter((n) => n.id !== id)
  }

  const clearAllNotifications = () => {
    notifications.value = []
  }

  // Convenience methods
  const showSuccess = (message: string, duration?: number) => {
    return showNotification({ type: 'success', message, duration })
  }

  const showError = (message: string, duration?: number) => {
    return showNotification({ type: 'error', message, duration })
  }

  const showInfo = (message: string, duration?: number) => {
    return showNotification({ type: 'info', message, duration })
  }

  const showWarning = (message: string, duration?: number) => {
    return showNotification({ type: 'warning', message, duration })
  }

  const setMaxNotifications = (max: number) => {
    maxNotifications.value = Math.max(1, Math.min(10, max))
    
    // Trim existing notifications if needed
    if (notifications.value.length > maxNotifications.value) {
      notifications.value = notifications.value.slice(-maxNotifications.value)
    }
  }

  return {
    // State
    notifications: readonly(notifications),
    maxNotifications: readonly(maxNotifications),
    
    // Actions
    showNotification,
    removeNotification,
    clearAllNotifications,
    
    // Convenience methods
    showSuccess,
    showError,
    showInfo,
    showWarning,
    
    // Configuration
    setMaxNotifications
  }
}