import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def write_outputs(masked_df, config, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if config.SOURCE_MODE == 'excel':
        _write_scrambled_excel(masked_df, timestamp, config)

    elif config.SOURCE_MODE == 'filesystem':
        for source_file, group in masked_df.groupby('source_file'):
            # Get source extension from first row of group
            source_ext = '.json'  # default
            if 'source_ext' in group.columns:
                source_ext = group['source_ext'].iloc[0]
            _write_scrambled_json(group, source_file, timestamp, config, source_ext)


def write_validation_reports(validation_df, config, timestamp=None):
    """Write validation reports — single or one per source"""
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if config.SOURCE_MODE == 'excel':
        _write_validation(validation_df, timestamp, config)
    elif config.SOURCE_MODE == 'filesystem':
        for source_file, group in validation_df.groupby('source_file'):
            _write_validation(group, timestamp, config, source_file=source_file)


def _write_scrambled_excel(masked_df, timestamp, config):
    try:
        out_path = Path(config.SCRAMBLED_DIR) / f'scrambled_json_{timestamp}.xlsx'
        masked_df[['json_data']].to_excel(out_path, index=False)
        logger.info(f'Scrambled: {out_path}')
    except Exception as e:
        logger.error(f'Failed to write scrambled Excel: {e}')
        raise


def _write_scrambled_json(group, source_file, timestamp, config, source_ext='.json'):
    """Write scrambled output — preserve source file extension"""
    try:
        records = []
        for val in group['json_data']:
            try:
                records.append(json.loads(str(val)))
            except json.JSONDecodeError:
                records.append(str(val))

        is_jsonl = len(records) > 1

        if is_jsonl:
            out_path = Path(config.SCRAMBLED_DIR) / f'scrambled_{source_file}_{timestamp}.jsonl'
            with open(out_path, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        else:
            # Preserve original extension — .json or .txt
            out_path = Path(config.SCRAMBLED_DIR) / f'scrambled_{source_file}_{timestamp}{source_ext}'
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(records[0] if records else {}, f, indent=2, ensure_ascii=False)

        logger.info(f'Scrambled: {out_path}')

    except Exception as e:
        logger.error(f'Failed to write scrambled output for {source_file}: {e}')
        raise


def _write_validation(validation_df, timestamp, config, source_file=None):
    try:
        if source_file:
            filename = f'validation_{source_file}_{timestamp}.xlsx'
        else:
            filename = f'masking_validation_report_{timestamp}.xlsx'
        out_path = Path(config.VALIDATION_DIR) / filename
        validation_df.to_excel(out_path, index=False)
        logger.info(f'Validation: {out_path}')
    except Exception as e:
        logger.error(f'Failed to write validation report: {e}')
        raise

