import { ref } from 'vue';
import { calculateKeyDelay } from '../utils/qwertyMap';
import { getPauseDelay, PAUSE_PATTERNS } from '../utils/pausePatterns';
import { simulateError } from '../utils/errorSimulation';

interface TypewriterOptions {
    text: string;
    mode?: 'basic' | 'human' | 'expert';
    baseSpeed?: number;
    variance?: number;
    errorRate?: number;
    loop?: boolean;
    onComplete?: () => void;
}

export const useTypewriter = (options: TypewriterOptions) => {
    const displayText = ref('');
    const isTyping = ref(false);
    const isFirstAnimation = ref(true);
    const hasCompletedAnimation = ref(false);
    const currentText = ref(options.text);
    let animationId: number | null = null;

    const delay = (ms: number): Promise<void> => {
        return new Promise(resolve => setTimeout(resolve, ms));
    };

    const getTypingDelay = (baseDelay: number, variance: number): number => {
        const variation = (Math.random() - 0.5) * 2 * variance;
        const calculatedDelay = baseDelay * (1 + variation);
        return Math.max(50, Math.min(500, calculatedDelay));
    };

    const animateBackspace = async (fromLength: number, toLength: number) => {
        while (displayText.value.length > toLength && isTyping.value) {
            displayText.value = displayText.value.slice(0, -1);
            // Backspace speed: 30-70ms per character
            await delay(30 + Math.random() * 40);
        }
    };

    const startTyping = async () => {
        if (isTyping.value) return; // Prevent multiple animations
        
        isTyping.value = true;
        
        // Update current text reference
        currentText.value = options.text;
        
        // Check if we need to backspace (not first animation and we have existing text)
        if (!isFirstAnimation.value && displayText.value.length > 0) {
            // Calculate how many characters to keep (20-80% will be deleted)
            const currentLength = displayText.value.length;
            const deletePercentage = 0.2 + Math.random() * 0.6; // 20% to 80%
            const charactersToDelete = Math.floor(currentLength * deletePercentage);
            const targetLength = currentLength - charactersToDelete;
            
            // Animate backspacing
            await animateBackspace(currentLength, targetLength);
            
            // Pause after partial backspace (200-400ms)
            if (isTyping.value) {
                await delay(200 + Math.random() * 200);
            }
            
            // Continue backspacing to empty if we haven't cleared everything
            if (displayText.value.length > 0 && isTyping.value) {
                await animateBackspace(displayText.value.length, 0);
            }
            
            // Final pause before typing new text (200-400ms)
            if (isTyping.value) {
                await delay(200 + Math.random() * 200);
            }
        } else if (isFirstAnimation.value) {
            // First animation - start clean
            displayText.value = '';
        }
        
        // Type the new text with occasional backspacing
        await typeTextWithBackspacing();
        
        // Mark animation as completed
        if (isTyping.value) {
            if (isFirstAnimation.value) {
                isFirstAnimation.value = false;
            }
            hasCompletedAnimation.value = true;
            isTyping.value = false;
            options.onComplete?.();
        }
        
        // Handle looping if enabled
        if (options.loop && isTyping.value !== false) {
            await delay(1500); // Pause before looping
            startTyping();
        }
    };
    
    const typeTextWithBackspacing = async () => {
        const chars = currentText.value.split('');
        let position = 0;
        
        while (position < chars.length && isTyping.value) {
            // Check if we should do random backspacing (not on first animation)
            if (!isFirstAnimation.value && 
                position > 5 && // Don't backspace too early
                position < chars.length - 10 && // Don't backspace too close to the end
                Math.random() < 0.15) { // 15% chance of backspacing
                
                // Decide how many characters to backspace (2-8 characters)
                const backspaceCount = 2 + Math.floor(Math.random() * 7);
                const actualBackspace = Math.min(backspaceCount, position - 2); // Keep at least 2 chars
                
                // Pause before realizing "mistake" (100-300ms)
                await delay(100 + Math.random() * 200);
                
                // Animate backspacing
                const targetLength = displayText.value.length - actualBackspace;
                await animateBackspace(displayText.value.length, targetLength);
                
                // Pause after backspacing (200-400ms)
                await delay(200 + Math.random() * 200);
                
                // Reset position to retype from where we backspaced to
                position = targetLength;
                continue;
            }
            
            // Type the character (with possible typo)
            const typed = await typeCharacter(chars, position);
            if (typed) {
                position++;
            }
            // If typeCharacter returns false (typo correction), position stays the same
        }
    };
    
    const typeCharacter = async (chars: string[], position: number): Promise<boolean> => {
        const currentChar = chars[position];
        const nextChar = chars[position + 1] || '';
        const prevChar = position > 0 ? chars[position - 1] : '';
        let keyDelay: number;
        
        // Use expert mode for first animation regardless of settings
        const currentMode = isFirstAnimation.value ? 'expert' : (options.mode || 'human');
        
        if (currentMode === 'basic') {
            // Basic mode: constant speed with small variance
            keyDelay = getTypingDelay(options.baseSpeed || 250, 0.2);
        } else {
            // Human and expert modes: QWERTY-based delays
            const qwertyDelay = calculateKeyDelay(prevChar, currentChar);
            const baseDelay = currentMode === 'expert' ? qwertyDelay * 0.6 : qwertyDelay;
            keyDelay = getTypingDelay(baseDelay, options.variance || 0.5);
        }
        
        // Add pause patterns for human and expert modes
        let pauseDelay = 0;
        if (currentMode !== 'basic' && !isFirstAnimation.value) {
            pauseDelay = getPauseDelay(currentChar, nextChar, PAUSE_PATTERNS);
        }
        
        // Simulate typos (only after first animation and not in basic mode)
        if (!isFirstAnimation.value && hasCompletedAnimation.value && currentMode !== 'basic') {
            const shouldSimulateError = Math.random() < 0.05 && // 5% chance
                                       position > 3 && // Not at the beginning
                                       position < chars.length - 3; // Not at the end
            
            if (shouldSimulateError) {
                // Type a wrong character
                const wrongChars = 'asdfjkl;qwertyuiop'.split('');
                const wrongChar = wrongChars[Math.floor(Math.random() * wrongChars.length)];
                displayText.value += wrongChar;
                
                // Continue typing for 1-3 more characters before noticing
                const detectionDelay = 1 + Math.floor(Math.random() * 3);
                const detectionChars = Math.min(detectionDelay, chars.length - position - 1);
                
                for (let i = 0; i < detectionChars && isTyping.value; i++) {
                    await delay(keyDelay);
                    displayText.value += chars[position + 1 + i];
                }
                
                // Pause before correction (human reaction time)
                if (isTyping.value) {
                    await delay(200 + Math.random() * 300);
                }
                
                // Backspace to correct
                const backspaceTarget = displayText.value.length - (detectionChars + 1);
                await animateBackspace(displayText.value.length, backspaceTarget);
                
                // Small pause after correction
                await delay(100 + Math.random() * 100);
                
                return false; // Signal to retry this character
            }
        }
        
        // Type the character normally
        displayText.value += currentChar;
        
        // Wait for next character
        await delay(keyDelay + pauseDelay);
        
        return true; // Successfully typed
    };

    const stopTyping = () => {
        isTyping.value = false;
        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }
    };

    const reset = () => {
        stopTyping();
        displayText.value = '';
        isFirstAnimation.value = true;
        hasCompletedAnimation.value = false;
    };
    
    const updateText = (newText: string) => {
        // Update the options text when it changes
        options.text = newText;
        currentText.value = newText;
        // DO NOT reset or clear displayText here - let the animation handle it
    };

    return {
        displayText,
        isTyping,
        isFirstAnimation,
        hasCompletedAnimation,
        startTyping,
        stopTyping,
        reset,
        updateText
    };
};