"""DSL-aware language model for word generation."""

import re
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.utils.data import Dataset
from transformers import GPT2LMHeadModel, GPT2Tokenizer, Trainer
from transformers.training_args import TrainingArguments

from .semantic_encoder import SemanticID, SimpleSemanticEncoder


@dataclass
class DSLTrainingExample:
    """Simple training example for DSL learning."""
    prompt: str
    target: str
    semantic_id: SemanticID | None = None


class DSLDataset(Dataset[dict[str, torch.Tensor]]):
    """Simple dataset for DSL training."""
    
    def __init__(self, examples: list[DSLTrainingExample], tokenizer: GPT2Tokenizer):
        self.examples = examples
        self.tokenizer = tokenizer
        
    def __len__(self) -> int:
        return len(self.examples)
    
    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        example = self.examples[idx]
        
        # Combine prompt and target
        full_text = f"{example.prompt} {example.target}"
        
        # Tokenize
        encoding = self.tokenizer(
            full_text,
            truncation=True,
            padding='max_length',
            max_length=128,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': encoding['input_ids'].squeeze()
        }


class SimpleDSLModel(nn.Module):
    """Simple DSL-aware language model."""
    
    def __init__(self, base_model: str = "gpt2"):
        super().__init__()
        
        # Load base model
        self.model = GPT2LMHeadModel.from_pretrained(base_model)
        self.tokenizer = GPT2Tokenizer.from_pretrained(base_model)
        
        # Add padding token
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Add DSL tokens
        self._add_dsl_tokens()
        
    def _add_dsl_tokens(self) -> None:
        """Add special tokens for DSL."""
        dsl_tokens = [
            "[ID]", "[/ID]", "[*]"
        ] + [f"[{i}]" for i in range(32)]  # Code tokens
        
        self.tokenizer.add_special_tokens({
            'additional_special_tokens': dsl_tokens
        })
        self.model.resize_token_embeddings(len(self.tokenizer))
    
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None, labels: torch.Tensor | None = None) -> torch.Tensor:
        """Forward pass."""
        output = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )
        return output  # type: ignore[no-any-return]


def parse_dsl_prompt(prompt: str) -> tuple[str, SemanticID | None]:
    """
    Parse DSL from prompt.
    
    Examples:
        "Generate [0,1,*,*] words" -> ("Generate words", [0,1,-1,-1])
        "Create [2,3,1,0] about time" -> ("Create about time", [2,3,1,0])
    """
    # Find pattern [n,n,n,n] or [n,n,*,*]
    pattern = r'\[(\d+|\*),(\d+|\*),(\d+|\*),(\d+|\*)\]'
    match = re.search(pattern, prompt)
    
    if match:
        # Remove DSL from prompt
        clean_prompt = re.sub(pattern, "", prompt).strip()
        
        # Parse semantic ID
        codes = []
        for code in match.groups():
            if code == '*':
                codes.append(-1)  # Wildcard marker
            else:
                codes.append(int(code))
        
        return clean_prompt, codes
    
    return prompt, None


def create_dsl_training_data(
    word_corpora: dict[str, list[str]],
    semantic_ids: dict[str, SemanticID]
) -> list[DSLTrainingExample]:
    """Create training examples for DSL understanding."""
    
    examples = []
    
    # Exact Semantic ID examples
    for corpus_name, words in word_corpora.items():
        if corpus_name in semantic_ids:
            semantic_id = semantic_ids[corpus_name]
            id_str = f"[{','.join(map(str, semantic_id))}]"
            
            # Sample words for training
            sample_words = words[:10] if len(words) >= 10 else words
            target = ' '.join(sample_words)
            
            examples.extend([
                DSLTrainingExample(f"Generate {id_str} words:", target, semantic_id),
                DSLTrainingExample(f"Create {id_str}:", target, semantic_id),
                DSLTrainingExample(f"Words like {id_str}:", target, semantic_id),
            ])
    
    # Wildcard examples
    examples.extend([
        DSLTrainingExample(
            "Generate [0,*,*,*] words:",
            "doth wherefore beauteous thou fair",
            [0, -1, -1, -1]
        ),
        DSLTrainingExample(
            "Create [*,0,*,*] words:",
            "luminous ethereal beautiful magnificent",
            [-1, 0, -1, -1]
        ),
        DSLTrainingExample(
            "Simple [*,1,*,*] words:",
            "run walk see think go",
            [-1, 1, -1, -1]
        )
    ])
    
    # Mixed natural language + DSL
    examples.extend([
        DSLTrainingExample(
            "Generate [0,0,*,*] words about love:",
            "amorous beauteous cherish adore",
            [0, 0, -1, -1]
        ),
        DSLTrainingExample(
            "Create elegant [*,0,*,*] words:",
            "graceful exquisite sublime refined",
            [-1, 0, -1, -1]
        )
    ])
    
    return examples


def train_dsl_model(
    word_corpora: dict[str, list[str]],
    semantic_ids: dict[str, SemanticID],
    output_dir: str = "models/dsl_model",
    num_epochs: int = 10
) -> SimpleDSLModel:
    """Train DSL-aware language model."""
    
    print("Creating DSL training data...")
    training_examples = create_dsl_training_data(word_corpora, semantic_ids)
    
    print(f"Training on {len(training_examples)} examples...")
    
    # Initialize model
    model = SimpleDSLModel()
    
    # Create dataset
    dataset = DSLDataset(training_examples, model.tokenizer)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="no",  # No validation for simplicity
        learning_rate=2e-5,
        fp16=True,  # Mixed precision for performance
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=model.tokenizer,
    )
    
    # Train
    trainer.train()  # type: ignore[attr-defined]
    
    # Save
    trainer.save_model()  # type: ignore[attr-defined]
    
    return model


def generate_with_dsl(
    model: SimpleDSLModel,
    prompt: str,
    max_length: int = 50,
    temperature: float = 0.8,
    top_p: float = 0.95
) -> list[str]:
    """
    Generate words using DSL-aware model.
    
    Examples:
        "Generate [0,0,*,*] words" -> ['beauteous', 'resplendent', ...]
        "Create [*,1,*,*] simple words" -> ['run', 'walk', 'see', ...]
    """
    
    # Tokenize input
    inputs = model.tokenizer(prompt, return_tensors='pt')
    
    # Generate
    with torch.no_grad():
        outputs = model.model.generate(
            **inputs,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=model.tokenizer.pad_token_id,
            eos_token_id=model.tokenizer.eos_token_id,
        )
    
    # Decode
    generated_text = model.tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract words (remove prompt, split on whitespace, filter)
    result_text = generated_text.replace(prompt, '').strip()
    words = [w for w in result_text.split() if w.isalpha() and len(w) > 1]
    
    return words


def interpolate_dsl_generation(
    model: SimpleDSLModel,
    encoder: SimpleSemanticEncoder,
    id1: SemanticID,
    id2: SemanticID,
    alpha: float = 0.5,
    context: str = "words"
) -> list[str]:
    """Generate words from interpolated Semantic IDs."""
    
    # Interpolate in vector space
    from .semantic_encoder import interpolate_semantic_ids
    interpolated_id = interpolate_semantic_ids(encoder, id1, id2, alpha)
    
    # Create DSL prompt
    id_str = f"[{','.join(map(str, interpolated_id))}]"
    prompt = f"Generate {id_str} {context}:"
    
    # Generate
    return generate_with_dsl(model, prompt)


def save_dsl_model(model: SimpleDSLModel, path: str) -> None:
    """Save DSL model to disk."""
    model.model.save_pretrained(path)
    model.tokenizer.save_pretrained(path)


def load_dsl_model(path: str) -> SimpleDSLModel:
    """Load DSL model from disk."""
    model = SimpleDSLModel.__new__(SimpleDSLModel)
    model.model = GPT2LMHeadModel.from_pretrained(path)
    model.tokenizer = GPT2Tokenizer.from_pretrained(path)
    return model


# Utility functions for quick testing
def test_dsl_generation() -> None:
    """Test DSL generation with sample data."""
    
    print("Testing DSL prompt parsing...")
    
    test_prompts = [
        "Generate [0,0,*,*] words",
        "Create [1,1,3,2] about time",
        "Simple words please"
    ]
    
    for prompt in test_prompts:
        clean_prompt, semantic_id = parse_dsl_prompt(prompt)
        print(f"'{prompt}' -> '{clean_prompt}' + {semantic_id}")


if __name__ == "__main__":
    test_dsl_generation()