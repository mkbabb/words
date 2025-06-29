# Floridify Prompt Template System

The prompt template system allows for easy management and editing of AI prompts used throughout Floridify. Instead of hardcoding prompts in Python code, they are stored as markdown files that can be easily edited, versioned, and maintained.

## Directory Structure

```
src/floridify/prompts/
├── __init__.py              # Module exports
├── loader.py                # PromptLoader class
├── templates.py             # PromptTemplate class and parsing
├── formatters.py            # Context formatting utilities
├── README.md               # This documentation
└── templates/              # Markdown template files
    ├── synthesis.md        # Definition synthesis prompt
    ├── examples.md         # Example sentence generation
    └── context_preparation.md  # Context formatting template
```

## Template Format

Each template is a markdown file with specific sections:

```markdown
# Template Title

## System Message
The system message for the AI assistant.

## User Prompt Template
The user prompt with {{variable}} placeholders.

## Instructions
Detailed instructions for the AI (optional).

## Output Format
Expected output format specification (optional).

## Variables
- `{{variable_name}}` - Description of the variable

## Notes
- Temperature: 0.7
- Model: gpt-4
- Max tokens: auto
```

### Required Sections
- **System Message**: The role/persona for the AI
- **User Prompt Template**: The main prompt with variable placeholders

### Optional Sections
- **Instructions**: Additional guidance for the AI
- **Output Format**: How the response should be structured
- **Variables**: Documentation of template variables
- **Notes**: AI model configuration (temperature, model, max_tokens)

## Variable Substitution

Variables use `{{variable_name}}` syntax and are replaced when the template is rendered:

```python
template.render({"word": "serendipity", "word_type": "noun"})
```

## AI Configuration

The **Notes** section can specify AI model parameters:

- `Temperature: 0.7` - Controls randomness (0.0 = deterministic, 1.0 = very random)
- `Model: gpt-4` - Which AI model to use 
- `Max tokens: 500` - Maximum response length (use "auto" for unlimited)

These settings override the default configuration when making API calls.

## Usage Examples

### Loading and Using Templates

```python
from floridify.prompts import PromptLoader

# Initialize loader
loader = PromptLoader()

# Load a template
template = loader.load_template("synthesis")

# Render with variables
system_msg, user_prompt = template.render({
    "word": "serendipity",
    "context": "Provider definitions here..."
})

# Get AI settings
ai_settings = template.get_ai_settings()
# Returns: {"temperature": 0.3, "model": "configurable"}
```

### CLI Commands

```bash
# List all available templates
python -m floridify.cli prompts

# View specific template info
python -m floridify.cli prompts synthesis
```

## Creating New Templates

1. Create a new `.md` file in `templates/` directory
2. Follow the template format with required sections
3. Add any needed variables and AI configuration
4. Test the template by loading it with `PromptLoader`

### Example New Template

```markdown
# Word Pronunciation Prompt

## System Message
You are a phonetics expert providing accurate pronunciations.

## User Prompt Template
Provide the phonetic pronunciation for "{{word}}" in {{dialect}} English.

## Output Format
Return only the phonetic spelling using standard pronunciation guides.

## Variables
- `{{word}}` - The word to pronounce
- `{{dialect}}` - English dialect (American, British, etc.)

## Notes
- Temperature: 0.1
- Model: gpt-4
```

## Template Best Practices

1. **Clear Instructions**: Be specific about what you want the AI to do
2. **Consistent Format**: Use consistent variable naming and formatting
3. **Appropriate Temperature**: 
   - Low (0.1-0.3) for factual, consistent responses
   - Medium (0.4-0.6) for balanced creativity
   - High (0.7-1.0) for creative, varied responses
4. **Documentation**: Always document variables in the Variables section
5. **Testing**: Test templates with various inputs to ensure robustness

## Integration Points

The prompt system integrates with:

- **OpenAI Connector**: Uses templates for all AI API calls
- **Word Processing Pipeline**: Automatically loads and uses appropriate templates
- **CLI Interface**: Provides commands to inspect and test templates
- **Testing Framework**: Comprehensive tests for template loading and rendering

## Error Handling

The system provides graceful error handling:

- Missing template files raise `FileNotFoundError`
- Malformed templates raise `ValueError` with details
- Template cache can be cleared and reloaded for development
- Fallback to default AI settings if template config is invalid

## Performance Considerations

- Templates are cached after first load for performance
- Use `loader.reload_template()` during development to pick up changes
- `loader.clear_cache()` clears all cached templates
- Template parsing is fast but caching eliminates repeated file I/O

## Future Enhancements

Planned improvements to the prompt system:

1. **Template Versioning**: Track template versions and migrations
2. **A/B Testing**: Support for template variants and performance comparison
3. **Dynamic Variables**: Runtime variable generation and validation
4. **Template Inheritance**: Base templates with extension mechanisms
5. **Web Interface**: GUI for editing templates without touching files