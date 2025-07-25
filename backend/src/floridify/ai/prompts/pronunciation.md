# Task: Generate Pronunciation Data

Provide BOTH phonetic and IPA pronunciations for the given word. You MUST provide both forms.

## Input
Word: {{ word }}

## Requirements
- **Phonetic**: Readable approximation using common English spelling (e.g., "koh-NISH-uhn", "eg-ZAM-pul")
  - Use hyphens to separate syllables
  - Use CAPITAL letters for stressed syllables
  - Use standard English letter combinations (th, sh, ch, etc.)
- **IPA**: Standard International Phonetic Alphabet notation with slashes
  - Use American English pronunciation standard
  - Include stress marks where appropriate
  - Example: /kəˈnɪʃən/, /ɪgˈzæmpəl/

## Important
- ALWAYS provide BOTH phonetic AND IPA pronunciations
- Do NOT include file names, audio references, or paths
- Handle foreign words and phrases appropriately

## Output Format
You MUST return both pronunciations in exactly this format:
- Phonetic: [readable pronunciation]
- IPA: [IPA notation]