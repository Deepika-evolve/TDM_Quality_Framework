import os
from datetime import datetime

# Base
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))

# Input
INPUT_DIR      = os.path.join(BASE_DIR, 'inputfiles')
INPUT_FILE     = os.path.join(INPUT_DIR, 'input_json.xlsx')

# Project — user sets name only
PROJECT_NAME = 'SAP HR Project'   # user fills this
PROJECT_ID   = ''                  # auto generated from name
# Project classifier — auto set by project_config.py
PROJECT_CLASSIFIER = ''
PROJECTS_DIR = os.path.join(BASE_DIR, 'pii_classifier', 'projects')

# Output
OUTPUT_DIR     = os.path.join(BASE_DIR, 'outputfiles')
AUDIT_DIR      = os.path.join(OUTPUT_DIR, 'auditfiles')
SCRAMBLED_DIR  = os.path.join(OUTPUT_DIR, 'scrambledfiles')
LOG_DIR        = os.path.join(OUTPUT_DIR, 'logs')
VALIDATION_DIR = os.path.join(OUTPUT_DIR, 'validationfiles')
TOOLINTERNALS_DIR = os.path.join(OUTPUT_DIR, 'toolinternals')

timestamp    = datetime.today().strftime('%Y%m%d_%H%M%S')
INPUT_HASH_FILE = os.path.join(TOOLINTERNALS_DIR, 'input_hash.txt')
AUDIT_FILE     = os.path.join(AUDIT_DIR,     'pii_audit_sheet.xlsx')
OUTPUT_FILE    = os.path.join(SCRAMBLED_DIR, f"scrambled_json_{timestamp}.xlsx")

HASH_AUDIT_FILE   = os.path.join(TOOLINTERNALS_DIR, 'hash_audit.xlsx')
AUDIT_ORIGINAL    = os.path.join(TOOLINTERNALS_DIR, 'pii_audit_original.xlsx')
AUDIT_HASH_TXT    = os.path.join(TOOLINTERNALS_DIR, 'audit_hash.txt')
AUDIT_ARCHIVE_DIR = os.path.join(TOOLINTERNALS_DIR, 'archive')
RESTART_ANALYSIS  = False  # True = clear and restart  the pii analysis from scratch

# Classifier
STANDARD_CLASSIFIER  = os.path.join(BASE_DIR, 'pii_classifier', 'standard.json')
EXCLUSION_LIST     = os.path.join(BASE_DIR, 'pii_classifier', 'exclusion_list.json')

# Masking validation report
MASKING_REPORT_FILE  = os.path.join(VALIDATION_DIR, f"masking_validation_report_{timestamp}.xlsx")


# Settings
JSON_COLUMN                 = 'json_data'
DELETE_SOURCE_AFTER_MASKING = False
MASKING_MODE                = 'review'  # review or auto
# PII protection in audit files
PARTIAL_MASK_IN_AUDIT = False   # True = partial mask value in audit sheet
                               # False = show full value (dev/trusted env only)
SOURCE_MODE = 'filesystem'  # 'excel' or 'filesystem'
INPUT_FOLDER = 'inputfiles/'  # filesystem mode — all file types here
MAX_FILES_PER_RUN = 10  # filesystem mode — hard stop