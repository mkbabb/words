/**
 * Richness score → visual helpers.
 */

/** HSL interpolation: blue (220) at 0.0 → orange-red (15) at 1.0 */
export function richnessToColor(score: number): string {
    const clamped = Math.max(0, Math.min(1, score));
    const hue = 220 - clamped * 205; // 220 → 15
    const saturation = 55 + clamped * 20; // 55% → 75%
    const lightness = 55 - clamped * 5; // 55% → 50%
    return `hsl(${Math.round(hue)}, ${Math.round(saturation)}%, ${Math.round(lightness)}%)`;
}

export function richnessToLabel(score: number): string {
    if (score >= 0.8) return 'Excellent';
    if (score >= 0.6) return 'Rich';
    if (score >= 0.4) return 'Good';
    if (score >= 0.2) return 'Basic';
    return 'Sparse';
}
