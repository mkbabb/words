import { toast } from 'vue-sonner'

export const showError = (message: string) => {
  toast.error(message, {
    duration: 5000,
    className: 'bg-destructive text-destructive-foreground',
  })
}

export const showSuccess = (message: string) => {
  toast.success(message, {
    duration: 3000,
    className: 'bg-background text-foreground',
  })
}

export const showInfo = (message: string) => {
  toast.info(message, {
    duration: 4000,
    className: 'bg-background text-foreground',
  })
}