# Floridify Frontend - July 2025

## Architecture

**Vue 3** + **TypeScript** SPA with **Tailwind CSS v4**, **shadcn/ui** components, **Pinia** state management, and **Vite** build system.

**Flow**: User Input → API Request → State Update → Reactive UI → Persistent Storage

## Directory Structure

```
src/
├── components/         # Vue components
│   ├── ui/            # shadcn/ui components (Button, Card, Tabs, etc.)
│   └── custom/        # Application components (DarkModeToggle, LaTeX)
├── stores/            # Pinia state management
├── types/             # TypeScript interfaces
├── utils/             # Utility functions and API client
├── views/             # Page components
├── assets/            # Global styles and static assets
└── main.ts            # Application entry point
```

## Core Dependencies

**Framework**: Vue 3.5.17 (Composition API), TypeScript 5.8.3
**Build**: Vite 7.0.3, Vue TSC (type checking)
**UI**: shadcn/ui + radix-vue, Tailwind CSS 4.1.11, Lucide icons
**State**: Pinia 3.0.3, VueUse (composition utilities)
**Styling**: SCSS, Class Variance Authority (type-safe variants)
**Development**: Prettier (with Tailwind sorting), ESLint

## Key Files

**Entry**: `main.ts` (app bootstrap), `App.vue` (root component)
**State**: `stores/index.ts` (persistent Pinia store, 485 lines)
**Types**: `types/index.ts` (TypeScript interfaces)
**API**: `utils/api.ts` (Axios client with interceptors)
**Styling**: `assets/index.css` (global styles + CSS variables)
**Components**: `components/ui/` (shadcn/ui), `components/custom/` (app-specific)

## Configuration

**Build**: `vite.config.ts` (port 3000, proxy to :8000, path aliases)
**Styling**: `tailwind.config.ts` (CSS variables, custom animations, dark mode)
**Code Quality**: `.prettierrc` (Tailwind sorting, 80 chars, 2 spaces)
**Types**: `tsconfig.json` (ES2020, strict mode, path mapping)

## Development

**Setup**: `npm install` (or `pnpm install`)
**Dev**: `npm run dev` (port 3000, HMR enabled)
**Build**: `npm run build` (ES2020 target, optimized chunking)
**Type Check**: `npm run type-check` (Vue TSC)
**Format**: `npm run format` (Prettier with Tailwind sorting)

## shadcn/ui Integration

**Components**: Button, Card, Input, Tabs, HoverCard, Avatar, Badge, Progress, Select
**Theming**: CSS variables-based system with dark mode support
**Customization**: Extended with metallic variants (gold, silver, bronze)
**Patterns**: CVA-powered component variants, composition-based

## Tailwind CSS Features

**Version**: 4.1.11 with modern `@tailwindcss/vite` plugin
**Theming**: CSS custom properties, class-based dark mode
**Custom**: Bronze color variants, sparkle/shimmer animations, metallic gradients
**Utilities**: hover-lift, focus-ring, custom scrollbar styling
**Responsive**: Container queries, mobile-first approach

## Vue 3 Patterns

**Composition API**: `<script setup>` syntax throughout
**State Management**: Pinia with persistent storage, reactive caching
**Routing**: Vue Router with dynamic routes
**Reactivity**: VueUse utilities, computed properties, watchers
**TypeScript**: Full type safety with strict mode

## Critical Technologies

**Performance**: Vite HMR, code splitting, optimized bundling, lazy loading
**UI/UX**: Responsive design, accessibility focus, smooth animations
**State**: Persistent localStorage, intelligent caching, session management
**Development**: TypeScript strict mode, automated formatting, hot reloading