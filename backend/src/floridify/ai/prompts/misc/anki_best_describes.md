# Best Describes: {{ word }} ({{ part_of_speech }})

**Definition**: {{ definition }}
{% if examples %}**Examples**: {{ examples }}{% endif %}

Create GRE-level question: "Which definition best describes '{{ word }}'?"

**Requirements**:
- NEVER include "{{ word }}" or its variants in choices
- One correct definition (paraphrased)
- Three plausible but incorrect distractors

Generate 4 choices (A-D) testing precise meaning. Specify correct letter.