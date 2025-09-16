#!/usr/bin/env python3
"""Run the Floridify REST API server."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.floridify.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
