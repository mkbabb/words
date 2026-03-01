import { ref } from 'vue';
import type { TypewriterOptions, CancellationToken } from '../types';
import { DEFAULTS } from '../types';
import { calculateKeyDelay } from '../utils/keyboard';
import { getPauseDelay, PAUSE_PATTERNS } from '../utils/pausePatterns';
import {
    createCancellationToken,
    sleep,
    stochasticDelay,
    backspaceDelay as calcBackspaceDelay,
    pickNgramSize,
    prefersReducedMotion,
} from '../utils/timing';
import {
    nextTypoAction,
    createTypoContext,
    DEFAULT_TYPO_CONFIG,
    type TypoConfig,
} from '../utils/typoStateMachine';

export function useTypewriter(options: TypewriterOptions) {
    // Merge options with defaults
    const opts = { ...DEFAULTS, ...options };

    // --- Reactive state ---
    const displayText = ref('');
    const isTyping = ref(false);
    const isFirstAnimation = ref(true);

    // --- Internal state (non-reactive) ---
    let targetText = opts.text;
    let currentToken: CancellationToken | null = null;

    // --- Derived typo config ---
    function getTypoConfig(): TypoConfig {
        return {
            ...DEFAULT_TYPO_CONFIG,
            maxCharsBeforeNotice: opts.maxCharsBeforeNotice,
            continueAfterTypoProbability: opts.continueAfterTypoProbability,
            sequentialTypoDecay: opts.sequentialTypoDecay,
        };
    }

    // --- Core typing loop ---

    async function typeTextWithNgrams(token: CancellationToken): Promise<void> {
        const chars = targetText;
        let typoCtx = createTypoContext();
        const typoConfig = getTypoConfig();
        const speedFactor = isFirstAnimation.value ? opts.firstAnimationSpeedFactor : 1;
        const skipTypos = isFirstAnimation.value;

        while (displayText.value.length < chars.length) {
            if (token.cancelled) return;

            const pos = displayText.value.length;
            const currentChar = chars[pos];
            const prevChar = pos > 0 ? chars[pos - 1] : '';

            // If FSM is in a non-normal state, drive it single-char
            if (typoCtx.state !== 'normal') {
                const result = nextTypoAction(
                    typoCtx,
                    currentChar,
                    typoConfig,
                    opts.errorRate,
                );
                typoCtx = result.ctx;

                const ok = await executeAction(result.action, token, prevChar, speedFactor);
                if (!ok) return;
                continue;
            }

            // Normal state: decide typo or n-gram
            if (!skipTypos && pos > 3 && pos < chars.length - 3) {
                const result = nextTypoAction(
                    typoCtx,
                    currentChar,
                    typoConfig,
                    opts.errorRate,
                );
                typoCtx = result.ctx;

                if (result.action.type === 'type_wrong') {
                    const ok = await executeAction(result.action, token, prevChar, speedFactor);
                    if (!ok) return;
                    continue;
                }

                // FSM said type_correct — fall through to n-gram path
            }

            // N-gram typing
            const ngramSize = Math.min(
                pickNgramSize(opts.ngramSize),
                chars.length - pos,
            );

            for (let i = 0; i < ngramSize; i++) {
                if (token.cancelled) return;
                const charPos = pos + i;
                const ch = chars[charPos];
                const prev = charPos > 0 ? chars[charPos - 1] : '';

                displayText.value += ch;

                // Only delay after the last char of the n-gram
                if (i === ngramSize - 1) {
                    const nextCh = chars[charPos + 1] ?? '';
                    const keyDelay = calculateKeyDelay(prev, ch) * speedFactor;
                    const typingDelay = stochasticDelay(keyDelay, opts.variance);

                    // Punctuation pauses (skip on first animation)
                    let pauseDelay = 0;
                    if (!isFirstAnimation.value) {
                        pauseDelay = getPauseDelay(ch, nextCh, PAUSE_PATTERNS);
                    }

                    const ok = await sleep(typingDelay + pauseDelay, token);
                    if (!ok) return;
                }
            }
        }
    }

    async function executeAction(
        action: ReturnType<typeof nextTypoAction>['action'],
        token: CancellationToken,
        prevChar: string,
        speedFactor: number,
    ): Promise<boolean> {
        switch (action.type) {
            case 'type_correct': {
                if (action.char === '') return true; // resume placeholder
                displayText.value += action.char;
                const delay = calculateKeyDelay(prevChar, action.char) * speedFactor;
                return sleep(stochasticDelay(delay, opts.variance), token);
            }

            case 'type_wrong': {
                displayText.value += action.char;
                const delay = calculateKeyDelay(prevChar, action.char) * speedFactor;
                return sleep(stochasticDelay(delay, opts.variance), token);
            }

            case 'type_past_correct': {
                displayText.value += action.char;
                const delay = calculateKeyDelay(prevChar, action.char) * speedFactor;
                return sleep(
                    stochasticDelay(delay * opts.correctionSpeedMultiplier, opts.variance),
                    token,
                );
            }

            case 'notice': {
                return sleep(action.pauseMs, token);
            }

            case 'backspace': {
                return animateBackspaceSequence(action.count, token, action.frantic);
            }

            case 'resume': {
                return sleep(action.pauseMs, token);
            }
        }
    }

    // --- Backspace animation ---

    async function animateBackspaceSequence(
        count: number,
        token: CancellationToken,
        frantic: boolean,
    ): Promise<boolean> {
        const base = frantic ? opts.correctionBaseDelay : opts.backspaceBaseDelay;
        const accel = frantic
            ? opts.backspaceAcceleration * 2
            : opts.backspaceAcceleration;

        for (let i = 0; i < count; i++) {
            if (token.cancelled) return false;
            displayText.value = displayText.value.slice(0, -1);
            const delay = calcBackspaceDelay(base, opts.variance * 0.5, i, accel);
            const ok = await sleep(delay, token);
            if (!ok) return false;
        }
        return true;
    }

    // --- Public API ---

    async function startTyping(): Promise<void> {
        // Cancel any in-flight animation
        currentToken?.cancel();
        const token = createCancellationToken();
        currentToken = token;
        isTyping.value = true;

        // Reduced motion: show final text immediately
        if (opts.respectReducedMotion && prefersReducedMotion()) {
            displayText.value = targetText;
            isTyping.value = false;
            isFirstAnimation.value = false;
            opts.onComplete?.();
            return;
        }

        // If not first animation and we have text, backspace it first
        if (!isFirstAnimation.value && displayText.value.length > 0) {
            const ok = await sleep(opts.preBackspacePause, token);
            if (!ok) return;

            const ok2 = await animateBackspaceSequence(
                displayText.value.length,
                token,
                false,
            );
            if (!ok2) return;

            const ok3 = await sleep(opts.postBackspacePause, token);
            if (!ok3) return;
        }

        // Type the text
        await typeTextWithNgrams(token);

        // Complete (only if we weren't cancelled)
        if (!token.cancelled) {
            isFirstAnimation.value = false;
            isTyping.value = false;
            opts.onComplete?.();

            if (opts.loop) {
                await sleep(2000, token);
                if (!token.cancelled) {
                    startTyping();
                }
            }
        }
    }

    function stopTyping(): void {
        currentToken?.cancel();
        currentToken = null;
        isTyping.value = false;
    }

    function reset(): void {
        stopTyping();
        displayText.value = '';
        isFirstAnimation.value = true;
    }

    function updateText(newText: string): void {
        targetText = newText;
        opts.text = newText;
        if (displayText.value.length > 0) {
            isFirstAnimation.value = false;
        }
    }

    async function backspaceToPosition(targetLength: number): Promise<void> {
        if (isTyping.value || targetLength >= displayText.value.length || targetLength < 0) {
            return;
        }

        currentToken?.cancel();
        const token = createCancellationToken();
        currentToken = token;
        isTyping.value = true;

        const charsToRemove = displayText.value.length - targetLength;
        await animateBackspaceSequence(charsToRemove, token, false);

        isTyping.value = false;
        if (!token.cancelled) {
            await sleep(200, token);
            if (!token.cancelled) {
                startTyping();
            }
        }
    }

    return {
        displayText,
        isTyping,
        isFirstAnimation,
        startTyping,
        stopTyping,
        reset,
        updateText,
        backspaceToPosition,
    };
}
