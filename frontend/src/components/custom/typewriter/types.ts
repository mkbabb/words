import type { KeyPosition } from './utils/keyboard';

export type { KeyPosition };

// --- Typo FSM types ---

export type TypoState =
    | 'normal'
    | 'typo_injected'
    | 'typing_past'
    | 'noticed'
    | 'correcting'
    | 'resuming';

export interface TypoContext {
    state: TypoState;
    /** Number of chars typed past the typo position */
    charsPastTypo: number;
    /** Total chars to delete when correcting (typo char + chars past) */
    charsToDelete: number;
    /** Number of sequential typos in this burst */
    sequentialTypoCount: number;
}

export type TypoAction =
    | { type: 'type_correct'; char: string }
    | { type: 'type_wrong'; char: string; intended: string }
    | { type: 'type_past_correct'; char: string }
    | { type: 'notice'; pauseMs: number }
    | { type: 'backspace'; count: number; frantic: boolean }
    | { type: 'resume'; pauseMs: number };

// --- Cancellation ---

export interface CancellationToken {
    readonly cancelled: boolean;
    cancel(): void;
    onCancel(fn: () => void): void;
    offCancel(fn: () => void): void;
}

// --- Options ---

export interface TypewriterOptions {
    text: string;
    ngramSize?: number | { min: number; max: number };
    baseSpeed?: number;
    variance?: number;
    errorRate?: number;
    firstAnimationSpeedFactor?: number;

    // Typo behavior
    maxCharsBeforeNotice?: number;
    continueAfterTypoProbability?: number;
    sequentialTypoDecay?: number;
    correctionSpeedMultiplier?: number;
    correctionBaseDelay?: number;

    // Backspace
    backspaceBaseDelay?: number;
    backspaceAcceleration?: number;
    preBackspacePause?: number;
    postBackspacePause?: number;

    // Cursor
    cursorVisible?: boolean;
    cursorBlink?: boolean;
    cursorChar?: string;

    // Misc
    respectReducedMotion?: boolean;
    loop?: boolean;
    onComplete?: () => void;
}

export const DEFAULTS = {
    ngramSize: { min: 1, max: 3 } as { min: number; max: number },
    baseSpeed: 150,
    variance: 0.4,
    errorRate: 0.015,
    firstAnimationSpeedFactor: 0.6,

    maxCharsBeforeNotice: 4,
    continueAfterTypoProbability: 0.6,
    sequentialTypoDecay: 0.3,
    correctionSpeedMultiplier: 0.5,
    correctionBaseDelay: 40,

    backspaceBaseDelay: 45,
    backspaceAcceleration: 0.05,
    preBackspacePause: 400,
    postBackspacePause: 250,

    cursorVisible: true,
    cursorBlink: true,
    cursorChar: '|',

    respectReducedMotion: true,
    loop: false,
} as const satisfies Omit<Required<TypewriterOptions>, 'text' | 'onComplete'>;
