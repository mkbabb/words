export interface FaviconConfig {
  // LaTeX expression to render
  expression: string;
  
  // Colors
  background: string;
  textColor: string;
  
  // Sizes to generate
  sizes: number[];
  
  // Style adjustments
  borderRadiusRatio: number; // As a ratio of size (e.g., 0.125 = 12.5% of size)
  fontSizeRatio: number;     // As a ratio of size (e.g., 0.75 = 75% of size)
  verticalOffsetRatio: number; // As a ratio of size for vertical centering
  
  // Output settings
  outputDir: string;
  svgFileName: string;
  pngFilePrefix: string;
}

export const defaultConfig: FaviconConfig = {
  expression: '\\mathfrak{F}',
  background: 'white',
  textColor: '#1f2937',
  sizes: [16, 32, 48, 64, 128, 256],
  borderRadiusRatio: 0.125,
  fontSizeRatio: 0.75,
  verticalOffsetRatio: 0.0625,
  outputDir: '../../public',
  svgFileName: 'favicon.svg',
  pngFilePrefix: 'favicon'
};