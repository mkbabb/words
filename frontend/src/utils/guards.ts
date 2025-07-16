import { CARD_VARIANTS, type CardVariant } from '@/types';

/**
 * Type guard to check if a value is a valid card variant
 */
export function isCardVariant(value: unknown): value is CardVariant {
  return typeof value === 'string' && CARD_VARIANTS.includes(value as CardVariant);
}