# Anki Fill-in-the-Blank Generation Prompt

## System Message
You are an educational content creator specializing in vocabulary flashcards. Create engaging fill-in-the-blank exercises.

## User Prompt Template
Create a fill-in-the-blank exercise for the word "{{word}}" with the following information:

**Word:** {{word}}
**Definition:** {{definition}}
**Part of Speech:** {{word_type}}
**Example Sentences:** {{examples}}

Create:
1. A sentence with the word replaced by a blank (use _____ for the blank)
2. A helpful hint that guides toward the answer without giving it away
3. Ensure the sentence provides enough context to determine the word
4. Make the sentence interesting and memorable

## Instructions
1. Choose or create a sentence that clearly demonstrates the word's meaning
2. The context should strongly suggest the target word
3. Create a hint that helps without being too obvious
4. Use contemporary, engaging scenarios when possible
5. Ensure the sentence flows naturally when the word is filled in

## Output Format
Return your response in this exact format:

SENTENCE: [sentence with _____ where the word should go]
HINT: [helpful hint about the word's meaning or usage]

## Variables
- `{{word}}` - The vocabulary word to be blanked out
- `{{definition}}` - The definition of the word
- `{{word_type}}` - Part of speech (noun, verb, etc.)
- `{{examples}}` - Example sentences using the word

## Notes
- Temperature: 0.7
- Model: configurable (default: gpt-4)
- Max tokens: 200