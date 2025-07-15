import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): T & { cancel: () => void } {
  let timeout: ReturnType<typeof setTimeout>;
  let cancel = () => clearTimeout(timeout);

  const debounced = ((...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  }) as T & { cancel: () => void };

  debounced.cancel = cancel;
  return debounced;
}

export function formatDate(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;

  if (!dateObj || isNaN(dateObj.getTime())) {
    return 'Invalid date';
  }

  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dateObj);
}

export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

export function normalizeWord(word: string): string {
  return word
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '');
}

export function getHeatmapClass(similarity: number): string {
  const intensity = Math.ceil(similarity * 10);
  return `heatmap-${Math.max(1, Math.min(10, intensity))}`;
}

export function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substr(0, maxLength) + '...';
}

export function isValidWord(word: string): boolean {
  return /^[a-zA-Z\s-']+$/.test(word.trim()) && word.trim().length > 0;
}
