"""Simple inference pipeline for WOTD system."""

import time
from dataclasses import dataclass

from .language_model import SimpleDSLModel, generate_with_dsl, parse_dsl_prompt
from .semantic_encoder import (
    SemanticID,
    SimpleSemanticEncoder,
    describe_semantic_id,
    similarity_score,
)


@dataclass
class GenerationResult:
    """Simple result from word generation."""
    words: list[str]
    semantic_id: SemanticID | None
    description: str | None
    processing_time: float
    confidence: float | None = None


class WOTDPipeline:
    """Simple WOTD inference pipeline."""
    
    def __init__(
        self,
        encoder: SimpleSemanticEncoder,
        dsl_model: SimpleDSLModel,
        semantic_ids: dict[str, SemanticID]
    ):
        self.encoder = encoder
        self.dsl_model = dsl_model
        self.semantic_ids = semantic_ids
        
    def generate(
        self,
        prompt: str,
        num_words: int = 10,
        temperature: float = 0.8
    ) -> GenerationResult:
        """Generate words from prompt."""
        
        start_time = time.time()
        
        # Parse DSL from prompt
        clean_prompt, semantic_id = parse_dsl_prompt(prompt)
        
        # If no DSL found, try to infer from natural language
        if semantic_id is None:
            semantic_id = self._infer_semantic_id_from_text(clean_prompt)
        
        # Generate words
        words = generate_with_dsl(
            self.dsl_model,
            prompt,
            max_length=num_words * 3,  # Rough estimate
            temperature=temperature
        )
        
        # Limit to requested number
        words = words[:num_words]
        
        # Get description if we have semantic ID
        description = None
        if semantic_id and all(x >= 0 for x in semantic_id):
            description = describe_semantic_id(semantic_id)
        
        processing_time = time.time() - start_time
        
        return GenerationResult(
            words=words,
            semantic_id=semantic_id,
            description=description,
            processing_time=processing_time
        )
    
    def generate_by_name(
        self,
        corpus_name: str,
        context: str | None = None,
        num_words: int = 10
    ) -> GenerationResult:
        """Generate words using named corpus preference."""
        
        if corpus_name not in self.semantic_ids:
            raise ValueError(f"Unknown corpus: {corpus_name}")
        
        semantic_id = self.semantic_ids[corpus_name]
        id_str = f"[{','.join(map(str, semantic_id))}]"
        
        prompt = f"Generate {id_str} words"
        if context:
            prompt += f" about {context}"
        prompt += ":"
        
        return self.generate(prompt, num_words)
    
    def interpolate_generate(
        self,
        corpus1: str,
        corpus2: str,
        alpha: float = 0.5,
        context: str | None = None,
        num_words: int = 10
    ) -> GenerationResult:
        """Generate words from interpolated preferences."""
        
        if corpus1 not in self.semantic_ids or corpus2 not in self.semantic_ids:
            raise ValueError("Unknown corpus names")
        
        # Interpolate Semantic IDs
        from .semantic_encoder import interpolate_semantic_ids
        id1 = self.semantic_ids[corpus1]
        id2 = self.semantic_ids[corpus2]
        
        interpolated_id = interpolate_semantic_ids(self.encoder, id1, id2, alpha)
        
        # Create prompt
        id_str = f"[{','.join(map(str, interpolated_id))}]"
        prompt = f"Generate {id_str} words"
        if context:
            prompt += f" about {context}"
        prompt += ":"
        
        result = self.generate(prompt, num_words)
        result.semantic_id = interpolated_id
        
        return result
    
    def find_similar_words(
        self,
        reference_corpus: str,
        num_words: int = 10,
        similarity_threshold: float = 0.5
    ) -> GenerationResult:
        """Find words similar to a reference corpus."""
        
        if reference_corpus not in self.semantic_ids:
            raise ValueError(f"Unknown corpus: {reference_corpus}")
        
        reference_id = self.semantic_ids[reference_corpus]
        
        # Find similar corpus
        similar_corpora = []
        for name, semantic_id in self.semantic_ids.items():
            if name != reference_corpus:
                sim = similarity_score(reference_id, semantic_id)
                if sim >= similarity_threshold:
                    similar_corpora.append((name, sim))
        
        # Sort by similarity
        similar_corpora.sort(key=lambda x: x[1], reverse=True)
        
        if similar_corpora:
            # Use most similar corpus
            best_match = similar_corpora[0][0]
            return self.generate_by_name(best_match, num_words=num_words)
        else:
            # Fallback to reference corpus
            return self.generate_by_name(reference_corpus, num_words=num_words)
    
    def get_semantic_ids(self) -> dict[str, SemanticID]:
        """Get all learned semantic IDs."""
        return self.semantic_ids.copy()
    
    def _infer_semantic_id_from_text(self, text: str) -> SemanticID | None:
        """Simple heuristic to infer Semantic ID from natural language."""
        
        text_lower = text.lower()
        
        # Simple keyword mapping
        if any(word in text_lower for word in ['shakespeare', 'elizabethan', 'thou', 'doth']):
            return [0, 0, 0, -1]  # Classical + beautiful + shakespearean
        elif any(word in text_lower for word in ['beautiful', 'elegant', 'gorgeous']):
            return [-1, 0, -1, -1]  # Beautiful (any style)
        elif any(word in text_lower for word in ['simple', 'basic', 'easy']):
            return [-1, 1, -1, -1]  # Simple (any style)
        elif any(word in text_lower for word in ['modern', 'contemporary', 'current']):
            return [1, -1, -1, -1]  # Modern (any aesthetic)
        elif any(word in text_lower for word in ['complex', 'sophisticated', 'intricate']):
            return [-1, 2, -1, -1]  # Complex (any style)
        
        return None
    
    def explain_result(self, result: GenerationResult) -> str:
        """Explain how the result was generated."""
        
        explanation = f"Generated {len(result.words)} words in {result.processing_time:.2f}s\n"
        
        if result.semantic_id:
            explanation += f"Semantic ID: {result.semantic_id}\n"
            if result.description:
                explanation += f"Style: {result.description}\n"
        
        explanation += f"Words: {', '.join(result.words)}"
        
        return explanation


def create_pipeline(
    encoder_path: str,
    model_path: str,
    semantic_ids: dict[str, SemanticID]
) -> WOTDPipeline:
    """Create inference pipeline from saved models."""
    
    from .language_model import load_dsl_model
    from .semantic_encoder import load_encoder
    
    print("Loading semantic encoder...")
    encoder = load_encoder(encoder_path)
    
    print("Loading DSL model...")
    dsl_model = load_dsl_model(model_path)
    
    print("Creating pipeline...")
    pipeline = WOTDPipeline(encoder, dsl_model, semantic_ids)
    
    return pipeline


# Quick test function
def test_pipeline() -> None:
    """Test pipeline with dummy data."""
    
    # Create dummy models (would be loaded from disk in practice)
    from .language_model import SimpleDSLModel
    from .semantic_encoder import EncoderConfig, SimpleSemanticEncoder
    
    encoder = SimpleSemanticEncoder(EncoderConfig())
    dsl_model = SimpleDSLModel()
    
    semantic_ids = {
        'shakespeare': [0, 0, 0, 5],
        'modern': [1, 1, 3, 2],
        'beautiful': [2, 0, 3, 1]
    }
    
    pipeline = WOTDPipeline(encoder, dsl_model, semantic_ids)
    
    # Test different generation modes
    test_prompts = [
        "Generate [0,0,*,*] words",
        "Create beautiful words about nature", 
        "Simple modern words"
    ]
    
    for prompt in test_prompts:
        print(f"\nTesting: '{prompt}'")
        result = pipeline.generate(prompt, num_words=5)
        print(pipeline.explain_result(result))


if __name__ == "__main__":
    test_pipeline()