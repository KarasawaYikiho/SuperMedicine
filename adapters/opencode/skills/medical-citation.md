---
name: supermedicine-medical-citation
description: Medical citation formatting — AMA and Vancouver styles
---

# Medical Citation

Automated citation formatting for user-provided medical research source metadata.
Citation output is deterministic formatting only; citations are not generated when
the source is missing, unknown, or invalid, and all output requires human expert
review before research, regulatory, or clinical use.

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
from plugins.standards.medical_citation.ama_format import AMAFormatter, JournalArticle

formatter = AMAFormatter()
citation = formatter.format_journal(JournalArticle(
    authors=["John Smith", "Jane Doe"],
    title="A Study of Metformin Efficacy",
    journal="JAMA",
    year=2024,
    volume="331",
    pages="123-130"
))
```

Executable plugin API example:

```python
from plugins.standards.medical_citation.main import execute

result = execute(
    "standard.citation.ama",
    {
        "source_id": "src-1",
        "sources": {
            "src-1": {
                "reference_type": "journal",
                "authors": ["John Smith", "Jane Doe"],
                "title": "A Study of Metformin Efficacy",
                "journal": "JAMA",
                "year": 2024,
                "volume": "331",
                "pages": "123-130",
            }
        },
    },
)
citation = result["output"]["citation"]
```

## Trigger
Use when formatting bibliographies, reference lists, or in-text citations for medical manuscripts.
