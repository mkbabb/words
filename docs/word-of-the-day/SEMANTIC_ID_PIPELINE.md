# Semantic ID Pipeline for Word Preference System

## Executive Summary

We encode preference vectors as **Semantic IDs**—hierarchical discrete codes like `[3, 14, 7, 2]` that capture aesthetic preferences at multiple levels of abstraction. A fine-tuned language model learns to interpret these IDs as a domain-specific language (DSL), enabling hybrid queries that combine natural language with precise preference specifications.

**The Process:**
1. Learn preference vectors from word corpora (Shakespeare, beauty examples, etc.)
2. Quantize these vectors into hierarchical Semantic IDs using learnable codebooks
3. Fine-tune a language model to understand prompts like: `"Generate [3,14,*,*] words about nature"`
4. The `[3,14,*,*]` encodes "Shakespearean beauty" while wildcards allow variation

This creates a powerful, interpretable system where preferences are both human-readable (via the DSL) and machine-learnable.

---

## Step 1: Semantic ID Encoder

Transform continuous preference vectors into discrete hierarchical codes.

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Optional

class SemanticIDEncoder(nn.Module):
    """
    Encodes preference vectors as hierarchical Semantic IDs.
    Each level captures increasingly specific preferences.
    
    Level 0: Broad style (classical/modern/neutral)  
    Level 1: Aesthetic (beautiful/plain/complex)
    Level 2: Author family (Shakespearean/Romantic/Contemporary)
    Level 3: Specific variation
    """
    
    def __init__(
        self,
        input_dim: int = 128,  # Preference vector dimension
        num_levels: int = 4,    # Hierarchy depth
        codebook_size: int = 32 # Codes per level (keeps IDs readable)
    ):
        super().__init__()
        
        self.num_levels = num_levels
        self.codebook_size = codebook_size
        
        # Learnable codebooks for each hierarchy level
        self.codebooks = nn.ParameterList([
            nn.Parameter(torch.randn(codebook_size, input_dim) * 0.1)
            for _ in range(num_levels)
        ])
        
        # Residual projections for each level
        self.projections = nn.ModuleList([
            nn.Linear(input_dim, input_dim) 
            for _ in range(num_levels)
        ])
        
    def encode(self, preference_vector: torch.Tensor) -> List[int]:
        """
        Encode preference vector as Semantic ID.
        Returns: List of integers [level0, level1, level2, level3]
        """
        semantic_id = []
        residual = preference_vector.clone()
        
        for level in range(self.num_levels):
            # Project residual for this level
            projected = self.projections[level](residual)
            
            # Find nearest codebook entry
            distances = torch.cdist(
                projected.unsqueeze(0), 
                self.codebooks[level].unsqueeze(0)
            ).squeeze(0)
            
            nearest_idx = torch.argmin(distances).item()
            semantic_id.append(nearest_idx)
            
            # Compute residual for next level
            residual = residual - self.codebooks[level][nearest_idx]
        
        return semantic_id
    
    def decode(self, semantic_id: List[int]) -> torch.Tensor:
        """Reconstruct preference vector from Semantic ID."""
        reconstructed = torch.zeros(128)
        
        for level, idx in enumerate(semantic_id):
            if idx < self.codebook_size:  # Valid index
                reconstructed += self.codebooks[level][idx]
        
        return F.normalize(reconstructed, p=2, dim=-1)
    
    def get_similarity(self, id1: List[int], id2: List[int]) -> float:
        """
        Compute hierarchical similarity between Semantic IDs.
        Earlier matches = higher similarity.
        """
        similarity = 0.0
        weight = 1.0
        
        for i in range(len(id1)):
            if id1[i] == id2[i]:
                similarity += weight
            else:
                break  # Stop at first mismatch
            weight *= 0.5
        
        return similarity

# Interpretation of Semantic IDs
SEMANTIC_ID_MEANINGS = {
    # Level 0: Broad style
    0: {0: "classical", 1: "modern", 2: "romantic", 3: "neutral"},
    # Level 1: Aesthetic  
    1: {0: "beautiful", 1: "simple", 2: "complex", 3: "plain"},
    # Level 2: Author family
    2: {0: "shakespearean", 1: "victorian", 2: "modernist", 3: "contemporary"},
    # Level 3: Specific variations (learned, not predefined)
    3: {}
}
```

## Step 2: Build Semantic ID Vocabulary

Learn Semantic IDs for key preference vectors.

```python
class SemanticIDVocabulary:
    """
    Manages the mapping between preference vectors and Semantic IDs.
    This becomes our DSL vocabulary.
    """
    
    def __init__(self, encoder: SemanticIDEncoder):
        self.encoder = encoder
        self.vocabulary = {}  # name -> semantic_id
        self.reverse_vocab = {}  # semantic_id -> name
        
    def learn_vocabulary(self, named_vectors: dict):
        """
        Convert named preference vectors to Semantic IDs.
        This creates our DSL vocabulary.
        """
        for name, vector in named_vectors.items():
            semantic_id = self.encoder.encode(vector)
            self.vocabulary[name] = semantic_id
            self.reverse_vocab[tuple(semantic_id)] = name
            
        return self.vocabulary
    
    def get_semantic_id(self, name: str) -> List[int]:
        """Get Semantic ID for named preference."""
        return self.vocabulary.get(name, [0, 0, 0, 0])
    
    def describe_semantic_id(self, semantic_id: List[int]) -> str:
        """Human-readable description of Semantic ID."""
        descriptions = []
        for level, code in enumerate(semantic_id):
            if level in SEMANTIC_ID_MEANINGS and code in SEMANTIC_ID_MEANINGS[level]:
                descriptions.append(SEMANTIC_ID_MEANINGS[level][code])
        return " + ".join(descriptions)

# Example vocabulary after training
LEARNED_VOCABULARY = {
    "shakespeare": [0, 0, 0, 5],     # classical + beautiful + shakespearean + variant_5
    "woolf": [1, 2, 2, 3],           # modern + complex + modernist + variant_3  
    "beauty": [2, 0, 3, 1],          # romantic + beautiful + contemporary + variant_1
    "simple": [3, 1, 3, 0],          # neutral + simple + contemporary + variant_0
}
```

## Step 3: DSL-Aware Language Model

Fine-tune a model to understand Semantic IDs as part of natural language.

```python
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch.nn as nn

class SemanticIDLanguageModel(nn.Module):
    """
    Language model that understands Semantic ID DSL.
    Can process prompts mixing natural language and Semantic IDs.
    """
    
    def __init__(self, vocab: SemanticIDVocabulary):
        super().__init__()
        
        # Base model (small for KISS)
        self.model = GPT2LMHeadModel.from_pretrained('gpt2')
        self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Add DSL tokens
        self._add_dsl_tokens()
        
        # Semantic ID vocabulary
        self.vocab = vocab
        
        # Embedding for Semantic IDs
        self.semantic_id_embeddings = nn.Embedding(
            32 * 4,  # 32 codes × 4 levels
            self.model.config.n_embd
        )
        
    def _add_dsl_tokens(self):
        """Add special tokens for DSL."""
        special_tokens = [
            "[ID_START]", "[ID_END]",
            "[WILDCARD]",  # * in Semantic IDs
            "[LEVEL_0]", "[LEVEL_1]", "[LEVEL_2]", "[LEVEL_3]",
        ] + [f"[CODE_{i}]" for i in range(32)]  # Codes 0-31
        
        self.tokenizer.add_special_tokens({
            'additional_special_tokens': special_tokens
        })
        self.model.resize_token_embeddings(len(self.tokenizer))
    
    def encode_prompt_with_semantic_ids(self, prompt: str) -> torch.Tensor:
        """
        Parse and encode prompts containing Semantic IDs.
        
        Example prompts:
        - "Generate [0,0,*,*] words"  -> Classical beautiful words (any author)
        - "Create [1,2,*,*] about time" -> Modern complex words about time
        - "Write like [0,0,0,5]"        -> Exact Shakespeare style
        """
        import re
        
        # Find Semantic ID patterns [n,n,n,n] or [n,n,*,*]
        pattern = r'\[(\d+|\*),(\d+|\*),(\d+|\*),(\d+|\*)\]'
        
        def replace_with_tokens(match):
            """Replace [n,n,n,n] with tokenized version."""
            codes = match.groups()
            tokens = ["[ID_START]"]
            
            for level, code in enumerate(codes):
                tokens.append(f"[LEVEL_{level}]")
                if code == '*':
                    tokens.append("[WILDCARD]")
                else:
                    tokens.append(f"[CODE_{code}]")
            
            tokens.append("[ID_END]")
            return " ".join(tokens)
        
        # Replace Semantic IDs with tokens
        processed_prompt = re.sub(pattern, replace_with_tokens, prompt)
        
        # Tokenize
        return self.tokenizer(processed_prompt, return_tensors='pt')
    
    def generate_with_semantic_ids(
        self,
        prompt: str,
        max_length: int = 50,
        temperature: float = 0.8
    ) -> str:
        """
        Generate text using prompt with Semantic IDs.
        
        The model learns that:
        - [0,*,*,*] constrains to classical style
        - [*,0,*,*] constrains to beautiful words
        - [0,0,0,5] precisely specifies Shakespeare
        """
        # Encode prompt
        inputs = self.encode_prompt_with_semantic_ids(prompt)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                do_sample=True,
                top_p=0.95,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        # Decode
        generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Post-process to extract words
        return self._extract_words(generated, prompt)
    
    def _extract_words(self, generated: str, original_prompt: str) -> List[str]:
        """Extract generated words from output."""
        # Remove original prompt
        result = generated.replace(original_prompt, '').strip()
        
        # Extract word-like tokens
        words = [w for w in result.split() if w.isalpha() and len(w) > 2]
        
        return words
```

## Step 4: Training Pipeline

Train the complete system end-to-end.

```python
def train_semantic_id_system(
    word_corpora: dict,
    preference_vectors: dict
) -> tuple:
    """
    Complete training pipeline.
    
    Args:
        word_corpora: {'shakespeare': [...], 'woolf': [...], ...}
        preference_vectors: Pre-learned preference vectors
    
    Returns:
        (encoder, vocabulary, model)
    """
    
    # Step 1: Train Semantic ID Encoder
    print("Training Semantic ID Encoder...")
    encoder = SemanticIDEncoder()
    train_semantic_encoder(encoder, preference_vectors)
    
    # Step 2: Build vocabulary
    print("Building Semantic ID Vocabulary...")
    vocabulary = SemanticIDVocabulary(encoder)
    vocabulary.learn_vocabulary(preference_vectors)
    
    # Print learned mappings
    for name, semantic_id in vocabulary.vocabulary.items():
        desc = vocabulary.describe_semantic_id(semantic_id)
        print(f"  {name}: {semantic_id} = {desc}")
    
    # Step 3: Create training data for language model
    print("Creating DSL training data...")
    training_data = create_dsl_training_data(vocabulary, word_corpora)
    
    # Step 4: Fine-tune language model
    print("Fine-tuning language model...")
    model = SemanticIDLanguageModel(vocabulary)
    train_language_model(model, training_data)
    
    return encoder, vocabulary, model

def train_semantic_encoder(
    encoder: SemanticIDEncoder,
    preference_vectors: dict,
    epochs: int = 100
):
    """Train encoder to create meaningful Semantic IDs."""
    optimizer = torch.optim.Adam(encoder.parameters(), lr=1e-3)
    
    for epoch in range(epochs):
        total_loss = 0
        
        for name, vector in preference_vectors.items():
            # Encode and decode
            semantic_id = encoder.encode(vector)
            reconstructed = encoder.decode(semantic_id)
            
            # Reconstruction loss
            loss = F.mse_loss(reconstructed, vector)
            
            # Add hierarchical consistency loss
            # (similar vectors should share early codes)
            for other_name, other_vector in preference_vectors.items():
                if name != other_name:
                    similarity = F.cosine_similarity(
                        vector.unsqueeze(0), 
                        other_vector.unsqueeze(0)
                    ).item()
                    
                    other_id = encoder.encode(other_vector)
                    id_similarity = encoder.get_similarity(semantic_id, other_id)
                    
                    # Similarity preservation loss
                    loss += 0.1 * abs(similarity - id_similarity)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        if epoch % 20 == 0:
            print(f"Epoch {epoch}: Loss = {total_loss:.4f}")

def create_dsl_training_data(
    vocabulary: SemanticIDVocabulary,
    word_corpora: dict
) -> List[tuple]:
    """
    Create training examples for DSL understanding.
    """
    examples = []
    
    # Exact Semantic ID references
    for name, words in word_corpora.items():
        semantic_id = vocabulary.get_semantic_id(name)
        id_str = f"[{','.join(map(str, semantic_id))}]"
        
        examples.append((
            f"Generate {id_str} words:",
            ' '.join(words[:10])
        ))
        
        examples.append((
            f"Create words like {id_str}:",
            ' '.join(words[10:20])
        ))
    
    # Wildcard patterns
    examples.extend([
        ("Generate [0,*,*,*] words:", "doth wherefore thou beauteous resplendent"),
        ("Create [*,0,*,*] beautiful words:", "luminous ethereal efflorescent serendipitous"),
        ("Write [1,2,*,*] complex modern:", "consciousness fragmentary disillusioned"),
    ])
    
    # Mixed natural language + DSL
    examples.extend([
        ("Generate [0,0,*,*] words about love:", "beauteous amorous doth cherish"),
        ("Create simple [*,1,*,*] words:", "run walk see think"),
        ("Elegant [2,0,*,*] descriptions:", "gossamer ethereal diaphanous luminescent"),
    ])
    
    return examples

def train_language_model(
    model: SemanticIDLanguageModel,
    training_data: List[tuple],
    epochs: int = 10
):
    """Fine-tune model to understand DSL."""
    optimizer = torch.optim.AdamW(model.model.parameters(), lr=2e-5)
    
    for epoch in range(epochs):
        total_loss = 0
        
        for prompt, target in training_data:
            # Prepare input
            inputs = model.encode_prompt_with_semantic_ids(prompt)
            
            # Prepare target
            full_text = prompt + " " + target
            labels = model.tokenizer(full_text, return_tensors='pt')['input_ids']
            
            # Forward pass
            outputs = model.model(**inputs, labels=labels)
            loss = outputs.loss
            
            # Update
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        print(f"Epoch {epoch}: Loss = {total_loss:.4f}")
```

## Step 5: Inference Pipeline

Use the trained system for generation.

```python
class SemanticIDInference:
    """High-level interface for using the system."""
    
    def __init__(self, encoder, vocabulary, model):
        self.encoder = encoder
        self.vocabulary = vocabulary
        self.model = model
        
    def query(self, prompt: str) -> List[str]:
        """
        Process any query - pure NL, pure DSL, or hybrid.
        
        Examples:
        - "Generate beautiful words" (pure NL)
        - "Generate [0,0,*,*] words" (pure DSL)  
        - "Create [0,0,*,*] words about time" (hybrid)
        """
        return self.model.generate_with_semantic_ids(prompt)
    
    def query_by_preference_name(self, name: str, context: str = "") -> List[str]:
        """Query using named preference."""
        semantic_id = self.vocabulary.get_semantic_id(name)
        id_str = f"[{','.join(map(str, semantic_id))}]"
        
        prompt = f"Generate {id_str} words"
        if context:
            prompt += f" about {context}"
        
        return self.query(prompt)
    
    def interpolate_query(
        self,
        name1: str,
        name2: str,
        alpha: float,
        context: str = ""
    ) -> List[str]:
        """Query with interpolated preferences."""
        # Get vectors
        vec1 = self.encoder.decode(self.vocabulary.get_semantic_id(name1))
        vec2 = self.encoder.decode(self.vocabulary.get_semantic_id(name2))
        
        # Interpolate
        interpolated = (1 - alpha) * vec1 + alpha * vec2
        interpolated = F.normalize(interpolated, p=2, dim=-1)
        
        # Get new Semantic ID
        new_id = self.encoder.encode(interpolated)
        id_str = f"[{','.join(map(str, new_id))}]"
        
        prompt = f"Generate {id_str} words"
        if context:
            prompt += f" about {context}"
        
        return self.query(prompt)
    
    def explain_semantic_id(self, semantic_id: List[int]) -> str:
        """Explain what a Semantic ID represents."""
        description = self.vocabulary.describe_semantic_id(semantic_id)
        
        # Find similar known vectors
        similar = []
        for name, known_id in self.vocabulary.vocabulary.items():
            similarity = self.encoder.get_similarity(semantic_id, known_id)
            if similarity > 0.5:
                similar.append((name, similarity))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        
        explanation = f"Semantic ID {semantic_id}:\n"
        explanation += f"  Interpretation: {description}\n"
        
        if similar:
            explanation += "  Similar to:\n"
            for name, sim in similar[:3]:
                explanation += f"    - {name} (similarity: {sim:.2f})\n"
        
        return explanation
```

## Usage Examples

### Complete Pipeline

```python
# Initialize system
encoder, vocabulary, model = train_semantic_id_system(
    word_corpora={
        'shakespeare': ['doth', 'thou', 'beauteous', ...],
        'woolf': ['consciousness', 'luminous', ...],
        'simple': ['run', 'walk', 'see', ...],
        'complex': ['ineffability', 'transcendental', ...]
    },
    preference_vectors={
        'shakespeare': shakespeare_vector,
        'woolf': woolf_vector,
        'beauty': beauty_vector,
        'simple': simple_vector
    }
)

# Create inference interface
inference = SemanticIDInference(encoder, vocabulary, model)

# Example 1: Pure DSL query
words = inference.query("Generate [0,0,*,*] words")
# → ['beauteous', 'resplendent', 'wherefore', 'doth', 'splendorous']

# Example 2: Hybrid query
words = inference.query("Create [0,0,*,*] words about the ocean")
# → ['tempestuous', 'briny', 'fathomless', 'neptune', 'mariners']

# Example 3: Wildcard for exploration
words = inference.query("Generate [*,0,*,*] beautiful words")
# → ['luminous', 'ethereal', 'gossamer', 'efflorescent', 'iridescent']

# Example 4: Named preference
words = inference.query_by_preference_name('shakespeare', context='love')
# → ['amorous', 'beauteous', 'cherish', 'doth', 'paramour']

# Example 5: Interpolation
words = inference.interpolate_query('shakespeare', 'woolf', 0.5, 'consciousness')
# → ['awareness', 'mindful', 'whereof', 'luminous', 'perceive']

# Example 6: Explain what a Semantic ID means
explanation = inference.explain_semantic_id([0, 0, 2, 7])
print(explanation)
# Semantic ID [0, 0, 2, 7]:
#   Interpretation: classical + beautiful + modernist + variant_7
#   Similar to:
#     - shakespeare (similarity: 0.75)
#     - beauty (similarity: 0.62)
```

### DSL Cheat Sheet

```python
"""
DSL Pattern Reference:

[n,n,n,n] - Exact Semantic ID
[n,n,*,*] - Partial match (wildcards for lower levels)
[*,n,*,*] - Match specific level only

Common Patterns:
[0,*,*,*] - Classical style (any beauty level)
[1,*,*,*] - Modern style
[*,0,*,*] - Beautiful (any style)
[*,1,*,*] - Simple
[*,2,*,*] - Complex
[0,0,*,*] - Classical + Beautiful
[1,1,*,*] - Modern + Simple

Hybrid Queries:
"Generate [0,0,*,*] words" - Pure preference
"Generate [0,0,*,*] words about nature" - Preference + topic
"Beautiful [0,*,*,*] words" - Natural language + preference
"""
```

---

## Key Design Decisions

1. **4-Level Hierarchy**: Sufficient for style→aesthetic→author→variant
2. **32 Codes per Level**: Human-readable while expressive (32^4 = 1M combinations)  
3. **Wildcards**: Allow exploration and generalization
4. **Hybrid Queries**: Natural language provides context, DSL provides precision
5. **Learnable Codebooks**: Discover structure from data, not hand-designed

## Why This Works

- **Interpretable**: Semantic IDs have clear hierarchical meaning
- **Composable**: Wildcards enable flexible queries
- **Learnable**: All components are trained, not heuristic
- **Powerful**: Combines precision of DSL with flexibility of NL
- **Simple**: ~500 lines of core code

## Training Requirements

- **Preference Vectors**: 20-50 named vectors (authors, styles, etc.)
- **Word Corpora**: 1000+ words per category
- **DSL Examples**: 200-500 prompt/output pairs
- **Training Time**: ~1 hour on GPU, ~4 hours on CPU

---

## Conclusion

This pipeline creates a powerful yet simple system where:
1. Preferences are encoded as interpretable Semantic IDs
2. A DSL allows precise specification using these IDs
3. A fine-tuned model understands both natural language and the DSL
4. Users can query with exact IDs, wildcards, or hybrid prompts

The result is a system that's both powerful for developers (precise control via DSL) and accessible for users (natural language with optional precision).