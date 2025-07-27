export const PART_OF_SPEECH_ORDER: Record<string, number> = {
    noun: 1,
    verb: 2,
    adjective: 3,
    adverb: 4,
    pronoun: 5,
    preposition: 6,
    conjunction: 7,
    interjection: 8,
    determiner: 9,
    article: 10,
};

export const ANIMATION_CYCLE_DELAY = {
    initial: 15000,  // 15 seconds initial delay
    min: 60000,      // 60 seconds minimum between cycles
    max: 90000,      // 90 seconds maximum between cycles
} as const;

export const CARD_THEMES = [
    { label: 'Default', value: 'default' },
    { label: 'Bronze', value: 'bronze' },
    { label: 'Silver', value: 'silver' },
    { label: 'Gold', value: 'gold' },
] as const;

export * from './providers';