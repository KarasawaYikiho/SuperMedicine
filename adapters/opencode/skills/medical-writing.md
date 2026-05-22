---
name: supermedicine-medical-writing
description: Medical writing standards compliance checking — CONSORT, STROBE, PRISMA, STARD
---

# Medical Writing Standards

Compliance checking for major medical research reporting guidelines.

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
from plugins.standards.medical_writing.checklists import get_consort_checklist
checklist = get_consort_checklist()
result = checklist.check(manuscript_text)
print(f"Compliance: {result['compliance_rate']}%")
```

## Trigger
Use when writing, reviewing, or evaluating medical research manuscripts for reporting guideline compliance.
