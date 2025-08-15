#!/usr/bin/env python3
"""Local inference server for WOTD ML pipeline.

Lightweight variant of the SageMaker deployment for local development,
testing, and lightweight production use. Uses FastAPI instead of Flask
for better async support and automatic API docs.
"""

import asyncio
import json
import time
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ...utils.logging import get_logger
from ..core import TrainingConfig, WOTDCorpus
from ..encoders import get_semantic_encoder
from ..trainer import WOTDEmbedder

logger = get_logger(__name__)


class GenerateRequest(BaseModel):
    """Request for word generation."""

    prompt: str
    num_words: int = 10
    temperature: float = 0.8


class GenerateResponse(BaseModel):
    """Response from word generation."""

    words: list[str]
    semantic_id: tuple[int, int, int, int] | None
    processing_ms: int
    confidence: float


class LocalWOTDServer:
    """Local WOTD inference server with full pipeline support."""

    def __init__(self, model_dir: str | Path = "./models/wotd"):
        """Initialize local server.

        Args:
            model_dir: Directory containing trained models

        """
        self.model_dir = Path(model_dir)
        self.config: TrainingConfig | None = None
        self.embedder: WOTDEmbedder | None = None
        self.encoder = None
        self.semantic_ids: dict[str, tuple[int, int, int, int]] | None = None
        self.loaded = False

    async def load_models(self) -> None:
        """Load trained WOTD models for inference."""
        logger.info(f"🔄 Loading WOTD models from {self.model_dir}")

        try:
            # Load semantic IDs mapping
            semantic_ids_path = self.model_dir / "semantic_ids.json"
            if semantic_ids_path.exists():
                with open(semantic_ids_path) as f:
                    data = json.load(f)
                    # Convert lists back to tuples for SemanticID
                    self.semantic_ids = {k: tuple(v) for k, v in data.items()}
                logger.info(f"✅ Loaded {len(self.semantic_ids)} semantic IDs")

            # Load semantic encoder
            encoder_path = self.model_dir / "semantic_encoder.pt"
            if encoder_path.exists():
                checkpoint = torch.load(encoder_path, map_location="cpu")

                # Reconstruct config from saved data
                self.config = TrainingConfig(**checkpoint["config"])

                # Create embedder and encoder
                self.embedder = WOTDEmbedder(model_name=self.config.embedding_model)

                # Create encoder with appropriate dimensions
                from ..constants import DEFAULT_EMBEDDING_MODEL, MODEL_DIMENSIONS

                input_dim = MODEL_DIMENSIONS.get(
                    self.config.embedding_model,
                    MODEL_DIMENSIONS.get(DEFAULT_EMBEDDING_MODEL, 1024),
                )
                self.encoder = get_semantic_encoder(input_dim=input_dim)

                # Load encoder state
                self.encoder.encoder.load_state_dict(checkpoint["model_state_dict"])
                self.encoder.encoder.eval()
                logger.info("✅ Loaded semantic encoder")

            self.loaded = True
            logger.success("🎯 Local WOTD server loaded successfully")

        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
            raise

    async def generate_words(self, request: GenerateRequest) -> GenerateResponse:
        """Generate words using the full WOTD pipeline."""
        if not self.loaded:
            raise HTTPException(status_code=503, detail="Models not loaded")

        start_time = time.time()

        # Parse semantic ID from prompt if present
        semantic_id = self._parse_semantic_id(request.prompt)

        if semantic_id:
            # Use semantic ID for generation
            words = await self._generate_from_semantic_id(semantic_id, request.num_words)
        else:
            # Generate semantic ID from prompt text
            semantic_id, words = await self._generate_from_text(request.prompt, request.num_words)

        processing_ms = int((time.time() - start_time) * 1000)

        return GenerateResponse(
            words=words,
            semantic_id=semantic_id,
            processing_ms=processing_ms,
            confidence=0.9,  # High confidence for local generation
        )

    async def encode_text(self, text: str) -> tuple[int, int, int, int]:
        """Encode text to semantic ID using trained pipeline."""
        if not self.loaded or not self.embedder or not self.encoder:
            raise HTTPException(status_code=503, detail="Models not loaded")

        # Create a simple corpus from the text
        from ..core import Complexity, Era, Style, WOTDWord

        # Split text into words and create a corpus
        words = [word.strip().lower() for word in text.split() if word.strip()]
        if not words:
            return (0, 0, 0, 0)

        # Create temporary corpus
        corpus = WOTDCorpus(
            id="temp_encoding",
            style=Style.NEUTRAL,
            complexity=Complexity.SIMPLE,
            era=Era.CONTEMPORARY,
            words=[
                WOTDWord(
                    word=word,
                    definition="Word from input text",
                    pos="noun",
                    style=Style.NEUTRAL,
                    complexity=Complexity.SIMPLE,
                    era=Era.CONTEMPORARY,
                )
                for word in words[:50]  # Limit to 50 words
            ],
        )

        # Get embedding
        preference_vector = await self.embedder.encode_corpus(
            corpus,
            cache_embeddings=False,
        )

        # Encode to semantic ID
        semantic_id = self.encoder.encode(preference_vector.unsqueeze(0))
        return semantic_id

    def _parse_semantic_id(self, prompt: str) -> tuple[int, int, int, int] | None:
        """Parse semantic ID from prompt like [2,1,3,0]."""
        import re

        match = re.search(r"\[(\d+),(\d+),(\d+),(\d+)\]", prompt)
        if match:
            return tuple(int(x) for x in match.groups())
        return None

    async def _generate_from_semantic_id(
        self,
        semantic_id: tuple[int, int, int, int],
        num_words: int,
    ) -> list[str]:
        """Generate words from semantic ID (simplified implementation)."""
        # Find closest matching corpus
        if self.semantic_ids:
            closest_corpus_id = min(
                self.semantic_ids.keys(),
                key=lambda k: sum(
                    abs(a - b) for a, b in zip(self.semantic_ids[k], semantic_id, strict=False)
                ),
            )
            logger.info(f"Using closest corpus: {closest_corpus_id}")

        # For now, return sample words based on semantic characteristics
        style_words = {
            0: ["formal", "academic", "scholarly", "professional"],
            1: ["casual", "relaxed", "informal", "friendly"],
            2: ["poetic", "lyrical", "melodic", "artistic"],
            3: ["dramatic", "intense", "powerful", "striking"],
        }

        complexity_words = {
            0: ["simple", "clear", "basic", "easy"],
            1: ["beautiful", "lovely", "pretty", "nice"],
            2: ["complex", "intricate", "sophisticated", "elaborate"],
            3: ["plain", "ordinary", "common", "standard"],
        }

        era_words = {
            0: ["ancient", "classical", "timeless", "eternal"],
            1: ["historical", "traditional", "vintage", "classic"],
            2: ["modern", "contemporary", "current", "recent"],
            3: ["futuristic", "innovative", "cutting-edge", "advanced"],
        }

        # Combine words based on semantic ID
        words = []
        words.extend(style_words.get(semantic_id[0], ["neutral"])[:2])
        words.extend(complexity_words.get(semantic_id[1], ["moderate"])[:2])
        words.extend(era_words.get(semantic_id[2], ["contemporary"])[:2])

        # Add some variation based on the fourth dimension
        variation_words = ["unique", "distinct", "special", "particular", "specific"]
        words.extend(variation_words[: semantic_id[3] + 1])

        # Pad or trim to requested number
        while len(words) < num_words:
            words.extend(words[: min(len(words), num_words - len(words))])

        return words[:num_words]

    async def _generate_from_text(
        self,
        text: str,
        num_words: int,
    ) -> tuple[tuple[int, int, int, int], list[str]]:
        """Generate semantic ID and words from input text."""
        # Encode text to semantic ID
        semantic_id = await self.encode_text(text)

        # Generate words from the semantic ID
        words = await self._generate_from_semantic_id(semantic_id, num_words)

        return semantic_id, words


# Create FastAPI app
app = FastAPI(
    title="WOTD Local Inference Server",
    description="Local deployment of the Word-of-the-Day semantic encoding pipeline",
    version="1.0.0",
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global server instance
server = LocalWOTDServer()


@app.on_event("startup")
async def startup_event():
    """Load models on server startup."""
    try:
        await server.load_models()
    except Exception as e:
        logger.warning(f"⚠️ Could not load models on startup: {e}")
        logger.info("Server will start but inference may not work until models are loaded")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "loaded": server.loaded,
        "timestamp": time.time(),
        "model_dir": str(server.model_dir),
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_words(request: GenerateRequest):
    """Generate words using WOTD pipeline."""
    return await server.generate_words(request)


@app.post("/encode")
async def encode_text(request: dict[str, str]):
    """Encode text to semantic ID."""
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    semantic_id = await server.encode_text(text)
    return {
        "text": text,
        "semantic_id": semantic_id,
        "interpretation": {
            "style": semantic_id[0],
            "complexity": semantic_id[1],
            "era": semantic_id[2],
            "variation": semantic_id[3],
        },
    }


@app.get("/semantic_ids")
async def list_semantic_ids():
    """List all available semantic IDs."""
    if not server.loaded or not server.semantic_ids:
        raise HTTPException(status_code=503, detail="Semantic IDs not loaded")

    return {
        "count": len(server.semantic_ids),
        "semantic_ids": server.semantic_ids,
    }


async def run_server(
    host: str = "127.0.0.1",
    port: int = 8888,
    model_dir: str = "./models/wotd",
):
    """Run the local WOTD server."""
    # Initialize server with model directory
    global server
    server.model_dir = Path(model_dir)

    logger.info(f"🚀 Starting local WOTD server on {host}:{port}")
    logger.info(f"📁 Model directory: {model_dir}")
    logger.info(f"📖 API docs available at: http://{host}:{port}/docs")

    # Run with uvicorn
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
    )

    server_instance = uvicorn.Server(config)
    await server_instance.serve()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run local WOTD inference server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8888, help="Port to bind to")
    parser.add_argument("--model-dir", default="./models/wotd", help="Model directory")

    args = parser.parse_args()

    asyncio.run(
        run_server(
            host=args.host,
            port=args.port,
            model_dir=args.model_dir,
        )
    )
