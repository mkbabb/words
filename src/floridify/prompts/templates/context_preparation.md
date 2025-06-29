# Context Preparation Template

## Template for Provider Context

Word: {{word}}

{{#providers}}
{{provider_name}} DEFINITIONS:
{{#definitions}}
{{index}}. [{{word_type}}] {{definition}}
{{#examples}}
   Examples:
{{#example_list}}
   - {{sentence}}
{{/example_list}}
{{/examples}}
{{/definitions}}

{{/providers}}

## Variables
- `{{word}}` - The word being defined
- `{{providers}}` - Array of provider data
  - `{{provider_name}}` - Name of the provider (WIKTIONARY, OXFORD, etc.)
  - `{{definitions}}` - Array of definitions from this provider
    - `{{index}}` - Definition number (1, 2, 3...)
    - `{{word_type}}` - Part of speech
    - `{{definition}}` - The definition text
    - `{{examples}}` - Optional examples section
      - `{{example_list}}` - Array of example sentences
        - `{{sentence}}` - Individual example sentence

## Notes
- This template is used to format provider data before sending to AI
- Limited to 2 examples per definition to keep context manageable
- Provider names are automatically uppercased