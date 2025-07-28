export interface ErrorConfig {
    errorRate: number;          // 0.03-0.05 for subtle errors
    detectionDelay: number;     // 1-3 characters
    correctionProbability: number; // 0.8-0.95
}

export interface ErrorResult {
    corrected: boolean;
    detectionDelay: number;
    backspaceDelay: number;
}

const shouldMakeError = (config: ErrorConfig): boolean => {
    return Math.random() < config.errorRate;
};

export const simulateError = async (
    _text: string,
    _position: number,
    config: ErrorConfig
): Promise<ErrorResult> => {
    if (!shouldMakeError(config)) {
        return { corrected: false, detectionDelay: 0, backspaceDelay: 0 };
    }
    
    // Type 1-3 more characters before noticing
    const detectionDelay = Math.ceil(Math.random() * config.detectionDelay);
    
    // Decide whether to correct
    const willCorrect = Math.random() < config.correctionProbability;
    
    if (willCorrect) {
        // Backspace delay (faster than typing)
        const backspaceDelay = 50 + Math.random() * 30;
        
        return {
            corrected: true,
            detectionDelay,
            backspaceDelay
        };
    }
    
    return { corrected: false, detectionDelay: 0, backspaceDelay: 0 };
};