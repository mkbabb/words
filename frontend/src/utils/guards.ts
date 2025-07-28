import { CARD_VARIANTS, type CardVariant } from '@/types';
import type { Etymology } from '@/types/api';

/**
 * Type guard to check if a value is a valid card variant
 */
export function isCardVariant(value: unknown): value is CardVariant {
  return typeof value === 'string' && CARD_VARIANTS.includes(value as CardVariant);
}

/**
 * Type guard to check if a value is a valid Etymology object
 */
export function isEtymology(value: unknown): value is Etymology {
  return typeof value === 'object' && value !== null && 'text' in value && typeof (value as any).text === 'string';
}

/**
 * Normalize etymology data to always return an Etymology object
 * Handles both string and object forms from the API
 */
export function normalizeEtymology(etymology: unknown): Etymology | null {
  if (!etymology) return null;
  
  if (typeof etymology === 'string') {
    return { text: etymology };
  }
  
  if (isEtymology(etymology)) {
    return etymology;
  }
  
  return null;
}