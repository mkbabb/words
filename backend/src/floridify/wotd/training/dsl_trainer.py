"""Stage 4: DSL fine-tuning with language models.

This module handles the fine-tuning of large language models to generate
text conditioned on semantic IDs.
"""

from __future__ import annotations

from ..constants import QWEN_25_7B
from ..core import (
    CorpusDict,
    SemanticIDDict,
    TrainingConfig,
)


class DSLTrainer:
    """Stage 4: DSL fine-tuning with language models.

    This class handles the fine-tuning of large language models to generate
    text conditioned on semantic IDs. It uses parameter-efficient fine-tuning
    techniques to adapt pre-trained models for controlled generation.

    Architecture:
        Semantic ID -> Instruction Format -> LLM -> Generated Words

    The model learns to interpret semantic IDs as generation constraints,
    producing words that match the specified style, complexity, era, and
    variation attributes.

    Supported Models:
        - Qwen-2.5-7B: State-of-the-art 7B model with 32K context
        - Phi-4: Microsoft's 14B reasoning model with 128K context
        - Mistral Nemo: 12B Apache-licensed model with 128K context

    Training Approach:
        - LoRA (Low-Rank Adaptation): Adds trainable rank decomposition
          matrices to transformer layers, reducing parameters by 99%
        - Instruction tuning: Formats data as instruction-response pairs
        - Multi-template training: Uses various phrasings to improve
          generalization and prevent overfitting to specific formats
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model_name = config.base_model

        # Determine model type
        self.is_qwen_or_phi4 = self.model_name in [
            QWEN_25_7B,
            "microsoft/Phi-4",
            "mistralai/Mistral-Nemo-Instruct-2407",
        ]

    def create_training_examples(
        self,
        corpora_dict: CorpusDict,
        semantic_ids: SemanticIDDict,
    ) -> list[dict[str, str]]:
        """Generate training examples mapping semantic IDs to word lists.

        This method creates the training data for teaching the language model
        to understand the relationship between semantic IDs and word characteristics.

        Data Format:
            Each example consists of:
            - Instruction: Contains semantic ID and generation prompt
            - Response: Target word list from the corpus

        Template Variations:
            Multiple templates are used to prevent the model from memorizing
            a single format. This improves robustness at inference time.

        Example:
            Input: "[2,1,3,0] Generate classical beautiful modernist words"
            Output: "eloquent, sophisticated, nuanced, contemplative..."

        The semantic ID [2,1,3,0] encodes:
            - Style: 2 (classical)
            - Complexity: 1 (beautiful/simple)
            - Era: 3 (modernist)
            - Variation: 0 (base form)

        Args:
            corpora_dict: Mapping of corpus IDs to word collections
            semantic_ids: Mapping of corpus IDs to semantic IDs

        Returns:
            List of instruction-response pairs for training

        """
        examples = []

        for corpus_id, corpus in corpora_dict.items():
            if corpus_id in semantic_ids:
                semantic_id = semantic_ids[corpus_id]
                id_str = f"[{','.join(map(str, semantic_id))}]"

                # Get sample words from corpus
                sample_words = [w.word for w in corpus.words[:5]]
                word_list = ", ".join(sample_words)

                # Create training examples with appropriate formats
                if self.is_qwen_or_phi4:
                    # Enhanced templates for newer models
                    templates = [
                        f"Generate {id_str} words with style={corpus.style.value}, "
                        f"complexity={corpus.complexity.value}, era={corpus.era.value}: {word_list}",
                        f"Create semantic {id_str} vocabulary: {word_list}",
                        f"Words matching pattern {id_str}: {word_list}",
                        f"<semantic>{id_str}</semantic> Generate: {word_list}",
                    ]
                else:
                    # Standard templates
                    templates = [
                        f"Generate {id_str} words: {word_list}",
                        f"Create {id_str}: {word_list}",
                        f"Words like {id_str}: {word_list}",
                    ]

                for template in templates:
                    examples.append(
                        {
                            "input": template.split(":")[0] + ":",  # Prompt part
                            "output": word_list,  # Expected output
                        },
                    )

        # Add wildcard examples for flexibility
        wildcard_examples = [
            "Generate [0,*,*,*] words: classical, elegant, timeless, noble",
            "Create [*,0,*,*]: beautiful, lovely, gorgeous, stunning",
            "Words like [*,*,0,*]: shakespearean, elizabethan, archaic",
            "Find [1,1,*,*] vocabulary: modern, simple, clear, direct",
        ]

        for example in wildcard_examples:
            examples.append({"input": example, "output": example})

        return examples
