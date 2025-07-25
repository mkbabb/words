# Pronunciation Data Issues Analysis - Floridify Codebase

## Summary

The pronunciation extraction in the Floridify codebase has several issues that result in:
1. **Phonetic field containing .ogg filenames** instead of phonetic text
2. **IPA fields being null** when they should contain pronunciation data
3. **Audio template arguments being misinterpreted** as phonetic pronunciations

## Root Causes

### 1. Wiktionary Audio Template Handling (Primary Issue)

In `/backend/src/floridify/connectors/wiktionary.py`, lines 504-510:

```python
elif template_name in ["pron", "pronunciation", "audio"]:
    for arg in template.arguments:
        arg_value = str(arg.value).strip()
        if arg_value and len(arg_value) > 2:
            if not phonetic:  # Don't override IPA-derived phonetic
                phonetic = arg_value
                break
```

**Problem**: When processing Wiktionary's audio templates (e.g., `{{audio|en|En-us-word.ogg|Audio (US)}}`), the code extracts the filename argument (`En-us-word.ogg`) and sets it as the phonetic pronunciation.

**Why it happens**: The code doesn't distinguish between different template arguments. In audio templates:
- arg[0] = language code (e.g., "en")
- arg[1] = audio filename (e.g., "En-us-word.ogg")
- arg[2] = display text (e.g., "Audio (US)")

The current logic takes any argument longer than 2 characters, which catches the filename.

### 2. IPA Template Processing Issues

The IPA extraction logic (lines 495-502) works correctly when IPA data is present:

```python
if "ipa" in template_name:
    for arg in template.arguments:
        if not arg.name:  # Positional argument
            arg_value = str(arg.value).strip()
            if "/" in arg_value or "[" in arg_value:
                ipa = arg_value
                phonetic = self._ipa_to_phonetic(ipa)
                break
```

However, the test output shows an error occurs during extraction, preventing IPA data from being captured.

### 3. IPA to Phonetic Conversion

The `_ipa_to_phonetic` method has limited coverage for IPA symbols. For example:
- `/ˈwɜːd/` converts to `wɜd` (missing substitution for `ɜ`)
- `/wɝd/` converts to `wɝd` (missing substitution for `ɝ`)

### 4. Exception Handling Suppresses Errors

Line 520 logs errors at DEBUG level only:
```python
except Exception as e:
    logger.debug(f"Error extracting pronunciation: {e}")
```

This makes it difficult to diagnose extraction failures in production.

## Synthesis Function Issues

In `/backend/src/floridify/ai/synthesis_functions.py`, the `synthesize_pronunciation` function:
1. First checks for existing pronunciation data from providers
2. Falls back to AI generation if none found
3. But if provider data contains invalid phonetic data (like .ogg filenames), it will use that instead of generating proper pronunciation

## AI Pronunciation Generation

The AI pronunciation generation uses a proper prompt template (`/backend/src/floridify/ai/prompts/pronunciation.md`) that requests:
- Phonetic: Readable approximation (e.g., "koh-NISH-uhn")
- IPA: Standard International Phonetic Alphabet notation

However, this fallback is only used when NO pronunciation data exists, not when invalid data is present.

## Recommendations

### 1. Fix Audio Template Handling
```python
elif template_name in ["pron", "pronunciation"]:
    # Handle pronunciation templates
    for arg in template.arguments:
        arg_value = str(arg.value).strip()
        if arg_value and len(arg_value) > 2:
            if not phonetic:
                phonetic = arg_value
                break
elif template_name == "audio":
    # Skip audio templates - they contain filenames, not pronunciations
    continue
```

### 2. Improve Argument Parsing
Instead of taking any argument, be more selective:
```python
elif template_name == "audio":
    # Audio templates: {{audio|lang|filename|description}}
    # We might extract description if useful, but skip filename
    if len(template.arguments) >= 3:
        description = str(template.arguments[2].value).strip()
        # Could store this as audio metadata
```

### 3. Enhance IPA Coverage
Add missing IPA substitutions to `_ipa_to_phonetic`:
```python
"ɜ": "er",  # As in "bird"
"ɝ": "er",  # R-colored schwa
"ɚ": "er",  # R-colored schwa (unstressed)
```

### 4. Add Validation
In `synthesize_pronunciation`, validate phonetic data:
```python
# Check if phonetic looks like a filename
if phonetic and ('.ogg' in phonetic or '.mp3' in phonetic):
    logger.warning(f"Invalid phonetic data (appears to be filename): {phonetic}")
    phonetic = None
```

### 5. Improve Error Handling
Change debug logging to warning/error level for extraction failures:
```python
except Exception as e:
    logger.warning(f"Error extracting pronunciation: {e}")
```

## Impact

This issue affects:
1. **Data Quality**: Users see filenames instead of pronunciations
2. **AI Synthesis**: Invalid data prevents proper AI fallback
3. **User Experience**: Pronunciation feature is essentially broken for Wiktionary-sourced words
4. **API Responses**: Frontend receives and displays incorrect pronunciation data

## Testing

The test script demonstrates:
1. Audio template is found but pronunciation extraction fails
2. IPA template is present but not processed due to early error
3. IPA to phonetic conversion needs improvement for certain symbols