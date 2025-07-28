// Quick script to generate placeholder PWA icons
const fs = require('fs');
const path = require('path');

// Create a simple SVG icon
const createSvgIcon = (size) => `
<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
  <rect width="${size}" height="${size}" fill="#faf8f6"/>
  <rect x="${size * 0.1}" y="${size * 0.1}" width="${size * 0.8}" height="${size * 0.8}" 
        fill="none" stroke="#1a1a1a" stroke-width="${size * 0.02}"/>
  <text x="50%" y="50%" font-family="Georgia, serif" font-size="${size * 0.3}" 
        font-weight="bold" text-anchor="middle" dominant-baseline="middle" fill="#1a1a1a">F</text>
</svg>
`;

const sizes = [72, 96, 128, 144, 152, 192, 384, 512];

// Ensure icons directory exists
const iconsDir = path.join(__dirname, '../public/icons');
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

// Generate SVG icons
sizes.forEach(size => {
  const svg = createSvgIcon(size);
  const filename = path.join(iconsDir, `icon-${size}x${size}.svg`);
  fs.writeFileSync(filename, svg);
  console.log(`Generated ${filename}`);
});

// Also create apple-touch-icon
const appleIcon = createSvgIcon(180);
fs.writeFileSync(path.join(iconsDir, 'apple-touch-icon.svg'), appleIcon);

console.log('\nSVG icons generated! To convert to PNG:');
console.log('1. Open each SVG in a browser');
console.log('2. Right-click and save as PNG');
console.log('3. Or use an online converter like cloudconvert.com');