export interface KeyPosition {
    row: number;
    col: number;
    finger: 'pinky' | 'ring' | 'middle' | 'index' | 'thumb';
    hand: 'left' | 'right';
}

export const QWERTY_MAP: Record<string, KeyPosition> = {
    // Row 0 - Numbers row
    '1': { row: 0, col: 1, finger: 'pinky', hand: 'left' },
    '2': { row: 0, col: 2, finger: 'ring', hand: 'left' },
    '3': { row: 0, col: 3, finger: 'middle', hand: 'left' },
    '4': { row: 0, col: 4, finger: 'index', hand: 'left' },
    '5': { row: 0, col: 5, finger: 'index', hand: 'left' },
    '6': { row: 0, col: 6, finger: 'index', hand: 'right' },
    '7': { row: 0, col: 7, finger: 'index', hand: 'right' },
    '8': { row: 0, col: 8, finger: 'middle', hand: 'right' },
    '9': { row: 0, col: 9, finger: 'ring', hand: 'right' },
    '0': { row: 0, col: 10, finger: 'pinky', hand: 'right' },
    
    // Row 1 - QWERTY row
    'q': { row: 1, col: 1, finger: 'pinky', hand: 'left' },
    'w': { row: 1, col: 2, finger: 'ring', hand: 'left' },
    'e': { row: 1, col: 3, finger: 'middle', hand: 'left' },
    'r': { row: 1, col: 4, finger: 'index', hand: 'left' },
    't': { row: 1, col: 5, finger: 'index', hand: 'left' },
    'y': { row: 1, col: 6, finger: 'index', hand: 'right' },
    'u': { row: 1, col: 7, finger: 'index', hand: 'right' },
    'i': { row: 1, col: 8, finger: 'middle', hand: 'right' },
    'o': { row: 1, col: 9, finger: 'ring', hand: 'right' },
    'p': { row: 1, col: 10, finger: 'pinky', hand: 'right' },
    
    // Row 2 - ASDF row (home row)
    'a': { row: 2, col: 1, finger: 'pinky', hand: 'left' },
    's': { row: 2, col: 2, finger: 'ring', hand: 'left' },
    'd': { row: 2, col: 3, finger: 'middle', hand: 'left' },
    'f': { row: 2, col: 4, finger: 'index', hand: 'left' },
    'g': { row: 2, col: 5, finger: 'index', hand: 'left' },
    'h': { row: 2, col: 6, finger: 'index', hand: 'right' },
    'j': { row: 2, col: 7, finger: 'index', hand: 'right' },
    'k': { row: 2, col: 8, finger: 'middle', hand: 'right' },
    'l': { row: 2, col: 9, finger: 'ring', hand: 'right' },
    ';': { row: 2, col: 10, finger: 'pinky', hand: 'right' },
    
    // Row 3 - ZXCV row
    'z': { row: 3, col: 1, finger: 'pinky', hand: 'left' },
    'x': { row: 3, col: 2, finger: 'ring', hand: 'left' },
    'c': { row: 3, col: 3, finger: 'middle', hand: 'left' },
    'v': { row: 3, col: 4, finger: 'index', hand: 'left' },
    'b': { row: 3, col: 5, finger: 'index', hand: 'left' },
    'n': { row: 3, col: 6, finger: 'index', hand: 'right' },
    'm': { row: 3, col: 7, finger: 'index', hand: 'right' },
    ',': { row: 3, col: 8, finger: 'middle', hand: 'right' },
    '.': { row: 3, col: 9, finger: 'ring', hand: 'right' },
    '/': { row: 3, col: 10, finger: 'pinky', hand: 'right' },
    
    // Space bar
    ' ': { row: 4, col: 5, finger: 'thumb', hand: 'right' },
    
    // Common punctuation
    "'": { row: 2, col: 11, finger: 'pinky', hand: 'right' },
    '"': { row: 2, col: 11, finger: 'pinky', hand: 'right' },
    '?': { row: 3, col: 10, finger: 'pinky', hand: 'right' },
    '!': { row: 0, col: 1, finger: 'pinky', hand: 'left' },
    '-': { row: 0, col: 11, finger: 'pinky', hand: 'right' },
    '=': { row: 0, col: 12, finger: 'pinky', hand: 'right' }
};

export const calculateKeyDelay = (prevChar: string, nextChar: string): number => {
    const prev = QWERTY_MAP[prevChar.toLowerCase()];
    const next = QWERTY_MAP[nextChar.toLowerCase()];
    
    if (!prev || !next) return 250; // default delay for unmapped characters
    
    // Fastest: alternating hands (promotes rhythm)
    if (prev.hand !== next.hand) {
        return 150 + Math.random() * 50; // 150-200ms
    }
    
    // Same key pressed twice (like 'ss', 'ee')
    if (prev.row === next.row && prev.col === next.col) {
        return 350 + Math.random() * 100; // 350-450ms
    }
    
    // Fast: drumming motion (adjacent fingers, same hand)
    const colDiff = Math.abs(prev.col - next.col);
    if (colDiff === 1 && prev.row === next.row) {
        return 180 + Math.random() * 40; // 180-220ms
    }
    
    // Home row combinations (most comfortable)
    if (prev.row === 2 && next.row === 2) {
        return 200 + Math.random() * 50; // 200-250ms
    }
    
    // Reaching from home row
    if ((prev.row === 2 && next.row !== 2) || (prev.row !== 2 && next.row === 2)) {
        return 280 + Math.random() * 70; // 280-350ms
    }
    
    // Bottom row with pinky/ring fingers (awkward)
    if ((prev.row === 3 || next.row === 3) && 
        (['pinky', 'ring'].includes(prev.finger) || ['pinky', 'ring'].includes(next.finger))) {
        return 320 + Math.random() * 80; // 320-400ms
    }
    
    // Large movements (crossing rows and columns)
    const rowDiff = Math.abs(prev.row - next.row);
    if (rowDiff > 1 || colDiff > 2) {
        return 300 + Math.random() * 100; // 300-400ms
    }
    
    // Default for other combinations
    return 250 + Math.random() * 50; // 250-300ms
};