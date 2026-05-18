Table of Contents
- [Overview](#overview)
- [Why This Tool](#why-this-tool)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [How to Use — Step by Step](#how-to-use)
- [Source Adapters](#source-adapters)
- [PII Classification Engine](#pii-classification-engine)
- [Governance Engine](#governance-engine)
- [Masking Engine](#masking-engine)
- [Validation Report](#validation-report)
- [Supported JSON Formats](#supported-json-formats)
- [Configuration Reference](#configuration-reference)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Author](#Author)
- [License](#License)


## Overview

TDM Quality Framework — JSONMasking is a open source tool for masking
JSON data with built-in governance, audit trail, and validation.
The vision of this framework is true source agnosticism — 
decoupling PII governance and masking logic from data sources 
so that any input system can plug in without re-engineering the core pipeline.

**What it does**
- Detects PII fields in any JSON structure automatically
- Requires explicit human approval before masking — no silent defaults
- Applies realistic, format-preserving masking functions
- Generates a before/after validation report after every run
- Learns from user decisions — fewer fields to review each run
- Generates Scrambled output files preserving the format

**Input formats supported**
Excel files, JSON files, JSONL files, TXT files containing JSON strings

**Output**
scrabled JSON files + Consolidated validation report + validation report per input file

## Why This Tool

This tool—JSONMasking—was built from real challenges in enterprise TDM projects and reflects a broader vision for source-agnostic, accountable data masking.

Most enterprise masking tools focus on automating the masking process, but the quality of masking itself is often inconsistent. They lack strong PII analysis, provide limited transparency, and are difficult to validate or audit. As a result, organizations are left without clarity on what sensitive data was actually identified and how effectively it was masked.

In addition, classification in existing tools is typically static and not adaptable to project-specific contexts, leading to inconsistent outcomes across domains and datasets.

In one such enterprise implementation, the need for a PII audit trail after masking exposed a critical gap—existing solutions could not provide traceability or validation of masked data. Combined with weak PII detection and lack of transparency, this highlighted the need for a more accountable and adaptable approach.

JSONMasking is built to address this gap. It introduces structured PII analysis, end-to-end auditability, and a project-based classifier that adapts to each use case and continuously improves through a self-learning mechanism.

This is the foundation of a broader vision: source-agnostic, transparent, and governance-first data masking.

**Key design principles**
- Governance first — no masking without approval
- Honest documentation — limitations are documented with workarounds
- Source agnostic — Excel files with json strings, JSON files, JSONL files, TXT files containing JSON strings supported and API tomorrow
- Self-learning — decisions saved per project, reused in future runs

Architecture
## Architecture

<img width="270" height="300" alt="image" src="https://github.com/user-attachments/assets/66b5a2af-eee4-43d4-8f1f-1bc389298420" />


Five engines, one pipeline:

Input → PIIAnalysisEngine → audit sheet
              ↓
   [User reviews and approves]
              ↓
      GovernanceEngine → hash_audit
              ↓
      MaskingEngine → scrambled output
              ↓
  ValidationReport → masking_validation_report

**OrchestrationEngine** — coordinates the pipeline
  adapters.py       — ExcelAdapter, FilesystemAdapter (Acts as convergence point and makes the tool source agnostic)
  source_loader.py  — picks correct adapter
  output_writer.py  — routes output per source file

**PIIAnalysisEngine** — JSON traversal, PII detection
  pii_analyser.py   — recursive traversal, classifier matching

**GovernanceEngine** — approval and audit
  governance.py     — validation, hash generation, save decisions

**MaskingEngine** — masking and validation
  json_masker.py          — all masking functions
  post_masking_validation — before/after report

**QualityEngine** — shared utilities
  data_quality.py   — normalise, validate, pattern checks

**pii_classifier/**
  standard.json     — GDPR based — 18+ groups — read only
  exclusion_list.json
  projects/         — one classifier per project

Getting Started
## Getting Started

**Prerequisites**
- Python 3.10+
- pip install -r requirements.txt

**Installation**
git clone https://github.com/Deepika-evolve/TDM_Quality_Framework
cd TDM_Quality_Framework
pip install -r requirements.txt

**Configure**
Edit jm_config.py — set PROJECT_NAME, file paths
Edit project_config.py — set SOURCE_MODE, input folder, max files

**Run**
python main.py
PII Classification Engine
## PII Classification Engine

### Standard classifier — GDPR based — ships with tool — read only

18+ field groups covering:
name_group, email_group, phone_group, dob_group, address_group
city_group, country_group, postal_group, national_id_group
passport_group, aadhaar_group, pan_group, driverlicense_group
financial_group, salary_group, ip_group, url_group
social_identity_group, medical_group, biometric_group

Users cannot modify standard.json. It is protected at startup.

### Project classifier — per project — user managed

Stored in pii_classifier/projects/<PROJECT_ID>_classifier.json
User decisions from the audit sheet are saved here automatically.
Decisions are scoped to the project — never affect other projects.

### Classification priority

Exclusion list → Project not-PII → Project PII → Global PII

Project decisions always override global defaults.

### Matching strategy

Step 1 — Exact match across all groups
Step 2 — Fuzzy match (contains) — only if no exact match found
Step 3 — Unknown — flagged as ? for user review

Note: Generic field names like 'code', 'id', 'type' may cause
fuzzy match conflicts. Use specific names in the project classifier.



How to Use — Step by Step
## How to Use

### Step 1 — Prepare input

Excel mode:
Place input_json.xlsx in inputfiles/
Each row should contain one JSON string in the json_data column

Filesystem mode:
Place .json, .jsonl, or .txt files in inputfiles/
The number of files processed per run is controlled by MAX_FILES_PER_RUN

### Step 2 — First run — PII Analysis

python main.py

Tool traverses all JSON documents and classifies every field.
pii_audit_sheet.xlsx is generated in auditfiles/

https://github.com/Deepika-evolve/TDM_Quality_Framework/blob/main/JSONMasking/outputfiles/auditfiles/pii_audit_sheet.xlsx 

Fields are classified as:
- Yes — detected as PII
- No — detected as not PII
- ?  — unknown — user must review 

### Step 3 — Review and approve

Open pii_audit_sheet.xlsx and for each field:

| Column     | What to fill                                    |
|------------|-------------------------------------------------|
| is_pii     | Yes or No                                       |
| scope      | project_pii or project_not_pii (to classify unknown pii or to override standard classification based on the project context)                 |
| reason     | Required if overriding the classification        |
| approved   | Yes or No                                       |
| approved_by| Approver name — holds the accountability for all the pii classification decisions.          |

All fields must be approved before masking can proceed.
No unknown ? fields allowed — tool will block with an error.

### Step 4 — Second run — Masking

python main.py

Tool validates approvals, generates a tamper-proof hash audit,
runs masking, and generates a validation report.

https://github.com/Deepika-evolve/TDM_Quality_Framework/tree/main/JSONMasking/outputfiles/validationfiles
https://github.com/Deepika-evolve/TDM_Quality_Framework/tree/main/JSONMasking/outputfiles/scrambledfiles

Output files:
- scrambledfiles/ — masked JSON output
- validationfiles/ — masking validation report

### Subsequent runs

Fields classified in previous runs are auto-classified.
Only new or changed fields need review.
The audit trail grows with each project run.

Source Adapters
## Source Adapters

The tool is source agnostic. Set SOURCE_MODE in jm_config.py.

### Excel Adapter (SOURCE_MODE = 'excel')

- Reads JSON strings from input_json.xlsx
- One JSON document per row
- Input change detected by hashing file content
- Single scrambled Excel output file
- Single validation report

### Filesystem Adapter (SOURCE_MODE = 'filesystem')

- Reads .json, .jsonl, .txt files from inputfiles/
- Supports up to MAX_FILES_PER_RUN files per run
- Input change detected by hashing all file contents
- Separate scrambled output per input file
  employee_data.json → scrambled_employee_data_timestamp.json
  order_data.jsonl  → scrambled_order_data_timestamp.jsonl
- Separate validation report per input file

**Adding future adapters**
Add a new class to adapters.py
Add the mode to source_loader.py
No other changes needed

Governance Engine
## Governance Engine

### Approval validation — 7 checks

Before generating the hash audit, the tool checks:
1. Container fields skipped — only leaf values classified
2. Global scope blocked — only project_pii or project_not_pii allowed
3. All fields approved — no unapproved fields allowed
4. Overrides have reason — any classification change needs justification
5. Approver name required — regex validated — must be a real name
6. No unresolved ? fields — all unknowns must be resolved
7. Known PII cannot go to global exclusion list

### Tamper-proof hash audit

After validation:
- A hash of the approved audit is generated using MD5
- Hash is stored in tool_internals/audit_hash.txt
- Before masking — hash is recomputed and compared
- Any modification to the hash_audit blocks the masking run

<img width="600" height="212" alt="image" src="https://github.com/user-attachments/assets/39ae67e7-2471-43ac-a3ef-7a9924c96a7c" />


### Input change detection

- Excel mode — hashes input_json.xlsx content
- Filesystem mode — hashes all file contents in inputfiles/
- If input changes after approval — audit is cleared automatically
- User must re-review and approve the new data

### Self-learning classifier

After masking:
- project_pii decisions saved to project classifier
- project_not_pii decisions saved to project classifier
- Next run — these fields auto-classified — no manual review needed
- Bidirectional — decisions can be moved between pii and not_pii

Masking Engine
## Masking Engine

### Masking functions

All masking is deterministic — Faker.seed(42) ensures same input
always produces the same masked output across runs.

| Function          | Description                            | Example                         |
|-------------------|----------------------------------------|---------------------------------|
| mask_name         | Names — format preserving              | Deepika Mothilal → Bhavika Gole |
| mask_email        | Email — domain preserved, format aware | deepika.m@co.com → bhavika.k@co.com |
| mask_phone        | Phone — first 2 digits retained        | 9876543210 → 9819933867         |
| mask_dob          | Date — format preserved, shifted       | 1985-05-15 → 1985-08-31         |
| mask_address      | Street — number preserved              | 123 Main St → 123 Krishnan Rd  |
| mask_city         | City name or IATA code                 | BLR → XQK, Bangalore → Amravati|
| mask_country      | Country name or ISO code               | IN → ZA, India → Brazil         |
| mask_ip           | IPv4 and IPv6                          | 192.168.1.1 → 148.175.168.212  |
| mask_url          | URLs and URIs                          | https://real.com → masked URL   |
| mask_handle       | Social media handles                   | @sid_sharma → @bhavika          |
| mask_number       | Numbers — first digit retained         | 12345 → 19832                   |
| mask_alphanumeric | Mixed — letters and digits             | EMP001 → EMP089                 |
| mask_postal       | Postal codes — all formats             | SW1A 2AA → Xb9K 4qR            |
| mask_partial      | Partial — show last N characters       | 999-00-1234 → XXX-XX-1234       |
| mask_generic      | Fallback — full redaction              | any value → ***REDACTED***      |

### Pattern validation

Before masking, each function validates the input pattern:
- Email must have at least one letter in local part and a valid domain
- Phone must contain only digits, spaces, hyphens, or +
- Name must contain at least one letter
- City and country must not contain digits
- Address must contain at least one letter
- Postal code must contain at least one digit
- IP must match valid IPv4 or IPv6 format

Invalid inputs are returned as-is and flagged as
'Invalid Input Data' in the validation report.

Validation Report
## Validation Report

https://github.com/Deepika-evolve/TDM_Quality_Framework/tree/main/JSONMasking/outputfiles/validationfiles

Generated after every masking run in validationfiles/

### Summary sheet

| Column              | Description                              |
|---------------------|------------------------------------------|
| Total PII Fields    | All approved PII fields processed        |
| Validated           | Fields where masking was expected        |
| Skipped (empty)     | Fields with null or empty values         |
| Invalid Input Data  | Fields where input did not match pattern |
| Masking Pass        | Fields correctly masked                  |
| Masking Fail        | Fields that should have been masked      |
| Masking Pass Rate % | Pass / Validated                         |
| Type Match Pass     | Fields where type was preserved          |
| Type Match Fail     | Fields where type changed after masking  |

### Details sheet

Columns: doc_id, path, key, original_value (partial masked),
masked_value, original_type, masked_type, type_status,
mask_status, is_pii, approved, approved_by, mask_function,suorce_file

Supported JSON Formats
## Supported JSON Formats

Tested across 21 different JSON structures:

| Format                              | Status |
|-------------------------------------|--------|
| Flat JSON                           | ✅     |
| Nested JSON (11+ levels deep)       | ✅     |
| Root level arrays                   | ✅     |
| SAP OData (d.results wrapper)       | ✅     |
| JSON:API (attributes, relationships)| ✅     |
| GraphQL response (edges, node)      | ✅     |
| Salesforce format                   | ✅     |
| MongoDB document                    | ✅     |
| Arrays of primitives                | ✅     |
| Mixed type arrays                   | ✅     |
| JSONL — newline delimited           | ✅     |

Configuration Reference
## Configuration Reference

### jm_config.py — tool level settings

| Setting              | Description                        |
|----------------------|------------------------------------|
| PROJECT_NAME         | Name of the project                |
| INPUT_DIR            | Input files folder                 |
| AUDIT_DIR            | Audit sheet output folder          |
| SCRAMBLED_DIR        | Scrambled output folder            |
| VALIDATION_DIR       | Validation report folder           |
| LOG_DIR              | Log files folder                   |
| RESTART_ANALYSIS     | True to force fresh analysis       |
| PARTIAL_MASK_IN_AUDIT| Show partial masked values in audit|
| SOURCE_MODE          | 'excel' or 'filesystem'            |
| INPUT_FILE           | Excel input file path              |
| INPUT_FOLDER         | Filesystem input folder            |
| MAX_FILES_PER_RUN    | Max files per run (filesystem mode)|
| STANDARD_CLASSIFIER  | Path to standard.json              |
| PROJECT_CLASSIFIER   | Path to project classifier         |
| EXCLUSION_LIST       | Path to exclusion_list.json        |

### project_config.py — project level settings

| Setting              | Description                        |
|----------------------|------------------------------------|
| PROJECT_ID           | Unique project identifier generated from projectname |


Known Limitations
## Known Limitations

These are documented design boundaries of Phase 1.0,
not bugs. Workarounds are provided where possible.

| Limitation                  | Workaround              | Fix Phase |
|-----------------------------|-------------------------|-----------|
| Context-aware masking       | User reviews context    | 1.5       |
| System IDs not masked by default      | Mark scope as project_pii and give the reason in reason filed in pii_audit_sheet    | 1.5       |
| URL embedded IDs            | URL replaced with dummy | 3       |
| Generic field names (code)  | Use specific names      | 1.5       |
| Compound field values       | Use mask_generic function      | 3       |
| Function selection in audit | Re-classify in project  | 1.5       |
| Name-email correlation      | Works for full name     | 1.5       |

Roadmap
## Roadmap

**Phase 1.5**
- Tkinter UI with bulk approval
- Path-based classifier
- Inflight API masking
- MongoDB adapter
- Context-aware masking

**Phase 2**
- PostgreSQL backend
- Multi-user support
- Multiple projects support
- ID mapping table with collision avoidance
- Cross-system referential integrity templates

**Phase 3**
- Presidio NLP inference engine
- URL embedded ID masking
- Compound field masking

---

## Author

**Deepika Mothilal**  
Senior TDM Consultant | SQL Developer | Python Enthusiast | 11+ years of experience  
GitHub: [deepika-evolve](https://github.com/Deepika-evolve)

---
## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

*Built to solve a real TDM problem. Work in progress*


