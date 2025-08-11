"""Semantic ID encoder - converts preference vectors to hierarchical discrete codes."""

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

# Simple types
SemanticID = list[int]  # [level0, level1, level2, level3]
PreferenceVector = torch.Tensor  # shape: [128]


@dataclass
class EncoderConfig:
    """Simple encoder configuration."""
    num_levels: int = 4
    codebook_size: int = 32
    hidden_dim: int = 128
    learning_rate: float = 1e-3
    num_epochs: int = 100


class SimpleSemanticEncoder(nn.Module):
    """Minimal semantic encoder for preference vectors."""
    
    def __init__(self, config: EncoderConfig):
        super().__init__()
        self.config = config
        
        # Learnable codebooks for each level
        self.codebooks = nn.ParameterList([
            nn.Parameter(torch.randn(config.codebook_size, config.hidden_dim) * 0.1)
            for _ in range(config.num_levels)
        ])
        
    def encode(self, preference_vector: PreferenceVector) -> SemanticID:
        """Convert preference vector to Semantic ID."""
        semantic_id = []
        residual = preference_vector.clone()
        
        for level in range(self.config.num_levels):
            # Find nearest codebook entry
            distances = torch.cdist(
                residual.unsqueeze(0),
                self.codebooks[level].unsqueeze(0)
            ).squeeze()
            
            nearest_idx: int = int(torch.argmin(distances).item())
            semantic_id.append(nearest_idx)
            
            # Subtract for next level
            residual = residual - self.codebooks[level][nearest_idx]
            
        return semantic_id
    
    def decode(self, semantic_id: SemanticID) -> PreferenceVector:
        """Convert Semantic ID back to preference vector."""
        result = torch.zeros(self.config.hidden_dim)
        
        for level, idx in enumerate(semantic_id):
            if 0 <= idx < self.config.codebook_size:
                result += self.codebooks[level][idx]
                
        return F.normalize(result, p=2, dim=-1)


def learn_preference_vectors(word_corpora: dict[str, list[str]]) -> dict[str, PreferenceVector]:
    """Learn preference vectors from word corpora using BERT."""
    
    # Simple BERT encoder
    tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
    model = AutoModel.from_pretrained('bert-base-uncased')
    
    preference_vectors = {}
    
    for corpus_name, words in word_corpora.items():
        # Encode all words
        embeddings = []
        for word in words[:100]:  # Limit for performance
            tokens = tokenizer(word, return_tensors='pt', padding=True, truncation=True)
            with torch.no_grad():
                embedding = model(**tokens).last_hidden_state.mean(dim=1).squeeze()
            embeddings.append(embedding)
        
        # Average to get corpus preference vector
        if embeddings:
            corpus_vector = torch.stack(embeddings).mean(dim=0)
            preference_vectors[corpus_name] = F.normalize(corpus_vector, p=2, dim=-1)
    
    return preference_vectors


def train_semantic_encoder(
    preference_vectors: dict[str, PreferenceVector],
    config: EncoderConfig = EncoderConfig()
) -> SimpleSemanticEncoder:
    """Train semantic encoder on preference vectors."""
    
    encoder = SimpleSemanticEncoder(config)
    optimizer = torch.optim.Adam(encoder.parameters(), lr=config.learning_rate)
    
    vectors = list(preference_vectors.values())
    
    print(f"Training semantic encoder with {len(vectors)} vectors...")
    
    for epoch in range(config.num_epochs):
        total_loss = 0.0
        
        for vector in vectors:
            # Encode and decode
            semantic_id = encoder.encode(vector)
            reconstructed = encoder.decode(semantic_id)
            
            # Reconstruction loss
            loss = F.mse_loss(reconstructed, vector)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        if epoch % 20 == 0:
            avg_loss = total_loss / len(vectors)
            print(f"Epoch {epoch}: Loss = {avg_loss:.4f}")
    
    return encoder


def encode_words(
    encoder: SimpleSemanticEncoder,
    preference_vectors: dict[str, PreferenceVector]
) -> dict[str, SemanticID]:
    """Encode preference vectors to Semantic IDs."""
    
    semantic_ids = {}
    for name, vector in preference_vectors.items():
        semantic_ids[name] = encoder.encode(vector)
        
    return semantic_ids


def decode_semantic_ids(
    encoder: SimpleSemanticEncoder,
    semantic_ids: dict[str, SemanticID]
) -> dict[str, PreferenceVector]:
    """Decode Semantic IDs back to preference vectors."""
    
    preference_vectors = {}
    for name, semantic_id in semantic_ids.items():
        preference_vectors[name] = encoder.decode(semantic_id)
        
    return preference_vectors


def interpolate_semantic_ids(
    encoder: SimpleSemanticEncoder,
    id1: SemanticID,
    id2: SemanticID,
    alpha: float = 0.5
) -> SemanticID:
    """Interpolate between two Semantic IDs via vector space."""
    
    # Decode to vectors
    vec1 = encoder.decode(id1)
    vec2 = encoder.decode(id2)
    
    # Interpolate in vector space
    interpolated = (1 - alpha) * vec1 + alpha * vec2
    interpolated = F.normalize(interpolated, p=2, dim=-1)
    
    # Encode back
    return encoder.encode(interpolated)


def similarity_score(id1: SemanticID, id2: SemanticID) -> float:
    """Compute hierarchical similarity between Semantic IDs."""
    
    similarity = 0.0
    weight = 1.0
    
    for i, (code1, code2) in enumerate(zip(id1, id2)):
        if code1 == code2:
            similarity += weight
        else:
            break  # Stop at first mismatch
        weight *= 0.5
    
    return similarity


# Simple vocabulary for Semantic ID interpretation
LEVEL_MEANINGS = {
    0: {0: "classical", 1: "modern", 2: "romantic", 3: "neutral"},
    1: {0: "beautiful", 1: "simple", 2: "complex", 3: "plain"},
    2: {0: "shakespearean", 1: "victorian", 2: "modernist", 3: "contemporary"},
    3: {}  # Learned variations
}


def describe_semantic_id(semantic_id: SemanticID) -> str:
    """Get human-readable description of Semantic ID."""
    
    descriptions = []
    for level, code in enumerate(semantic_id):
        if level in LEVEL_MEANINGS and code in LEVEL_MEANINGS[level]:
            descriptions.append(LEVEL_MEANINGS[level][code])
    
    return " + ".join(descriptions) if descriptions else "unknown"


def save_encoder(encoder: SimpleSemanticEncoder, path: str) -> None:
    """Save encoder to disk."""
    torch.save({
        'model_state_dict': encoder.state_dict(),
        'config': encoder.config
    }, path)


def load_encoder(path: str) -> SimpleSemanticEncoder:
    """Load encoder from disk."""
    checkpoint = torch.load(path, map_location='cpu')
    encoder = SimpleSemanticEncoder(checkpoint['config'])
    encoder.load_state_dict(checkpoint['model_state_dict'])
    return encoder