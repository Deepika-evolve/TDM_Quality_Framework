import os
import pandas as pd
from utils import get_logger

logger = get_logger(__name__)


def validate_files(previous_file, current_file):
    """
    Validates all input file conditions before comparison begins.
    1. Files exist
    2. Not same file
    3. Must be .xlsx format
    4. Common sheets must exist
    5. At least one sheet must have valid audit format
    """

    # 1 — File exists
    if not os.path.exists(previous_file):
        raise FileNotFoundError(
            f"Previous audit file not found: {previous_file}\n"
            f"Please check the file path in config.py"
        )
    if not os.path.exists(current_file):
        raise FileNotFoundError(
            f"Current audit file not found: {current_file}\n"
            f"Please check the file path in config.py"
        )

    # 2 — Not same file
    if os.path.abspath(previous_file) == os.path.abspath(current_file):
        raise ValueError(
            "Previous and current audit files are the same file.\n"
            "Comparison requires two different files."
        )

    # 3 — Must be .xlsx format
    for f in [previous_file, current_file]:
        if not f.lower().endswith('.xlsx'):
            raise ValueError(
                f"Invalid file format: {f}\n"
                f"Only .xlsx files are supported."
            )

    # 4 — Common sheets must exist
    prev_sheets = set(pd.ExcelFile(previous_file).sheet_names)
    curr_sheets = set(pd.ExcelFile(current_file).sheet_names)
    common      = prev_sheets & curr_sheets

    if not common:
        raise ValueError(
            f"No matching sheets found between files.\n"
            f"Previous file sheets : {list(prev_sheets)}\n"
            f"Current file sheets  : {list(curr_sheets)}\n"
            f"Both files must have same sheet names (connection names)."
        )

    # 5 — At least one common sheet has valid audit format
    valid = False
    for sheet in common:
        df   = pd.read_excel(previous_file, sheet_name=sheet, nrows=1)
        hdrs = [str(c).strip().lower() for c in df.columns]
        if any('database' in h or 'db' in h for h in hdrs):
            valid = True
            break

    if not valid:
        raise ValueError(
            f"Invalid audit file format.\n"
            f"No sheets found with required headers.\n"
            f"Expected headers: Database, Schema, Tables, Columns, Datatype, IsPII"
        )

    logger.info(f"Files validated — previous: {previous_file} — current: {current_file}")
    return True
