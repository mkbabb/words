import { defineStore } from 'pinia'
import { ref, readonly } from 'vue'
import { generateId } from '@/utils'

interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  duration?: number
  timestamp: number
}

/**
 * NotificationStore - Centralized notification system
 * Handles toast notifications with automatic cleanup and queue management
 * Provides a clean, consistent API for showing user feedback
 */
export const useNotificationStore = defineStore('notifications', () => {
  // ==========================================================================
  // STATE (Non-persisted)
  // ==========================================================================
  
  const notifications = ref<Notification[]>([])
  const maxNotifications = ref(5) // Maximum number of concurrent notifications

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
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

  // Convenience methods for different notification types
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

  // Batch operations
  const showMultiple = (notificationsList: Array<{
    type: 'success' | 'error' | 'info' | 'warning'
    message: string
    duration?: number
  }>) => {
    const ids: string[] = []
    notificationsList.forEach(notification => {
      ids.push(showNotification(notification))
    })
    return ids
  }

  // Configuration
  const setMaxNotifications = (max: number) => {
    maxNotifications.value = Math.max(1, Math.min(10, max))
    
    // Trim existing notifications if needed
    if (notifications.value.length > maxNotifications.value) {
      notifications.value = notifications.value.slice(-maxNotifications.value)
    }
  }

  // Get notifications by type
  const getNotificationsByType = (type: 'success' | 'error' | 'info' | 'warning') => {
    return notifications.value.filter(n => n.type === type)
  }

  // Get notification count
  const getNotificationCount = () => {
    return notifications.value.length
  }

  // Check if has notifications
  const hasNotifications = () => {
    return notifications.value.length > 0
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    notifications: readonly(notifications),
    maxNotifications: readonly(maxNotifications),
    
    // Actions
    showNotification,
    removeNotification,
    clearAllNotifications,
    showSuccess,
    showError,
    showInfo,
    showWarning,
    showMultiple,
    setMaxNotifications,
    getNotificationsByType,
    getNotificationCount,
    hasNotifications
  }
})