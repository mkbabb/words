import { toast } from '@/components/ui/toast'

export const showError = (message: string) => {
  toast({
    title: 'Error',
    description: message,
    variant: 'destructive',
  })
}

export const showSuccess = (message: string) => {
  toast({
    title: 'Success',
    description: message,
  })
}

export const showInfo = (message: string) => {
  toast({
    title: 'Info',
    description: message,
  })
}