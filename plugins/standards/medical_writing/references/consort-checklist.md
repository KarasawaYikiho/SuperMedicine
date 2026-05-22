# CONSORT 2010 Checklist

CONSORT (Consolidated Standards of Reporting Trials) 2010 — 随机对照试验报告规范。

## Checklist Items

| Section | Item No | Description | Reported |
|---------|---------|-------------|----------|
| Title and Abstract | 1a | Identification as a randomised trial in the title | |
| | 1b | Structured summary of trial design, methods, results, and conclusions | |
| Introduction | 2a | Scientific background and explanation of rationale | |
| | 2b | Specific objectives or hypotheses | |
| Methods: Trial Design | 3a | Description of trial design (such as parallel, factorial) including allocation ratio | |
| | 3b | Important changes to methods after trial commencement (such as eligibility criteria), with reasons | |
| Methods: Participants | 4a | Eligibility criteria for participants | |
| | 4b | Settings and locations where the data were collected | |
| Methods: Interventions | 5 | The interventions for each group with sufficient details to allow replication, including how and when they were actually administered | |
| Methods: Outcomes | 6a | Completely defined pre-specified primary and secondary outcome measures, including how and when they were assessed | |
| | 6b | Any changes to trial outcomes after the trial commenced, with reasons | |
| Methods: Sample Size | 7a | How sample size was determined | |
| | 7b | When applicable, explanation of any interim analyses and stopping guidelines | |
| Methods: Randomisation | 8a | Method used to generate the random allocation sequence | |
| | 8b | Type of randomisation; details of any restriction (such as blocking and block size) | |
| Methods: Allocation Concealment | 9 | Mechanism used to implement the random allocation sequence (such as sequentially numbered containers), describing any steps taken to conceal the sequence until interventions were assigned | |
| Methods: Implementation | 10 | Who generated the random allocation sequence, who enrolled participants, and who assigned participants to interventions | |
| Methods: Blinding | 11a | If done, who was blinded after assignment to interventions (for example, participants, care providers, those assessing outcomes) and how | |
| | 11b | If relevant, description of the similarity of interventions | |
| Methods: Statistical Methods | 12a | Statistical methods used to compare groups for primary and secondary outcomes | |
| | 12b | Methods for additional analyses, such as subgroup analyses and adjusted analyses | |
| Results: Participant Flow | 13a | For each group, the numbers of participants who were randomly assigned, received intended treatment, and were analysed for the primary outcome | |
| | 13b | For each group, losses and exclusions after randomisation, together with reasons | |
| Results: Recruitment | 14a | Dates defining the periods of recruitment and follow-up | |
| | 14b | Why the trial ended or was stopped | |
| Results: Baseline Data | 15 | A table showing baseline demographic and clinical characteristics for each group | |
| Results: Numbers Analysed | 16 | For each group, number of participants (denominator) included in each analysis and whether the analysis was by original assigned groups | |
| Results: Outcomes and Estimation | 17a | For each primary and secondary outcome, results for each group, and the estimated effect size and its precision (such as 95% confidence interval) | |
| | 17b | For binary outcomes, presentation of both absolute and relative effect sizes is recommended | |
| Results: Ancillary Analyses | 18 | Results of any other analyses performed, including subgroup analyses and adjusted analyses, distinguishing pre-specified from exploratory | |
| Results: Harms | 19 | All important harms or unintended effects in each group | |
| Discussion: Limitations | 20 | Trial limitations, addressing sources of potential bias, imprecision, and, if relevant, multiplicity of analyses | |
| Discussion: Generalisability | 21 | Generalisability (external validity, applicability) of the trial findings | |
| Discussion: Interpretation | 22 | Interpretation consistent with results, balancing benefits and harms, and considering other relevant evidence | |
| Other Information: Registration | 23 | Registration number and name of trial registry | |
| Other Information: Protocol | 24 | Where the full trial protocol can be accessed, if available | |
| Other Information: Funding | 25 | Sources of funding and other support (such as supply of drugs), role of funders | |

## Reference

Schulz KF, Altman DG, Moher D, for the CONSORT Group. CONSORT 2010 Statement: updated guidelines for reporting parallel group randomised trials. BMJ. 2010;340:c332.

## Usage

```python
from plugins.standards.medical_writing.checklists import get_consort_checklist
checklist = get_consort_checklist()
result = checklist.check(manuscript_text)
print(f"CONSORT compliance: {result['compliance_rate']}%")
print(f"Missing required items: {len(result['required_missing'])}")
```
