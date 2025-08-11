#!/usr/bin/env python3
"""SageMaker inference script for WOTD ML pipeline."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import torch
from flask import Flask, request, jsonify

# Add code directory to Python path
sys.path.append('/opt/ml/code')

from wotd.core import GenerateRequest, GenerateResponse, SemanticID
from wotd.trainer import SemanticEncoder


class WOTDInferenceHandler:
    """SageMaker inference handler for WOTD."""
    
    def __init__(self) -> None:
        self.model_path = os.environ.get('MODEL_PATH', '/opt/ml/model')
        self.encoder: SemanticEncoder | None = None
        self.semantic_ids: dict[str, SemanticID] | None = None
        self.loaded = False
    
    def load_models(self) -> None:
        """Load trained WOTD models."""
        model_dir = Path(self.model_path)
        
        print(f"🔄 Loading WOTD models from {model_dir}")
        
        try:
            # Load semantic IDs mapping
            semantic_ids_path = model_dir / "semantic_ids.json"
            if semantic_ids_path.exists():
                with open(semantic_ids_path) as f:
                    data = json.load(f)
                    # Convert lists back to tuples for SemanticID
                    self.semantic_ids = {k: tuple(v) for k, v in data.items()}
                print(f"✅ Loaded {len(self.semantic_ids)} semantic IDs")
            
            # Load semantic encoder
            encoder_path = model_dir / "semantic_encoder.pt"
            if encoder_path.exists():
                checkpoint = torch.load(encoder_path, map_location='cpu')
                
                # Reconstruct config from saved data
                from wotd.core import TrainingConfig
                config = TrainingConfig(**checkpoint['config'])
                
                # Create and load encoder
                self.encoder = SemanticEncoder(config)
                self.encoder.load_state_dict(checkpoint['model_state_dict'])
                self.encoder.eval()
                print("✅ Loaded semantic encoder")
            
            self.loaded = True
            print("🎯 WOTD inference pipeline loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load models: {e}")
            raise
    
    def generate_words(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate words using WOTD pipeline."""
        if not self.loaded:
            raise RuntimeError("Models not loaded")
        
        start_time = time.time()
        
        # Parse request
        request_obj = GenerateRequest(**request_data)
        
        # Simple mock generation (in real implementation, would use trained language model)
        words = self._mock_generate(request_obj)
        
        # Detect semantic ID (mock implementation)
        semantic_id = self._detect_semantic_id(request_obj.prompt)
        
        processing_ms = int((time.time() - start_time) * 1000)
        
        response = GenerateResponse(
            words=words,
            semantic_id=semantic_id,
            processing_ms=processing_ms,
            confidence=0.85  # Mock confidence
        )
        
        return response.model_dump()
    
    def _mock_generate(self, request: GenerateRequest) -> list[str]:
        """Mock word generation (replace with actual model inference)."""
        # In real implementation, this would use the trained language model
        mock_words = [
            "serendipity", "ephemeral", "mellifluous", "petrichor", 
            "sonder", "wanderlust", "luminous", "ethereal", 
            "ineffable", "solitude", "reverie", "sublime"
        ]
        
        return mock_words[:request.num_words]
    
    def _detect_semantic_id(self, prompt: str) -> SemanticID | None:
        """Detect semantic ID from prompt (mock implementation)."""
        # Parse DSL patterns like [0,1,*,2]
        import re
        match = re.search(r'\[([0-9*]),([0-9*]),([0-9*]),([0-9*])\]', prompt)
        if match:
            levels = []
            for group in match.groups():
                levels.append(int(group) if group != '*' else 0)
            return tuple(levels)
        
        return None


# Global handler instance
handler = WOTDInferenceHandler()

# Flask app for SageMaker
app = Flask(__name__)


@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy", 
        "loaded": handler.loaded,
        "timestamp": time.time()
    })


@app.route('/invocations', methods=['POST'])
def invoke():
    """Main inference endpoint."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        prediction = handler.generate_words(data)
        return jsonify(prediction)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": time.time()
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/ping", "/invocations"]
    }), 404


if __name__ == '__main__':
    print("🚀 Starting WOTD inference server")
    
    # Load models on startup
    try:
        handler.load_models()
    except Exception as e:
        print(f"⚠️ Warning: Could not load models: {e}")
        print("Server will start but inference may not work properly")
    
    # Start Flask server
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)