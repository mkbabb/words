import webpush from 'web-push';
import fs from 'fs';
import path from 'path';

// Generate VAPID keys
const vapidKeys = webpush.generateVAPIDKeys();

console.log('VAPID Keys Generated:');
console.log('====================');
console.log('Public Key:', vapidKeys.publicKey);
console.log('Private Key:', vapidKeys.privateKey);

// Create .env file if it doesn't exist
const envPath = path.join(process.cwd(), '.env');
const envContent = `# VAPID Keys for Web Push Notifications
VAPID_PUBLIC_KEY=${vapidKeys.publicKey}
VAPID_PRIVATE_KEY=${vapidKeys.privateKey}
VAPID_SUBJECT=mailto:notifications@floridify.com

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
DB_NAME=floridify

# Server Configuration
PORT=3001
NODE_ENV=development

# API Configuration
API_URL=http://localhost:8000

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
`;

if (!fs.existsSync(envPath)) {
  fs.writeFileSync(envPath, envContent);
  console.log('\n.env file created with VAPID keys');
} else {
  console.log('\n.env file already exists. Add these keys manually:');
  console.log(`VAPID_PUBLIC_KEY=${vapidKeys.publicKey}`);
  console.log(`VAPID_PRIVATE_KEY=${vapidKeys.privateKey}`);
}

// Also save to frontend .env
const frontendEnvPath = path.join(process.cwd(), '..', 'frontend', '.env');
const frontendEnvContent = `# Add this to your frontend .env file
VITE_VAPID_PUBLIC_KEY=${vapidKeys.publicKey}
`;

console.log('\nAdd this to your frontend .env file:');
console.log(`VITE_VAPID_PUBLIC_KEY=${vapidKeys.publicKey}`);