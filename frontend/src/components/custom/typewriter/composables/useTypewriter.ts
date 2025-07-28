import { ref } from 'vue';
import { calculateKeyDelay } from '../utils/qwertyMap';
import { getPauseDelay, PAUSE_PATTERNS } from '../utils/pausePatterns';

interface TypewriterOptions {
    text: string;
    mode?: 'basic' | 'human' | 'expert';
    baseSpeed?: number;
    variance?: number;
    errorRate?: number;
    loop?: boolean;
    animationDelay?: number;
    onComplete?: () => void;
}

export const useTypewriter = (options: TypewriterOptions) => {
    const displayText = ref('');
    const isTyping = ref(false);
    const isFirstAnimation = ref(true);
    const currentText = ref(options.text);

    const delay = (ms: number): Promise<void> => {
        return new Promise(resolve => setTimeout(resolve, ms));
    };

    const getTypingDelay = (baseDelay: number, variance: number): number => {
        const variation = (Math.random() - 0.5) * 2 * variance;
        const calculatedDelay = baseDelay * (1 + variation);
        return Math.max(50, Math.min(500, calculatedDelay));
    };

    const animateBackspace = async (count: number) => {
        for (let i = 0; i < count && isTyping.value; i++) {
            displayText.value = displayText.value.slice(0, -1);
            await delay(40 + Math.random() * 30);
        }
    };

    const startTyping = async () => {
        if (isTyping.value) return;
        
        isTyping.value = true;
        
        // If this is not the first animation and we have text, backspace it
        if (!isFirstAnimation.value && displayText.value.length > 0) {
            // Pause before backspacing
            await delay(500);
            
            // Backspace all text
            await animateBackspace(displayText.value.length);
            
            // Pause after backspacing
            await delay(300);
        }
        
        // Type the text
        await typeText();
        
        // Mark as completed
        if (isTyping.value) {
            isFirstAnimation.value = false;
            isTyping.value = false;
            options.onComplete?.();
            
            // Handle looping
            if (options.loop) {
                // Use animationDelay if provided, otherwise default to 2 seconds
                const loopDelay = options.animationDelay || 2000;
                await delay(loopDelay);
                startTyping();
            }
        }
    };
    
    const typeText = async () => {
        const chars = currentText.value.split('');
        
        for (let position = 0; position < chars.length && isTyping.value; position++) {
            const currentChar = chars[position];
            const nextChar = chars[position + 1] || '';
            const prevChar = position > 0 ? chars[position - 1] : '';
            
            // Determine typing mode
            const currentMode = isFirstAnimation.value ? 'expert' : (options.mode || 'human');
            
            // Calculate delay
            let keyDelay: number;
            if (currentMode === 'basic') {
                keyDelay = getTypingDelay(options.baseSpeed || 250, 0.2);
            } else {
                const qwertyDelay = calculateKeyDelay(prevChar, currentChar);
                const baseDelay = currentMode === 'expert' ? qwertyDelay * 0.6 : qwertyDelay;
                keyDelay = getTypingDelay(baseDelay, options.variance || 0.5);
            }
            
            // Add pause patterns for non-first animations
            let pauseDelay = 0;
            if (!isFirstAnimation.value && currentMode !== 'basic') {
                pauseDelay = getPauseDelay(currentChar, nextChar, PAUSE_PATTERNS);
            }
            
            // Occasional mid-word backspacing (only after first animation)
            if (!isFirstAnimation.value && 
                position > 5 && 
                position < chars.length - 5 && 
                Math.random() < 0.08) {
                
                // Backspace 2-5 characters
                const backspaceCount = 2 + Math.floor(Math.random() * 4);
                await delay(200); // Pause before backspacing
                await animateBackspace(Math.min(backspaceCount, position - 2));
                await delay(200); // Pause after backspacing
                
                // Reset position to retype
                position = displayText.value.length - 1; // Will be incremented by loop
                continue;
            }
            
            // Occasional typos (only after first animation)
            if (!isFirstAnimation.value && 
                currentMode !== 'basic' &&
                position > 3 &&
                position < chars.length - 3 &&
                Math.random() < 0.03) {
                
                // Type wrong character
                const wrongChars = 'asdfjkl;'.split('');
                const wrongChar = wrongChars[Math.floor(Math.random() * wrongChars.length)];
                displayText.value += wrongChar;
                
                // Type 1-2 more characters before noticing
                const detectionDelay = 1 + Math.floor(Math.random() * 2);
                for (let i = 0; i < detectionDelay && position + i + 1 < chars.length; i++) {
                    await delay(keyDelay);
                    displayText.value += chars[position + 1 + i];
                }
                
                // Pause and correct
                await delay(300);
                await animateBackspace(detectionDelay + 1);
                await delay(100);
                
                // Continue from current position
                position--; // Will be incremented by loop
                continue;
            }
            
            // Type the character
            displayText.value += currentChar;
            await delay(keyDelay + pauseDelay);
        }
    };

    const stopTyping = () => {
        isTyping.value = false;
    };

    const reset = () => {
        stopTyping();
        displayText.value = '';
        isFirstAnimation.value = true;
    };
    
    const updateText = (newText: string) => {
        options.text = newText;
        currentText.value = newText;
    };

    return {
        displayText,
        isTyping,
        isFirstAnimation,
        startTyping,
        stopTyping,
        reset,
        updateText
    };
};