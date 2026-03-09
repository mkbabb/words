# Etymology: {{ word }}

## Sources
{% for provider in provider_data %}
**{{ provider.name }}**: {{ provider.etymology_text }}
{% endfor %}

## Task

Synthesize a scholarly etymology from the provider data above.

### Reconciliation Rules
- When providers give different origin languages, prefer the earliest well-documented ancestor.
- When dates conflict, use the earliest attested date with a credible source.
- Flag folk etymologies explicitly (e.g., "sine cera" for "sincere").
- When one provider gives deeper historical roots than others, incorporate the full chain.

### Output Fields
- **Text**: 2-3 sentences tracing the word's journey from origin to modern usage. Include intermediate languages when relevant (e.g., Latin -> Old French -> Middle English).
- **Origin Language**: The ultimate source language (e.g., "Proto-Indo-European", "Arabic", "Latin").
- **Root Words**: Key etymological ancestors as a list. Include reconstructed forms with asterisk (e.g., *lewk-).
- **First Known Use**: Year if documented, otherwise century or period (e.g., "c. 1400", "15th century").

## Examples

### `sincere`
Sources: [Latin sincerus "pure", uncertain origin, false "sine cera"]
**Text**: From Latin 'sincerus' (pure, genuine), c. 1530s. Ultimate origin uncertain; possibly Proto-Indo-European *sm-keros "of one growth." Folk etymology "sine cera" (without wax) is spurious.
**Origin**: Latin
**Roots**: ['sincerus', '*sm-keros']
**First Use**: 1533

### `algebra`
Sources: [Arabic al-jabr "restoration", via Medieval Latin]
**Text**: From Arabic 'al-jabr' (restoration of broken parts), via al-Khwarizmi's 9th-century treatise. Entered English through Medieval Latin, 15th century.
**Origin**: Arabic
**Roots**: ['al-jabr', 'jabara']
**First Use**: 1551