import os, json, logging
import pandas as pd
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jm_config as config
from OrchestrationEngine               import setup_project,load_source,write_outputs, write_validation_reports
from PIIAnalysisEngine                 import load_classifier, generate_audit_sheet
from GovernanceEngine                  import *
from MaskingEngine                     import mask_json, generate_masking_report
from QualityEngine                     import validate_json_string

for d in [config.INPUT_DIR, config.AUDIT_DIR, config.SCRAMBLED_DIR,
          config.LOG_DIR, config.AUDIT_ARCHIVE_DIR, config.VALIDATION_DIR]:
    os.makedirs(d, exist_ok=True)

log_file = os.path.join(config.LOG_DIR,
    f'json_masking_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger(__name__)


def run():
    try:
        setup_project(config)
        logger.info('=' * 60)
        logger.info(f'JSON Masking Phase 1.0 | {config.PROJECT_NAME}')

        make_readonly(config.STANDARD_CLASSIFIER)
        logger.info('Standard classifier protected — read only')

        # Input hash detection — Excel mode only
        if config.SOURCE_MODE == 'excel':
            if input_file_changed(config.INPUT_FILE, config.INPUT_HASH_FILE):
                if os.path.exists(config.HASH_AUDIT_FILE):
                    logger.warning('Input changed — previous approval cleared')
                    clear_for_restart([
                        config.HASH_AUDIT_FILE, config.AUDIT_FILE,
                        config.AUDIT_ORIGINAL, config.AUDIT_HASH_TXT,
                        config.INPUT_HASH_FILE
                    ])
            save_hash(hash_input_data(config.INPUT_FILE), config.INPUT_HASH_FILE)
        # Filesystem mode — detect input change
        elif config.SOURCE_MODE == 'filesystem':
            current_hash = hash_folder_contents(config.INPUT_DIR)
            stored_hash = load_hash(config.INPUT_HASH_FILE)
            if stored_hash and current_hash != stored_hash:
                logger.warning('Input files changed — clearing audit for re-review')
                clear_for_restart([
                    config.HASH_AUDIT_FILE,
                    config.AUDIT_FILE,
                    config.AUDIT_ORIGINAL,
                    config.AUDIT_HASH_TXT
                ])
            save_hash(current_hash, config.INPUT_HASH_FILE)
        if config.RESTART_ANALYSIS:
            clear_for_restart([config.HASH_AUDIT_FILE, config.AUDIT_FILE,
                               config.AUDIT_ORIGINAL, config.AUDIT_HASH_TXT])

        classifier = load_classifier(config.STANDARD_CLASSIFIER,
                                     config.PROJECT_CLASSIFIER,
                                     config.EXCLUSION_LIST)

        if os.path.exists(config.HASH_AUDIT_FILE):
            logger.info('hash_audit found — verifying and masking')
            valid, hash_df = verify_hash_audit(config.HASH_AUDIT_FILE, config.AUDIT_HASH_TXT)
            if not valid: return
            _run_masking(hash_df, classifier)
            return

        if os.path.exists(config.AUDIT_FILE) and os.path.exists(config.AUDIT_ORIGINAL):
            logger.info('Audit sheet found — running validation')
            approved_df = pd.read_excel(config.AUDIT_FILE)
            original_df = pd.read_excel(config.AUDIT_ORIGINAL)
            errors = validate_audit(approved_df, original_df)
            if errors:
                logger.error('Validation failed:')
                for e in errors: logger.error(e)
                print('Fix errors and re-run.')
                return
            _, hash_df = generate_hash_audit(
                approved_df, original_df,
                config.HASH_AUDIT_FILE, config.AUDIT_HASH_TXT,
                config.AUDIT_ARCHIVE_DIR
            )
            save_decisions(approved_df, config.PROJECT_CLASSIFIER, config.EXCLUSION_LIST)
            dedup_classifier(config.STANDARD_CLASSIFIER, 'global_pii')
            dedup_classifier(config.PROJECT_CLASSIFIER, 'project_pii')
            classifier = load_classifier(config.STANDARD_CLASSIFIER,
                                         config.PROJECT_CLASSIFIER,
                                         config.EXCLUSION_LIST)
            _run_masking(hash_df, classifier)
            return

        # First run — PII Analysis
        logger.info('First run — PII Analysis')
        df = load_source(config)
        audit_df = generate_audit_sheet(df, config.JSON_COLUMN, classifier)
        user_cols = ['project_id', 'doc_id', 'path', 'key', 'value',
                     'is_pii', 'scope', 'reason', 'approved', 'approved_by', 'source']
        audit_df[user_cols].to_excel(config.AUDIT_FILE, index=False)
        audit_df.to_excel(config.AUDIT_ORIGINAL, index=False)
        logger.info(f'Audit sheet: {config.AUDIT_FILE}')
        print(f'\nReview and approve: {config.AUDIT_FILE}\nRe-run when done.')

    except ValueError as e:
        logger.error(f'Validation error: {e}')
        raise
    except FileNotFoundError as e:
        logger.error(f'File not found: {e}')
        raise
    except Exception as e:
        logger.error(f'Pipeline failed: {e}')
        raise

##_run_masking — Updated
def _run_masking(hash_df, classifier):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    df = load_source(config)
    approved_fields = get_approved_fields(hash_df)
    logger.info(f'Masking: {list(approved_fields.keys())}')

    masked_rows = []
    for idx, row in df.iterrows():
        try:
            json_str = str(row[config.JSON_COLUMN])
            doc = validate_json_string(json_str, f'row_{idx + 1}')
            if doc is None:
                row_dict = row.to_dict()
                row_dict['doc_id'] = f'row_{idx + 1}'
                masked_rows.append(row_dict)
                continue
            row_dict = row.to_dict()
            row_dict['doc_id'] = f'row_{idx + 1}'
            row_dict[config.JSON_COLUMN] = json.dumps(mask_json(doc, approved_fields))
            masked_rows.append(row_dict)
        except json.JSONDecodeError as e:
            logger.warning(f'Row {idx + 1}: JSON parse error — {e} — skipped')
            row_dict = row.to_dict()
            row_dict['doc_id'] = f'row_{idx + 1}'
            masked_rows.append(row_dict)
        except Exception as e:
            logger.warning(f'Row {idx + 1}: Masking failed — {e} — original kept')
            row_dict = row.to_dict()
            row_dict['doc_id'] = f'row_{idx + 1}'
            masked_rows.append(row_dict)

    masked_df = pd.DataFrame(masked_rows)
    # Write scrambled output — single or per source file
    write_outputs(masked_df, config, timestamp)

    # Generate validation report — returns dataframe
    validation_df = generate_masking_report(
        hash_df, masked_df, classifier,
        config.MASKING_REPORT_FILE, config.JSON_COLUMN
    )

    # Write validation reports — single or per source file
    if validation_df is not None:
        write_validation_reports(validation_df, config, timestamp)

    if config.DELETE_SOURCE_AFTER_MASKING:
        if config.SOURCE_MODE == 'excel':
            os.remove(config.INPUT_FILE)
        logger.info('Source deleted')

    logger.info('Masking completed successfully')
    logger.info('=' * 60)


if __name__ == '__main__':
    run()

