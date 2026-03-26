import type { MasteryLevel, CardState } from '@/types/wordlist';

const countFormatter = new Intl.NumberFormat('en-US');

export function formatCount(value: number | undefined | null): string {
    return countFormatter.format(value ?? 0);
}

/** Format fractional-day interval: 0.000694 -> "1min", 0.00694 -> "10min", 1 -> "1d", 4 -> "4d" */
export function formatInterval(days: number | undefined): string {
    if (days == null) return '';
    if (days <= 0) return 'now';
    const minutes = days * 24 * 60;
    if (minutes < 60) return `${Math.max(1, Math.round(minutes))}min`;
    const hours = days * 24;
    if (hours < 24) return `${Math.round(hours)}hr`;
    if (days < 365) return `${Math.round(days)}d`;
    const years = days / 365;
    return `${years.toFixed(1)}yr`;
}

/** MasteryLevel -> human label */
export function getMasteryLabel(level: MasteryLevel): string {
    return {
        default: 'New',
        bronze: 'Learning',
        silver: 'Familiar',
        gold: 'Mastered',
    }[level] ?? 'New';
}

/** MasteryLevel -> Tailwind text color class */
export function getMasteryColorClass(level: MasteryLevel): string {
    return {
        default: 'mastery-default',
        bronze: 'mastery-bronze',
        silver: 'mastery-silver',
        gold: 'mastery-gold',
    }[level] ?? 'mastery-default';
}

/** CardState -> human label, null for 'new' */
export function getCardStateLabel(state: CardState | undefined): string | null {
    if (!state || state === 'new') return null;
    return {
        learning: 'Learning',
        young: 'Reviewing',
        mature: 'Mature',
        relearning: 'Relearning',
    }[state] ?? null;
}

/** CardState -> Tailwind text color class */
export function getCardStateColorClass(state: CardState | undefined): string {
    return {
        new: 'state-new',
        learning: 'state-learning',
        young: 'state-young',
        mature: 'state-mature',
        relearning: 'state-relearning',
    }[state ?? 'new'] ?? 'state-new';
}

/** CardState -> bg + text Tailwind classes for badge display */
export function getCardStateBadgeClasses(state: CardState | undefined): string {
    return {
        new: 'bg-state-new state-new',
        learning: 'bg-state-learning state-learning',
        young: 'bg-state-young state-young',
        mature: 'bg-state-mature state-mature',
        relearning: 'bg-state-relearning state-relearning',
    }[state ?? 'new'] ?? 'bg-state-new state-new';
}

/** MasteryLevel -> emoji */
export function getMasteryEmoji(level: MasteryLevel): string {
    return {
        default: '📝',
        bronze: '🥉',
        silver: '🥈',
        gold: '🥇',
    }[level] ?? '📝';
}

/** Compute progress % from mastery + repetitions (0-100) */
export function computeProgress(level: MasteryLevel, repetitions: number): number {
    const baseProgress = {
        default: 0,
        bronze: 25,
        silver: 60,
        gold: 100,
    }[level] ?? 0;

    const reviewBonus = Math.min(repetitions * 2, 20);
    return Math.min(baseProgress + reviewBonus, 100);
}

/** SM2Quality -> review button Tailwind class */
export function getReviewButtonClass(quality: number): string {
    if (quality === 0) return 'review-btn-again';
    if (quality <= 2) return 'review-btn-hard';
    if (quality <= 4) return 'review-btn-good';
    return 'review-btn-easy';
}

/** Map card state to its CSS custom property color value */
export function getCardStateCSSColor(state: CardState | undefined): string {
    const colors: Record<string, string> = {
        new: 'var(--card-state-new)',
        learning: 'var(--card-state-learning)',
        young: 'var(--card-state-young)',
        mature: 'var(--card-state-mature)',
        relearning: 'var(--card-state-relearning)',
    };
    return colors[state ?? 'new'] ?? colors['new'];
}

/** CardState -> full label (including 'New') for review display */
export function getCardStateLabelFull(state: CardState | undefined): string {
    return {
        new: 'New',
        learning: 'Learning',
        young: 'Young',
        mature: 'Mature',
        relearning: 'Relearning',
    }[state ?? 'new'] ?? state ?? 'New';
}
