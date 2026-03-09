# Regional Variants: {{ definition }}

## Region Codes
US, UK, AU, CA, IN, ZA, IE, NZ

## Decision Rules

1. Return [] (empty) if the word/sense is used universally across English varieties.
2. Return regions only where this specific sense is the **primary or standard** term.
3. Spelling alone does not determine region (the definition text, not spelling, is the input).
4. If a word is understood everywhere but primarily *used* in certain regions, list those regions.

## Anchors

| Sense | Regions | Why |
|-------|---------|-----|
| elevator (vertical transport) | [] | Universal |
| lift (vertical transport) | ["UK", "AU", "NZ", "ZA", "IE"] | Not standard in US/CA |
| fall (season) | ["US", "CA"] | UK/AU say "autumn" |
| boot (car storage) | ["UK", "AU", "NZ", "ZA", "IE"] | US/CA say "trunk" |
| biscuit (sweet baked snack) | ["UK", "AU", "NZ", "IN", "ZA", "IE"] | US "cookie" |
| diaper | ["US", "CA"] | UK "nappy" |
| queue (line of people) | ["UK", "AU", "NZ", "IN", "ZA", "IE"] | US prefers "line" |
| apartment | [] | Understood and used broadly |

Return region list or empty list.
