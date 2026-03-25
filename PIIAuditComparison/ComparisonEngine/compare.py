import pandas as pd
from models        import build_result
from data_quality  import detect_headers, clean_dataframe
from error_handler import validate_files
import logging
from utils import get_logger
logger = get_logger("Drift Detection Engine")
from config import (
    COL_DATABASE, COL_SCHEMA, COL_TABLE, COL_COLUMN, COL_DATATYPE, COL_ISPII,
    NEW_DATABASE, DROPPED_DATABASE,
    NEW_SCHEMA,   DROPPED_SCHEMA,
    NEW_TABLE,    DROPPED_TABLE,
    NEW_COLUMN,   DROPPED_COLUMN,
    DATATYPE_CHANGED,
    HIGH, MEDIUM, LOW
)
from error_handler import validate_files


def compare_pii_audit(previous_file, current_file):

    # Validate files before processing

    validate_files(previous_file, current_file)

    results     = []
    counts_dict = {
        'tables_under_new_schema'     : 0,
        'tables_under_dropped_schema' : 0,
        'pii_under_dropped_schema'    : 0,
        'non_pii_under_dropped_schema': 0,
        'sheets_with_errors': 0,
    }
    try:
        prev_sheets   = set(s.strip() for s in pd.ExcelFile(previous_file).sheet_names)
        curr_sheets   = set(s.strip() for s in pd.ExcelFile(current_file).sheet_names)
        common_sheets = prev_sheets & curr_sheets
        """trimmedsheetname"""
        actual_trimmedprev={s.strip(): s for s in pd.ExcelFile(previous_file).sheet_names}
        actual_trimmedcurr={s.strip(): s for s in pd.ExcelFile(current_file).sheet_names}

        for sheet in common_sheets:

            logger.info(f"Comparing connection: {sheet}")
            ##print(f"\nComparing connection: {sheet}")

            try:
                prev = pd.read_excel(previous_file, sheet_name=actual_trimmedprev.get(sheet,sheet))
                curr = pd.read_excel(current_file,  sheet_name=actual_trimmedcurr.get(sheet,sheet))


                # Auto detect headers + data quality
                prev = clean_dataframe(prev, detect_headers(prev), mode='all')
                curr = clean_dataframe(curr, detect_headers(curr), mode='all')


                prev_databases = set(prev[COL_DATABASE].unique())
                curr_databases = set(curr[COL_DATABASE].unique())

                # ================================
                # Database Level
                # ================================

                # New databases — one row per schema inside
                for db in (curr_databases - prev_databases):
                    ##print(f"  HIGH — New database: {db}")
                    curr_db      = curr[curr[COL_DATABASE] == db]
                    curr_schemas = curr_db[COL_SCHEMA].unique()
                    for schema in curr_schemas:
                        schema_rw=curr_db[curr_db[COL_SCHEMA]==schema]
                        first_row=int(schema_rw.index[0])+2
                        results.append(build_result(
                            sheet=sheet, database=db, schema=schema,
                            table='N/A', column='N/A', datatype='N/A',
                            change_type=NEW_DATABASE, is_pii='Unknown',
                            severity=HIGH,
                            action='Scan entire database — PII analysis required',
                            row_number=first_row
                        ))

                # Dropped databases — one row per schema that had PII
                for db in (prev_databases - curr_databases):
                    ##print(f"  HIGH — Database dropped: {db}")
                    prev_db      = prev[prev[COL_DATABASE] == db]
                    prev_schemas = prev_db[COL_SCHEMA].unique()
                    for schema in prev_schemas:
                        schema_rows = prev_db[prev_db[COL_SCHEMA] == schema]
                        has_pii     = 'Yes' if 'Yes' in schema_rows[COL_ISPII].values else 'No'
                        severity    = HIGH if has_pii == 'Yes' else MEDIUM
                        action      = 'Database dropped — PII data detected — verify removal — deactivate all masking routines' \
                                      if has_pii == 'Yes' else \
                                      'Database dropped — verify removal — deactivate masking routines'
                        results.append(build_result(
                            sheet=sheet, database=db, schema=schema,
                            table='N/A', column='N/A', datatype='N/A',
                            change_type=DROPPED_DATABASE, is_pii=has_pii,
                            severity=severity, action=action
                        ))

                # ================================
                # Schema Level
                # ================================
                for database in (prev_databases & curr_databases):

                    prev_db      = prev[prev[COL_DATABASE] == database]
                    curr_db      = curr[curr[COL_DATABASE] == database]
                    prev_schemas = set(prev_db[COL_SCHEMA].unique())
                    curr_schemas = set(curr_db[COL_SCHEMA].unique())
                    dropped_schemas = prev_schemas - curr_schemas

                    # New schemas — one row per column — all highlighted
                    for schema in (curr_schemas - prev_schemas):
                        ##print(f"  HIGH — New schema: {database}.{schema}")
                        schema_rows = curr_db[curr_db[COL_SCHEMA] == schema]

                        # Count distinct tables for metrics
                        counts_dict['tables_under_new_schema'] += len(schema_rows[COL_TABLE].unique())

                        for _, row in schema_rows.iterrows():
                            is_pii   = row[COL_ISPII]
                            severity = HIGH if is_pii == 'Yes' else MEDIUM
                            results.append(build_result(
                                sheet=sheet, database=database, schema=schema,
                                table=row[COL_TABLE], column=row[COL_COLUMN],
                                datatype=row[COL_DATATYPE],
                                change_type=NEW_SCHEMA, is_pii=is_pii,
                                severity=severity,
                                action='New schema — PII analysis required — raise change request',
                                row_number=int(row.name) + 2
                            ))

                    # Dropped schemas — one row only
                    for schema in dropped_schemas:
                        ##print(f"  HIGH — Schema dropped: {database}.{schema}")
                        schema_rows   = prev_db[prev_db[COL_SCHEMA] == schema]
                        has_pii       = 'Yes' if 'Yes' in schema_rows[COL_ISPII].values else 'No'
                        severity      = HIGH if has_pii == 'Yes' else MEDIUM
                        action        = 'Schema dropped — PII columns detected — verify removal — deactivate masking routines' \
                                        if has_pii == 'Yes' else \
                                        'Schema dropped — verify removal — deactivate masking routines'

                        # Count for metrics
                        counts_dict['tables_under_dropped_schema'] += len(schema_rows[COL_TABLE].unique())
                        counts_dict['pii_under_dropped_schema']    += len(schema_rows[schema_rows[COL_ISPII] == 'Yes'])
                        counts_dict['non_pii_under_dropped_schema']+= len(schema_rows[schema_rows[COL_ISPII] == 'No'])

                        results.append(build_result(
                            sheet=sheet, database=database, schema=schema,
                            table='N/A', column='N/A', datatype='N/A',
                            change_type=DROPPED_SCHEMA, is_pii=has_pii,
                            severity=severity, action=action
                        ))

                    # ================================
                    # Table Level
                    # ================================
                    for schema in (prev_schemas & curr_schemas):

                        prev_schema = prev_db[prev_db[COL_SCHEMA] == schema]
                        curr_schema = curr_db[curr_db[COL_SCHEMA] == schema]
                        prev_tables = set(prev_schema[COL_TABLE].unique())
                        curr_tables = set(curr_schema[COL_TABLE].unique())
                        dropped_tables = prev_tables - curr_tables

                        # New tables — one row per column
                        for table in (curr_tables - prev_tables):
                            ##print(f"  HIGH — New table: {database}.{schema}.{table}")
                            new_table_rows = curr_schema[curr_schema[COL_TABLE] == table]
                            for _, row in new_table_rows.iterrows():
                                is_pii   = row[COL_ISPII]
                                severity = HIGH if is_pii == 'Yes' else MEDIUM
                                results.append(build_result(
                                    sheet=sheet, database=database, schema=schema,
                                    table=table, column=row[COL_COLUMN],
                                    datatype=row[COL_DATATYPE],
                                    change_type=NEW_TABLE, is_pii=is_pii,
                                    severity=severity,
                                    action='New table — scan all columns — add PII to masking scope',
                                    row_number=int(row.name) + 2
                                ))

                        # Dropped tables — one row per PII column
                        # Skip if parent schema dropped
                        for table in dropped_tables:
                            if schema in dropped_schemas:
                                continue

                            ##print(f"  HIGH — Table dropped: {database}.{schema}.{table}")
                            table_rows = prev_schema[prev_schema[COL_TABLE] == table]
                            has_pii    = 'Yes' if 'Yes' in table_rows[COL_ISPII].values else 'No'

                            pii_rows = table_rows[table_rows[COL_ISPII] == 'Yes']

                            if not pii_rows.empty:
                                for _, row in pii_rows.iterrows():
                                    results.append(build_result(
                                        sheet=sheet, database=database, schema=schema,
                                        table=table, column=row[COL_COLUMN],
                                        datatype=row[COL_DATATYPE],
                                        change_type=DROPPED_TABLE, is_pii='Yes',
                                        severity=HIGH,
                                        action='Table dropped — PII columns detected — verify removal — deactivate masking routines'
                                    ))
                            else:
                                results.append(build_result(
                                    sheet=sheet, database=database, schema=schema,
                                    table=table, column='N/A', datatype='N/A',
                                    change_type=DROPPED_TABLE, is_pii='No',
                                    severity=MEDIUM,
                                    action='Table dropped — verify removal — deactivate masking routines'
                                ))

                        # ================================
                        # Column Level
                        # ================================
                        common_tables = prev_tables & curr_tables

                        for table in common_tables:

                            prev_tbl  = prev_schema[prev_schema[COL_TABLE] == table]
                            curr_tbl  = curr_schema[curr_schema[COL_TABLE] == table]
                            prev_keys = set(zip(prev_tbl[COL_SCHEMA], prev_tbl[COL_COLUMN]))
                            curr_keys = set(zip(curr_tbl[COL_SCHEMA], curr_tbl[COL_COLUMN]))

                            # New columns
                            for sch, column in (curr_keys - prev_keys):
                                match      = curr_tbl[(curr_tbl[COL_SCHEMA] == sch) & (curr_tbl[COL_COLUMN] == column)]
                                is_pii     = match[COL_ISPII].values[0]
                                datatype   = match[COL_DATATYPE].values[0]
                                row_number = int(match.index[0]) + 2
                                severity   = HIGH if is_pii == 'Yes' else LOW
                                action     = 'Add to masking scope immediately' if is_pii == 'Yes' else 'Review required'
                                results.append(build_result(
                                    sheet=sheet, database=database, schema=sch,
                                    table=table, column=column, datatype=datatype,
                                    change_type=NEW_COLUMN, is_pii=is_pii,
                                    severity=severity, action=action,
                                    row_number=row_number
                                ))

                            # Dropped columns
                            for sch, column in (prev_keys - curr_keys):
                                match    = prev_tbl[(prev_tbl[COL_SCHEMA] == sch) & (prev_tbl[COL_COLUMN] == column)]
                                is_pii   = match[COL_ISPII].values[0]
                                datatype = match[COL_DATATYPE].values[0]

                                # Skip if parent schema dropped
                                if schema in dropped_schemas:
                                    continue

                                # Skip non PII if parent table dropped
                                if table in dropped_tables and is_pii != 'Yes':
                                    continue

                                severity = HIGH if is_pii == 'Yes' else LOW
                                action   = 'Column dropped — PII detected — verify removal — update masking scope' \
                                           if is_pii == 'Yes' else \
                                           'Column dropped — verify removal'

                                results.append(build_result(
                                    sheet=sheet, database=database, schema=sch,
                                    table=table, column=column, datatype=datatype,
                                    change_type=DROPPED_COLUMN, is_pii=is_pii,
                                    severity=severity, action=action
                                ))

                            # Datatype changes
                            for sch, column in (prev_keys & curr_keys):
                                prev_dtype = prev_tbl[(prev_tbl[COL_SCHEMA] == sch) & (prev_tbl[COL_COLUMN] == column)][COL_DATATYPE].values[0]
                                curr_dtype = curr_tbl[(curr_tbl[COL_SCHEMA] == sch) & (curr_tbl[COL_COLUMN] == column)][COL_DATATYPE].values[0]

                                if prev_dtype != curr_dtype:
                                    match      = curr_tbl[(curr_tbl[COL_SCHEMA] == sch) & (curr_tbl[COL_COLUMN] == column)]
                                    is_pii     = match[COL_ISPII].values[0]
                                    row_number = int(match.index[0]) + 2
                                    severity   = HIGH if is_pii == 'Yes' else MEDIUM
                                    results.append(build_result(
                                        sheet=sheet, database=database, schema=sch,
                                        table=table, column=column,
                                        datatype=f"{prev_dtype} → {curr_dtype}",
                                        change_type=DATATYPE_CHANGED, is_pii=is_pii,
                                        severity=severity, action='Review required',
                                        row_number=row_number
                                    ))
            except Exception as e:
                logger.error(f"Error reading sheet {sheet}: {e}")
                counts_dict['sheets_with_errors'] += 1
                continue
        if not results:
            print("\nNo changes detected across all connections")
            logger.info("\nNo changes detected across all connections")
    except Exception as e:
            logger.error(f"Unexpected error occured: {e}")
            counts_dict['sheets_with_errors'] += 1
            raise #propagates to main.py
    return results, counts_dict
