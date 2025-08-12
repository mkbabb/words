# Floridify Scripts

## Installation & Setup

### `install-floridify`
**Complete installation and setup script for Floridify CLI**

```bash
./scripts/install-floridify
```

**What it does:**
- ✅ Creates and activates Python virtual environment
- ✅ Installs all dependencies with `uv sync`
- ✅ Installs floridify package in editable mode
- ✅ Creates global symlink at `~/.local/bin/floridify`
- ✅ Adds `~/.local/bin` to PATH if needed
- ✅ Sets up ZSH autocomplete (two methods)
- ✅ Tests CLI performance and functionality

**Requirements:**
- `uv` package manager installed
- ZSH shell (for autocomplete)

**After installation:**
```bash
# Test installation
floridify --version                    # Should show version in ~0.07s
floridify --help                       # Should be instant

# Test autocomplete (after restarting terminal)
floridify <TAB><TAB>                   # Shows commands
floridify scrape <TAB><TAB>            # Shows scrape subcommands
floridify scrape apple-dictionary --<TAB><TAB>  # Shows options

# Start scraping
floridify scrape apple-dictionary --language en --session-name "test-2025"
```

## Development Scripts

### `dev`
**Development environment orchestrator**

```bash
./scripts/dev                         # Start Docker containers
./scripts/dev --native               # Run natively without Docker  
./scripts/dev --logs                 # Start and follow logs
./scripts/dev --build                # Rebuild Docker images
```

## Performance

The CLI has been optimized for instant startup:
- **Main help**: ~0.07s (was 4.2s)
- **Scrape help**: ~0.08s (was 4.5s)
- **Command execution**: Heavy modules load only when needed

## Architecture

```
words/
├── backend/           # Python FastAPI + CLI
├── frontend/          # Vue 3 TypeScript SPA  
└── scripts/           # Installation & dev tools
    ├── install-floridify    # Complete setup script
    ├── dev                  # Development orchestrator
    └── README.md           # This file
```