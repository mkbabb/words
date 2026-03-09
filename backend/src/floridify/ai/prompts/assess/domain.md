# Domain: {{ definition }}

## Valid Domains

medical, legal, computing, mathematics, physics, chemistry, biology, music, art, architecture, engineering, linguistics, philosophy, psychology, economics, business, sports, military, nautical, culinary

## Decision Rules

1. Return null if a non-specialist would understand and use this word/sense.
2. Return a domain only if the definition contains domain-specific meaning not transferable to general use.
3. Pick the most specific applicable domain (e.g., "chemistry" over "science").
4. Words used metaphorically outside their origin domain → null (e.g., "catalyst" meaning "cause of change" → null; "catalyst" meaning "substance that speeds a reaction" → chemistry).

## Anchors

| Definition snippet | Domain |
|-------------------|--------|
| inflammation of the bronchial tubes | medical |
| LIFO data structure | computing |
| binding legal precedent | legal |
| interval between two musical pitches | music |
| load-bearing structural member | engineering |
| a type of tree | null |
| very tired | null |
| complex situation | null |

Return domain or null.
