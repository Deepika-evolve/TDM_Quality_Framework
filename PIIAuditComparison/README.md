# PII Audit Drift Detection Tool

Detects schema drift across Database, Schema, Table, and Column levels, flags PII impact, and generates Excel and HTML reports.

> Part of the **TDM Quality Framework** — Open Source

---

## Overview

- A Python-based tool to automate PII audit drift detection between releases.
- Built to solve a real problem: manual PII audit comparison done every release cycle, which was time-consuming and error-prone.

---

## What We Detect

| Change Type | Severity | IsPII | Action |
|---|---|---|---|
| New Column Added | HIGH | Yes | Add to masking scope immediately |
| New Column Added | LOW | No | Review required |
| Column Dropped | HIGH | Yes | Verify removal — update masking scope |
| Column Dropped | LOW | No | Review required |
| Datatype Changed | HIGH | Yes | Review datatype impact on masking |
| Datatype Changed | MEDIUM | No | Review required |
| New Table Added | HIGH | Yes | Scan all columns — add PII to masking scope |
| New Table Added | MEDIUM | No | Scan all columns — review required |
| Table Dropped | HIGH | Yes | Verify removal — deactivate masking routines |
| Table Dropped | MEDIUM | No | Verify removal — deactivate masking routines |
| New Schema Added | HIGH | Yes | PII analysis required — raise change request |
| Schema Dropped | HIGH | Yes | Verify removal — deactivate masking routines |
| New Database Added | HIGH | Unknown | Scan entire database — PII analysis required |
| Database Dropped | HIGH | Yes | Verify removal — deactivate all masking routines |

---

## Features

- Multi-connection support — compare multiple connection profiles in one run
- PII bubble-up logic — if any column has PII, entire table/schema flagged HIGH
- Data quality checks — strip whitespace, normalise IsPII values, deduplicate
- Fuzzy header detection — auto-detects column headers (Database/DB/DatabaseName etc.)
- Simple UI — no Python knowledge needed
- Handles messy audit data — whitespace, mixed case, duplicates
- Excel report — highlighted by change type, Drift Summary, Critical Changes
- HTML report — consolidated metrics, bar charts, critical changes grid
- Logging — per-run log file with timestamps
- CI/CD ready — exit codes for pipeline integration

---

## How It Works

The tool follows a pipeline-based processing approach:

```
┌─────────────────┐     ┌─────────────────┐
│  Previous Audit │     │  Current Audit  │
│     File        │     │     File        │
└────────┬────────┘     └────────┬────────┘
         └──────────┬────────────┘
                    ▼
          ┌─────────────────┐
          │  Validate Files │  ← error_handler.py
          └────────┬────────┘
                    ▼
          ┌─────────────────┐
          │   Clean Data    │  ← data_quality.py
          └────────┬────────┘
                    ▼
          ┌─────────────────┐
          │    Compare      │  ← compare.py
          └────────┬────────┘
                    ▼
          ┌─────────────────┐
          │ Generate Reports│  ← report_excel.py
          │  Excel + HTML   │     report_html.py
          └─────────────────┘
```

---

## Architecture

```
PIIAuditComparison/
├── OrchestrationEngine/
│   ├── main.py          ← Command line / CI/CD
│   └── app.py           ← tkinter UI
├── ComparisonEngine/
│   ├── compare.py       ← Core comparison logic
│   ├── config.py        ← User configuration
│   ├── metrics.py       ← Drift metrics calculation
│   └── models.py        ← Result model
├── QualityEngine/
│   ├── data_quality.py  ← Strip, normalise, dedup, header detection
│   ├── error_handler.py ← File validation
│   └── utils.py         ← Shared logger
├── OutputEngine/
│   ├── report_excel.py  ← Excel report generation
│   └── report_html.py   ← HTML report generation
├── audit_files/         ← Place audit files here
└── output/              ← Generated reports saved here
```

---

## Design Principles

- **Separation of Concerns** — each engine has one responsibility
- **Fail Fast Validation** — all validations upfront in error_handler.py
- **Single Responsibility** — one file, one job
- **Pipeline Processing** — Validate → Clean → Compare → Generate Reports
- **Configurable** — config.py exposes all user-configurable values

---

## Prerequisites

```bash
pip install pandas openpyxl numpy
```

---

## Installation

```bash
git clone https://github.com/Deepika-evolve/TDM_Quality_Framework.git
cd TDM_Quality_Framework/PIIAuditComparison
```

---

## Audit File Format

Each sheet = one connection profile

| Database | Schema | Tables | Columns | Datatype | IsPII |
|---|---|---|---|---|---|
| CRM_DB | dbo | Customer | Email | VARCHAR | Yes |
| CRM_DB | dbo | Customer | CustomerID | INT | No |

---

## How to Run

### Option 1 — UI (Recommended)

```bash
python OrchestrationEngine/app.py
```

- Browse Previous Audit file
- Browse Current Audit file
- Click **Run Drift Detection**
- Open Output Folder when done

### Option 2 — Command Line

```bash
python OrchestrationEngine/main.py
```

---

## Output Files

| File | Description |
|---|---|
| `PII_Audit_Drift_Detection_<timestamp>.xlsx` | Full Excel report with drift details |
| `PII_Audit_Drift_Detection_<timestamp>.html` | HTML summary report |
| `drift_detection_<timestamp>.log` | Execution log |

---

## CI/CD Integration

| Exit Code | Meaning | CI/CD Behaviour |
|---|---|---|
| 0 | No drift detected | Pipeline continues ✅ |
| 1 | Drift detected | Pipeline stops — manual review required ⚠️ |
| 2 | Tool error | Pipeline stops — fix the tool ❌ |
| 3 | Partial run | Rerun required — some sheets had errors |

### Azure DevOps
```yaml
- script: python PIIAuditComparison/OrchestrationEngine/main.py
  displayName: 'PII Audit Drift Detection'
```

### GitHub Actions
```yaml
- name: PII Audit Drift Detection
  run: python PIIAuditComparison/OrchestrationEngine/main.py
```

---

## Notes

### Datatype Changes
Datatype transition changes are shown in the Critical Changes sheet in the Excel report only. This is by design.

### Dropped Schema — PII Count
When a schema is dropped, the count of PII columns under that schema is reflected in the Drift Summary metrics. This is expected behaviour.

### Performance
Execution time increases with the number of sheets/connections. Recommended: maximum 10-15 connections per audit file for optimal performance.

### Known Limitations
- Unknown/null IsPII values treated as LOW severity — Phase 3 fix planned
- Null values in Database/Schema/Table/Column may cause incorrect drift detection — ensure clean audit files
- Null column headers — sheet skipped gracefully — error logged

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Complete | Core detection — Excel + HTML reports |
| Phase 1.5 | ✅ Complete | QualityEngine + UI + Logging + Exit codes |
| Phase 2 | 🔜 Current | GitHub release + LinkedIn |
| Phase 3 | 📋 Planned | UI enhancements + PII Classification changes + Unknown IsPII handling + Code Refactoring |
| Phase 3.5 | 📋 Planned | Performance Optimization |
| Phase 4 | 📋 Planned | EXE packaging + FastAPI |
| Phase 5 | 📋 Planned | PII Classifier JSON + Masking suggestions by Column Name and Datatype |

---

## Author

**Deepika Mothilal**  
Senior TDM Consultant | SQL Developer | Python Enthusiast | 11+ years of experience  
GitHub: [deepika-evolve](https://github.com/Deepika-evolve)

---

*Built to solve a real problem. Work in progress — unit testing underway.*
