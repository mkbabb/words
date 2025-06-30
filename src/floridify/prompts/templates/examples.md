# Example Sentence Generation Prompt

## System Message

You are a creative writing assistant generating modern example sentences.

## User Prompt Template

Generate {{num_examples}} modern, contextual example sentences for the word "{{word}}" used as a {{word_type}}.

**Definition:** {{definition}}

## Requirements

-   Use contemporary language and scenarios
-   Make the sentences interesting and memorable
-   Ensure the word is used correctly according to the definition
-   Keep sentences between 10-20 words
-   Make examples diverse in context
-   Use varied sentence structures

## Output Format

Format as a simple numbered list:

1. [sentence]
2. [sentence]

### Example

1. The serene lake reflected the mountain peaks perfectly.
2. We decided to lake our afternoon by the peaceful shoreline.

## Variables

-   `{{word}}` - The word to use in examples
-   `{{word_type}}` - Part of speech (noun, verb, etc.)
-   `{{definition}}` - The definition to create examples for
-   `{{num_examples}}` - Number of examples to generate (default: 2)
