# Anki Multiple Choice Generation Prompt

## System Message
You are an educational content creator specializing in vocabulary flashcards. Create challenging but fair multiple choice questions.

## User Prompt Template
Create a multiple choice question for the word "{{word}}" with the following definition:

**Definition:** {{definition}}
**Part of Speech:** {{word_type}}
**Examples:** {{examples}}

Generate 4 answer choices (A, B, C, D) where:
- One choice is the correct definition (closely match the provided definition)
- Three choices are plausible but incorrect distractors
- Distractors should be semantically related but clearly wrong
- All choices should be of similar length and complexity
- Use vocabulary appropriate for the word's difficulty level

## Instructions
1. Make the correct answer closely match the provided definition
2. Create distractors that are related to the word but clearly incorrect
3. Ensure distractors are believable and not obviously wrong
4. Match the style and complexity of the correct definition
5. Consider common misconceptions or similar words for distractors

## Output Format
Return your response in this exact format:

A) [first choice]
B) [second choice]  
C) [third choice]
D) [fourth choice]

CORRECT: [letter of correct answer]

## Variables
- `{{word}}` - The vocabulary word
- `{{definition}}` - The correct definition
- `{{word_type}}` - Part of speech (noun, verb, etc.)
- `{{examples}}` - Example sentences using the word

## Notes
- Temperature: 0.6
- Model: configurable (default: gpt-4)
- Max tokens: 300