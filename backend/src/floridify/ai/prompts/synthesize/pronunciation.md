# Pronunciation: {{ word }}

{% if language and language != "en" %}
Generate native {{ language_name }} pronunciation:
{% else %}
Generate American English pronunciation:
{% endif %}

**Phonetic**: Hyphenated syllables, CAPS for primary stress
{% if language and language != "en" %}
**IPA**: Standard {{ language_name }} IPA with /ˈ/ for stress
{% else %}
**IPA**: Standard American with /ˈ/ for stress
{% endif %}

Include variants with "or" if multiple are standard.

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
