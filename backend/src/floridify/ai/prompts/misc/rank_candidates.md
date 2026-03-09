# Rank Candidates: {{ task }}

## Candidates
{% for candidate in candidates %}
### Candidate {{ loop.index0 }}
{{ candidate.model_dump_json(indent=2) }}
{% endfor %}

## Task
Rank these {{ candidates | length }} candidates for **{{ task }}** quality.

{% if word %}
Context: This is for the word "{{ word }}".
{% endif %}

## Scoring Criteria (0-10 scale)
- **Accuracy** (3 points): Factual correctness, no hallucinated content
- **Completeness** (3 points): Covers all relevant senses/aspects
- **Clarity** (2 points): Clear, natural phrasing
- **Distinctiveness** (2 points): Avoids redundancy between definitions

## Rules
- Score each candidate independently on the 0-10 scale
- Provide brief reasoning (max 15 words) for each score
- Rankings must cover every candidate index (0 to {{ candidates | length - 1 }})
