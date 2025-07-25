import puppeteer from 'puppeteer';
import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { defaultConfig, FaviconConfig } from './config.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function generateFavicon(config: FaviconConfig = defaultConfig): Promise<void> {
  console.log('🎨 Generating favicons...');
  console.log(`   Expression: ${config.expression}`);
  console.log(`   Sizes: ${config.sizes.join(', ')}`);

  // Read template files
  const htmlTemplate = readFileSync(join(__dirname, 'template.html'), 'utf-8');
  const cssTemplate = readFileSync(join(__dirname, 'styles.css'), 'utf-8');

  // Launch browser once
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    // Generate PNGs for each size
    for (const size of config.sizes) {
      await generatePNG(browser, htmlTemplate, cssTemplate, config, size);
    }

    // SVG generation removed for now - needs proper path extraction from KaTeX

    console.log('\n✨ All favicons generated successfully!');
  } finally {
    await browser.close();
  }
}

async function generatePNG(
  browser: puppeteer.Browser,
  htmlTemplate: string,
  cssTemplate: string,
  config: FaviconConfig,
  size: number
): Promise<void> {
  const page = await browser.newPage();

  // Calculate dynamic values
  const borderRadius = size * config.borderRadiusRatio;
  const fontSize = size * config.fontSizeRatio;
  const verticalOffset = -(size * config.verticalOffsetRatio);

  // Inject CSS variables
  const css = cssTemplate
    .replace('--size: 128px', `--size: ${size}px`)
    .replace('--background: white', `--background: ${config.background}`)
    .replace('--color: #1f2937', `--color: ${config.textColor}`)
    .replace('--border-radius: 16px', `--border-radius: ${borderRadius}px`)
    .replace('--font-size: 96px', `--font-size: ${fontSize}px`)
    .replace('--vertical-offset: -8px', `--vertical-offset: ${verticalOffset}px`);

  // Create full HTML with inline CSS and expression
  const html = htmlTemplate
    .replace('<link rel="stylesheet" href="./styles.css">', `<style>${css}</style>`)
    .replace(
      `const params = new URLSearchParams(window.location.search);`,
      `const params = new URLSearchParams('');`
    )
    .replace(
      `const expression = params.get('expression') || '\\mathfrak{F}';`,
      `const expression = '${config.expression.replace(/\\\\/g, '\\\\\\\\')}'`
    )
    .replace(
      `const fontSize = params.get('fontSize') || '96';`,
      `const fontSize = '${fontSize}'`
    );

  // Set viewport
  await page.setViewport({
    width: size,
    height: size,
    deviceScaleFactor: size <= 64 ? 2 : 1
  });

  // Load page
  await page.setContent(html, { waitUntil: 'networkidle0' });

  // Wait for KaTeX to render
  await page.waitForSelector('.katex', { timeout: 5000 });
  await new Promise(resolve => setTimeout(resolve, 300));

  // Take screenshot
  const screenshot = await page.screenshot({
    omitBackground: false,
    type: 'png'
  });

  // Save PNG
  const outputPath = join(__dirname, config.outputDir);
  const fileName = size === 32 ? `${config.pngFilePrefix}.png` : `${config.pngFilePrefix}-${size}.png`;
  const pngPath = join(outputPath, fileName);
  
  writeFileSync(pngPath, screenshot);
  console.log(`   ✓ Generated ${size}x${size} PNG`);

  await page.close();
}

// SVG generation removed - needs proper implementation to extract paths from KaTeX
// TODO: Implement proper SVG generation using either:
// 1. OpenType.js to extract font glyphs
// 2. Canvas rendering + vectorization
// 3. Server-side LaTeX to SVG conversion

// Allow running directly or importing
if (import.meta.url === `file://${process.argv[1]}`) {
  // Parse command line args for custom config
  const args = process.argv.slice(2);
  const customConfig = { ...defaultConfig };

  // Simple arg parsing
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace('--', '');
    const value = args[i + 1];
    
    if (key === 'expression') {
      customConfig.expression = value;
    } else if (key === 'background') {
      customConfig.background = value;
    } else if (key === 'color') {
      customConfig.textColor = value;
    }
  }

  generateFavicon(customConfig).catch(console.error);
}

export { generateFavicon };