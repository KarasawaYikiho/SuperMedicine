---
name: supermedicine-medical-writing
description: Medical writing standards compliance checking — CONSORT, STROBE, PRISMA, STARD
---

# Medical Writing Standards

Compliance checking for major medical research reporting guidelines. This is a
drafting/reporting-quality review aid only; it is not clinical advice and requires
human expert review before research, regulatory, or clinical use.

This skill keeps reporting-standard boundaries local for optional OpenCode
consumption; the checklist reference files remain the source for detailed item
wording.

## Supported Standards

| Standard | Version | Items | Scope |
|----------|---------|-------|-------|
| CONSORT | 2010 | 23 | Randomized controlled trials |
| STROBE | 2007 | 22 | Observational studies |
| PRISMA | 2020 | 27 | Systematic reviews and meta-analyses |
| STARD | 2015 | 27 | Diagnostic accuracy studies |

## Capabilities
- `standard.consort` — Check RCT manuscripts against CONSORT checklist
- `standard.strobe` — Check observational study manuscripts against STROBE checklist
- `standard.prisma` — Check systematic review manuscripts against PRISMA checklist
- `standard.stard` — Check diagnostic accuracy manuscripts against STARD checklist

## Usage
```python
from plugins.standards.medical_writing.main import execute

result = execute(
    "standard.consort",
    {"text": manuscript_text},
)
print(f"Compliance: {result['output']['compliance_rate']}%")
```

## Trigger
Use when writing, reviewing, or evaluating medical research manuscripts for reporting guideline compliance.
