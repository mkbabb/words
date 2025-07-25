# Favicon Generator

A modular favicon generator that renders LaTeX expressions using KaTeX.

## Usage

```bash
# Generate with default settings (mathfrak F)
npm run generate-favicon

# Generate with custom expression
npm run generate-favicon -- --expression "\\mathscr{F}"

# Generate with custom colors
npm run generate-favicon -- --expression "\\mathbb{F}" --background "#f3f4f6" --color "#1e40af"
```

## Configuration

Edit `config.ts` to change default settings:

- `expression`: LaTeX expression to render (default: `\mathfrak{F}`)
- `background`: Background color (default: white)
- `textColor`: Text color (default: #1f2937)
- `sizes`: Array of sizes to generate (default: [16, 32, 48, 64, 128, 256])
- `borderRadiusRatio`: Corner radius as ratio of size (default: 0.125 = 12.5%)
- `fontSizeRatio`: Font size as ratio of icon size (default: 0.75 = 75%)
- `verticalOffsetRatio`: Vertical adjustment for centering (default: 0.0625 = 6.25%)

## Customization

1. **Styles**: Edit `styles.css` for global styling changes
2. **Template**: Edit `template.html` for structural changes
3. **Config**: Edit `config.ts` for default values

## Examples

```typescript
// Custom config example
import { generateFavicon } from './generate.js';

await generateFavicon({
  expression: '\\mathcal{W}',
  background: '#1e293b',
  textColor: '#f8fafc',
  sizes: [32, 64, 128],
  borderRadiusRatio: 0.2,
  fontSizeRatio: 0.8,
  verticalOffsetRatio: 0.05,
  outputDir: '../../public',
  svgFileName: 'favicon.svg',
  pngFilePrefix: 'favicon'
});
```