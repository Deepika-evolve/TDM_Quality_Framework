# Module level counts store
# Set once by main.py — used by get_drift_metrics
_counts_dict = {}

def set_counts(counts):
    global _counts_dict
    _counts_dict = counts if counts else {}

def get_drift_metrics(results):
    """
    Returns grouped drift metrics.
    Uses _counts_dict for tables/columns under dropped schemas.
    """

    DROPPED_TYPES = ['Column Dropped', 'Table Dropped', 'Schema Dropped', 'Database Dropped']
    NEW_TYPES     = ['New Column Added', 'New Table Added', 'New Schema Added', 'New Database Added']

    return {
        # Database Level
        'New Databases'          : len(set(
                                       (r['Database'],r['Sheet'])for r in results
                                       if r['ChangeType'] == 'New Database Added'
                                   )),
        'Dropped Databases'      : len(set(
                                       (r['Database'],r['Sheet'])for r in results
                                       if r['ChangeType'] == 'Database Dropped'
                                   )),

        # Schema Level
        'New Schemas'            : len(set(
                                       (r['Database'], r['Schema'],r['Sheet']) for r in results
                                       if r['ChangeType'] == 'New Schema Added'
                                   )),
        'Dropped Schemas'        : len(set(
                                       (r['Database'], r['Schema'],r['Sheet']) for r in results
                                       if r['ChangeType'] == 'Schema Dropped'
                                   )),

        # Table Level — include tables under dropped/new schemas
        'New Tables'             : (
                                       len(set(
                                           (r['Database'], r['Schema'], r['Table'],r['Sheet']) for r in results
                                           if r['ChangeType'] == 'New Table Added'
                                       ))
                                       + _counts_dict.get('tables_under_new_schema', 0)
                                   ),
        'Dropped Tables'         : (
                                       len(set(
                                           (r['Database'], r['Schema'], r['Table'],r['Sheet']) for r in results
                                           if r['ChangeType'] == 'Table Dropped'
                                       ))
                                       + _counts_dict.get('tables_under_dropped_schema', 0)
                                   ),

        # Column Level
        'New PII Columns'        : len([r for r in results
                                       if r['ChangeType'] in NEW_TYPES
                                       and r['IsPII'] == 'Yes']),
        'New Non PII Columns'    : len([r for r in results
                                       if r['ChangeType'] in NEW_TYPES
                                       and r['IsPII'] == 'No']),
        'Dropped PII Columns'    : (
                                       len([r for r in results
                                           if r['ChangeType'] in DROPPED_TYPES
                                           and r['IsPII'] == 'Yes'])
                                       + _counts_dict.get('pii_under_dropped_schema', 0)
                                   ),
        'Dropped Non PII Columns': (
                                       len([r for r in results
                                           if r['ChangeType'] in DROPPED_TYPES
                                           and r['IsPII'] == 'No'])
                                       + _counts_dict.get('non_pii_under_dropped_schema', 0)
                                   ),
        'Datatype Changes'       : len([r for r in results
                                       if r['ChangeType'] == 'Datatype Changed']),

        # Severity
        'HIGH Severity'          : len([r for r in results if r['Severity'] == 'HIGH']),
        'MEDIUM Severity'        : len([r for r in results if r['Severity'] == 'MEDIUM']),
        'LOW Severity'           : len([r for r in results if r['Severity'] == 'LOW']),
    }
