# Floridify Development Guide

## 🚀 Modern Development Environment

This project uses a modern Vue 3 + Vite setup with hot module replacement (HMR), TypeScript support, and seamless backend integration.

## Prerequisites

- Node.js 18+ (LTS recommended)
- Python 3.12+
- MongoDB (local or Atlas)
- Optional: pnpm for faster package management

## Quick Start

### 1. Install Dependencies

```bash
# Using npm (default)
cd frontend && npm install

# Using pnpm (recommended for speed)
npm install -g pnpm
cd frontend && pnpm install
```

### 2. Start Development Servers

```bash
# From project root - starts both frontend and backend
npm run dev

# Or run separately:
# Terminal 1 - Backend API (FastAPI on :8000)
cd backend && python scripts/api_server.py

# Terminal 2 - Frontend Dev Server (Vite on :3000)
cd frontend && npm run dev
```

### 3. Open Browser

Navigate to `http://localhost:3000` - Vite will automatically open this for you.

## 🔥 Hot Module Replacement (HMR)

Vite provides lightning-fast HMR out of the box:

- **Vue Components**: Update instantly without losing state
- **CSS/Tailwind**: See changes immediately
- **TypeScript**: Type checking in the background
- **API Proxy**: Backend changes require restart, but frontend proxy handles routing

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── views/          # Page-level components
│   ├── composables/    # Vue composition functions
│   ├── stores/         # Pinia state management
│   ├── utils/          # Utilities and helpers
│   ├── types/          # TypeScript definitions
│   └── assets/         # CSS, images, fonts
├── .env                # Development environment variables
├── .env.production     # Production environment variables
├── vite.config.ts      # Vite configuration
├── tailwind.config.ts  # Tailwind CSS configuration
└── tsconfig.json       # TypeScript configuration
```

## 🛠️ Development Features

### Type Checking

```bash
# Run type checking
npm run type-check

# Watch mode for continuous type checking
npm run type-check:watch
```

### Environment Variables

- Development: `.env` file
- Production: `.env.production` file
- Access in code: `import.meta.env.VITE_*`

Example:
```typescript
const apiUrl = import.meta.env.VITE_API_URL || '/api';
```

### API Proxy

The Vite dev server automatically proxies `/api/*` requests to the backend:

```typescript
// Frontend request
fetch('/api/lookup/example')

// Proxied to
http://localhost:8000/lookup/example
```

### Build for Production

```bash
# Type check and build optimized bundle
npm run build

# Preview production build locally
npm run preview
```

## 🔧 Configuration

### Vite Configuration (`vite.config.ts`)

- **HMR**: Configured for optimal hot reloading
- **Proxy**: Backend API integration
- **Aliases**: `@` maps to `src/` directory
- **Build**: Optimized chunking and minification

### TypeScript Configuration (`tsconfig.json`)

- **Strict Mode**: Full type safety
- **Vue Support**: Proper `.vue` file handling
- **Path Aliases**: Import shortcuts configured

### Tailwind Configuration (`tailwind.config.ts`)

- **Custom Fonts**: Fraunces and Fira Code
- **Animations**: Smooth transitions defined
- **Theme**: Consistent design tokens

## 🐛 Debugging

### Browser DevTools

1. Install Vue DevTools browser extension
2. Open DevTools → Vue tab
3. Inspect component state, props, and events

### VS Code Debugging

1. Install "Volar" extension for Vue 3 support
2. Use included `.vscode/launch.json` for debugging
3. Set breakpoints directly in `.vue` files

### Network Debugging

- Open Network tab to see API calls
- Vite proxy logs requests to console
- Check backend logs for API errors

## 📦 Dependencies

### Why These Choices?

- **Vite**: Fastest build tool with native ESM support
- **Vue 3**: Modern composition API and better TypeScript
- **Pinia**: Official state management, replacing Vuex
- **Tailwind CSS**: Utility-first styling with great DX
- **TypeScript**: Type safety and better IDE support

### Package Management

We recommend using **pnpm** for:
- 70% less disk space usage
- Faster installation (2-3x)
- Better monorepo support
- Strict dependency resolution

```bash
# Install pnpm globally
npm install -g pnpm

# Use pnpm commands
pnpm install      # Install dependencies
pnpm add [pkg]    # Add new dependency
pnpm dev          # Run dev server
```

## 🚨 Common Issues

### Port Already in Use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or change port in vite.config.ts
server: { port: 3001 }
```

### HMR Not Working

1. Check browser console for WebSocket errors
2. Ensure no proxy/firewall blocking
3. Try hard refresh: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)

### TypeScript Errors

```bash
# Clear cache and reinstall
rm -rf node_modules
pnpm install
pnpm type-check
```

### API Connection Issues

1. Ensure backend is running on port 8000
2. Check proxy configuration in `vite.config.ts`
3. Verify CORS settings in backend

## 📚 Resources

- [Vite Documentation](https://vitejs.dev/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Pinia Documentation](https://pinia.vuejs.org/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

Happy coding! 🎉 The development environment is optimized for the best possible developer experience with instant feedback and modern tooling.