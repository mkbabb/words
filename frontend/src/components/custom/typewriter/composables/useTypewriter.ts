import { ref } from 'vue';
import { QWERTY_MAP, calculateKeyDelay } from '../utils/qwertyMap';
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
    let animationId: number | null = null;
    let hasTypedOnce = ref(false);
    let isFirstAnimation = true;
    let currentText = ref(options.text);

    const delay = (ms: number): Promise<void> => {
        return new Promise(resolve => setTimeout(resolve, ms));
    };

    const getTypingDelay = (baseDelay: number, variance: number): number => {
        const variation = (Math.random() - 0.5) * 2 * variance;
        const calculatedDelay = baseDelay * (1 + variation);
        return Math.max(50, Math.min(500, calculatedDelay));
    };

    const backspace = async (toPosition: number, totalDelay: number) => {
        const backspacesNeeded = displayText.value.length - toPosition;
        const delayPerBackspace = totalDelay / backspacesNeeded;
        
        for (let i = 0; i < backspacesNeeded; i++) {
            displayText.value = displayText.value.slice(0, -1);
            await delay(delayPerBackspace);
        }
    };

    const startTyping = async () => {
        isTyping.value = true;
        
        // Update current text reference
        currentText.value = options.text;
        
        // Determine if this is truly the first animation
        const shouldBackspace = displayText.value.length > 0 && !isFirstAnimation;
        
        // Handle backspace animation when we have existing text
        if (shouldBackspace) {
            const currentLength = displayText.value.length;
            // Decide how many characters to backspace (20% to 80% of text)
            const minBackspace = Math.max(1, Math.floor(currentLength * 0.2));
            const maxBackspace = Math.floor(currentLength * 0.8);
            const targetLength = currentLength - (minBackspace + Math.floor(Math.random() * (maxBackspace - minBackspace + 1)));
            
            // Animate backspacing to target length
            while (displayText.value.length > targetLength && isTyping.value) {
                displayText.value = displayText.value.slice(0, -1);
                // Visible backspace speed (50-90ms per character)
                await delay(50 + Math.random() * 40);
            }
            
            // Pause after partial backspace (200-400ms)
            await delay(200 + Math.random() * 200);
            
            // Continue backspacing to empty
            while (displayText.value.length > 0 && isTyping.value) {
                displayText.value = displayText.value.slice(0, -1);
                // Slightly faster for the final deletion
                await delay(40 + Math.random() * 30);
            }
            
            // Final pause before typing new text
            await delay(200 + Math.random() * 200);
        } else if (isFirstAnimation) {
            // First animation - make sure we start clean
            displayText.value = '';
        }
        
        // Now type the new text from the beginning
        const chars = currentText.value.split('');
        
        for (let position = 0; position < chars.length && isTyping.value; position++) {
            await typeCharacter(chars, position);
        }
        
        // Mark that we've completed at least one animation
        if (isFirstAnimation) {
            isFirstAnimation = false;
        }
        hasTypedOnce.value = true;
        isTyping.value = false;
        options.onComplete?.();
        
        // Loop if enabled
        if (options.loop && isTyping.value !== false) {
            await delay(1500); // Pause before looping
            startTyping();
        }
    };
    
    const typeCharacter = async (chars: string[], position: number) => {
        const currentChar = chars[position];
        const nextChar = chars[position + 1] || '';
        const prevChar = position > 0 ? chars[position - 1] : '';
        let keyDelay: number;
        
        // Use expert mode for first animation regardless of settings
        const currentMode = (isFirstAnimation && !hasTypedOnce.value) ? 'expert' : options.mode;
        
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
        if (currentMode !== 'basic' && !isFirstAnimation) {
            pauseDelay = getPauseDelay(currentChar, nextChar, PAUSE_PATTERNS);
        }
        
        // Determine if we should introduce errors (never on first animation)
        const shouldIntroduceErrors = !isFirstAnimation && 
            hasTypedOnce.value && 
            options.mode !== 'basic' && 
            Math.random() < 0.2; // 20% chance after first animation
        
        // Check for errors (human and expert modes, after initial animation)
        if (shouldIntroduceErrors && position > 5 && position < chars.length - 5) {
            const error = await simulateError(options.text, position, {
                errorRate: options.errorRate || 0.03,
                detectionDelay: 3,
                correctionProbability: 0.9
            });
            
            if (error.corrected) {
                // Type a wrong character
                const wrongChars = 'asdfjkl;'.split('');
                const wrongChar = wrongChars[Math.floor(Math.random() * wrongChars.length)];
                displayText.value += wrongChar;
                
                // Continue typing for detection delay
                const detectionChars = Math.min(error.detectionDelay, chars.length - position - 1);
                for (let i = 0; i < detectionChars; i++) {
                    await delay(keyDelay);
                    displayText.value += chars[position + 1 + i];
                }
                
                // Pause before correction
                await delay(300 + Math.random() * 200);
                
                // Backspace to correct
                await backspace(position, error.backspaceDelay * (detectionChars + 1));
                return; // Exit to retry this character in the main loop
            }
        }
        
        // Type the character
        displayText.value += currentChar;
        
        // Wait for next character
        await delay(keyDelay + pauseDelay);
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
        hasTypedOnce.value = false;
        isFirstAnimation = true;
    };
    
    const updateText = (newText: string) => {
        // Update the options text when it changes
        options.text = newText;
        currentText.value = newText;
    };

    return {
        displayText,
        isTyping,
        startTyping,
        stopTyping,
        reset,
        updateText
    };
};