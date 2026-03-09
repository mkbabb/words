# Pronunciation: {{ word }}

{% if language and language != "en" %}
Language: {{ language_name }}
{% else %}
Language: American English
{% endif %}

## Task

Generate accurate pronunciation data for this word.

### Requirements
{% if language and language != "en" %}
- **Phonetic**: Hyphenated syllables using English-approximation letters. CAPS for primary stress.
- **IPA**: Standard {{ language_name }} IPA. Mark primary stress with /ˈ/ and secondary stress with /ˌ/.
{% else %}
- **Phonetic**: Hyphenated syllables using English letters. CAPS for primary stress.
- **IPA**: Standard American English IPA. Mark primary stress with /ˈ/ and secondary stress with /ˌ/.
{% endif %}

### Rules
- If multiple standard pronunciations exist, include variants separated by "or".
- For loanwords in English, give the anglicized pronunciation unless the word is typically pronounced in its source language.
- Ensure syllable breaks in the phonetic form align with the IPA syllabification.

## Examples

{% if language == "fr" %}
`bonjour`: **Phonetic**: bohn-ZHOOR | **IPA**: /bɔ̃.ʒuʁ/
`en coulisse`: **Phonetic**: ahn koo-LEES | **IPA**: /ɑ̃ ku.lis/
{% elif language == "es" %}
`hola`: **Phonetic**: OH-lah | **IPA**: /ˈo.la/
`desarrollo`: **Phonetic**: deh-sah-RROH-yoh | **IPA**: /de.sa.ˈro.ʝo/
{% elif language == "de" %}
`Schadenfreude`: **Phonetic**: SHAH-den-froy-deh | **IPA**: /ˈʃaːdn̩ˌfʁɔʏdə/
`Gemütlichkeit`: **Phonetic**: geh-MUET-likh-kite | **IPA**: /ɡəˈmyːtlɪçkaɪt/
{% elif language == "it" %}
`grazie`: **Phonetic**: GRAH-tsee-eh | **IPA**: /ˈɡrat.tsje/
`cappuccino`: **Phonetic**: kah-poo-CHEE-noh | **IPA**: /kap.putˈtʃiː.no/
{% else %}
`either`: **Phonetic**: EE-thur or EYE-thur | **IPA**: /ˈiːðər/ or /ˈaɪðər/
`croissant`: **Phonetic**: kruh-SAHNT | **IPA**: /krəˈsɑːnt/
`controversy`: **Phonetic**: KAHN-truh-vur-see | **IPA**: /ˈkɑntrəvɜrsi/
{% endif %}