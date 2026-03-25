from datetime import datetime


# ================================
# Build Result Row
# ================================
def build_result(sheet, database, schema, table, column,
                 datatype, change_type, is_pii, severity, action, row_number=None):
    """
    Builds a single result dictionary.
    Single source of truth for result structure.
    """
    return {
        "ComparisonDate" : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "Sheet"          : sheet,
        "Database"       : database,
        "Schema"         : schema,
        "Table"          : table,
        "Column"         : column,
        "Datatype"       : datatype,
        "ChangeType"     : change_type,
        "IsPII"          : is_pii,
        "Severity"       : severity,
        "Action"         : action,
        "ExcelRowNumber" : row_number
    }
