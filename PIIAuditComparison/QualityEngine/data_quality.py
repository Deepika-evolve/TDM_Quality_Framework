import numpy as np
import re
from config import (
    COL_DATABASE, COL_SCHEMA, COL_TABLE, COL_COLUMN, COL_DATATYPE, COL_ISPII,
    YES_VALUES, NO_VALUES
)


# ================================
# Column Header Patterns — Fuzzy Match
# Convert header to lowercase first then check contains
# ================================
HEADER_PATTERNS = {
    COL_DATABASE : r'database|dbname|db_name',
    COL_SCHEMA   : r'schema|schema_name|db_schema|dbschema',
    COL_TABLE    : r'table|tbl|table_name',
    COL_COLUMN   : r'column|col|field|column_name',
    COL_DATATYPE : r'datatype|data_type|dtype|type',
    COL_ISPII    : r'ispii|is_pii|pii|sensitive',
}


# ================================
# Auto Detect Headers
# ================================
def detect_headers(df):
    """
    Detects audit file column headers using regex patterns.
    Converts header to lowercase before matching — handles any case.
    Contains match — db_schema, SchemaName etc all detected.
    Falls back to config.py constants if not found.
    Returns mapping of standard name to actual header in file.
    """
    headers    = list(df.columns)
    header_map = {}

    for standard_name, pattern in HEADER_PATTERNS.items():
        matched = None
        for header in headers:
            # Lowercase first — then contains check
            if re.search(pattern, str(header).strip().lower()):
                matched = header
                break
        # If not found — use config constant as fallback
        header_map[standard_name] = matched if matched else standard_name

    return header_map


# ================================
# Clean DataFrame
# ================================
def clean_dataframe(df, header_map,mode='all'):
    """
    Applies all data quality checks on audit DataFrame.
    1. Rename headers to standard names
    2. Strip whitespace — all string columns
    3. Normalise IsPII — Yes/No/Unknown
    4. Deduplicate rows
    5. mode = 'all'   — strip + normalise + dedup
    6. mode = 'dedup' — dedup only
    7. mode = 'strip' — strip + normalise only
    """

    # Step 1 — Rename headers
    rename_map = {v: k for k, v in header_map.items() if v != k}
    if rename_map:
        df = df.rename(columns=rename_map)

    if mode in ['all', 'strip']:
        # Step 2 — Strip whitespace
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # Step 3 — Normalise IsPII
        pii = df[COL_ISPII].fillna('').astype(str).str.strip().str.lower()
        df[COL_ISPII] = np.where(pii.isin(YES_VALUES), 'Yes',
                                 np.where(pii.isin(NO_VALUES), 'No',
                                          'Unknown'))

    if mode in ['all', 'dedup']:
        # Step 4 — Deduplicate
        df = df.drop_duplicates(
            subset=[COL_DATABASE, COL_SCHEMA, COL_TABLE, COL_COLUMN],
            keep='first'
        )

    return df
