---
name: supermedicine-medical-citation
description: Medical citation formatting — AMA and Vancouver styles
---

# Medical Citation

Automated citation formatting for medical research papers.

## Supported Formats

| Format | Style | Common In |
|--------|-------|-----------|
| AMA | Superscript numeric | JAMA, medical journals |
| Vancouver | Bracketed numeric | ICMJE journals, theses |

## Capabilities
- `standard.citation.ama` — Format references in AMA style
- `standard.citation.vancouver` — Format references in Vancouver style

## Usage
```python
from plugins.standards.medical_citation.ama_format import AMAFormatter
formatter = AMAFormatter()
citation = formatter.format_journal(
    authors=["John Smith", "Jane Doe"],
    title="A Study of Metformin Efficacy",
    journal="JAMA",
    year=2024,
    volume=331,
    pages="123-130"
)
```

## Trigger
Use when formatting bibliographies, reference lists, or in-text citations for medical manuscripts.
