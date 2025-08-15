# Etymology: {{ word }}

{% for provider in provider_data %}
**{{ provider.name }}**: {{ provider.etymology_text }}
{% endfor %}

Generate scholarly etymology with:
- Text: Word's journey from origin to present (2-3 sentences)
- Origin Language: Ultimate source
- Root Words: Key etymological components 
- First Known Use: Year or century

Note false etymologies when relevant. Prefer earliest documented origins.

## Examples

### `sincere`
Sources: [Latin sincerus "pure", uncertain origin, false "sine cera"]
**Text**: From Latin 'sincerus' (pure, genuine), c. 1530s. Ultimate origin uncertain; possibly Proto-Indo-European *sm-kēros "of one growth." Folk etymology "sine cera" (without wax) is spurious.
**Origin**: Latin
**Roots**: ['sincerus', '*sm-kēros']
**First Use**: 1533

### `algebra`
Sources: [Arabic al-jabr "restoration", via Medieval Latin]
**Text**: From Arabic 'al-jabr' (restoration of broken parts), via al-Khwarizmi's 9th-century treatise. Entered English through Medieval Latin, 15th century.
**Origin**: Arabic
**Roots**: ['al-jabr', 'jabara']
**First Use**: 1551