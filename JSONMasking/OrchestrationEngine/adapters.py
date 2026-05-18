import json
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class ExcelAdapter:
    """Reads JSON strings from an Excel file"""

    def __init__(self, config):
        self.config = config

    def read(self):
        try:
            df = pd.read_excel(self.config.INPUT_FILE, header=None)
            first_val = str(df.iloc[0, 0]).strip()
            if first_val.startswith('{') or first_val.startswith('['):
                df.columns = ['json_data']
            else:
                df = pd.read_excel(self.config.INPUT_FILE)
                df.columns = ['json_data']
            df['source_file'] = 'excel_input'
            logger.info(f'ExcelAdapter: {len(df)} rows loaded')
            return df
        except Exception as e:
            logger.error(f'ExcelAdapter: failed to read: {e}')
            raise


class FilesystemAdapter:
    """Reads JSON, JSONL, TXT files from input folder"""

    SUPPORTED_EXTENSIONS = ['.json', '.jsonl', '.txt']

    def __init__(self, config):
        self.config = config

    def read(self):
        rows = []
        file_count = 0
        input_folder = Path(self.config.INPUT_DIR)

        if not input_folder.exists():
            raise FileNotFoundError(f'Input folder not found: {input_folder}')

        for filepath in sorted(input_folder.iterdir()):
            if filepath.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue
            if file_count >= self.config.MAX_FILES_PER_RUN:
                logger.warning(f'MAX_FILES_PER_RUN reached — remaining skipped')
                break
            if filepath.suffix.lower() == '.jsonl':
                rows.extend(self._read_jsonl(filepath))
            else:
                rows.extend(self._read_json(filepath))
            file_count += 1

        logger.info(f'FilesystemAdapter: {len(rows)} rows from {file_count} files')
        return pd.DataFrame(rows)

    def _read_json(self, filepath):
        try:
            content = filepath.read_text(encoding='utf-8').strip()
            json.loads(content)
            logger.info(f'Read: {filepath.name}')
            return [{'json_data': content, 'source_file': filepath.stem,'source_ext': filepath.suffix}]
        except json.JSONDecodeError as e:
            logger.warning(f'Invalid JSON {filepath.name}: {e} — skipped')
            return []
        except Exception as e:
            logger.warning(f'Cannot read {filepath.name}: {e} — skipped')
            return []

    def _read_jsonl(self, filepath):
        rows = []
        try:
            for i, line in enumerate(filepath.read_text(encoding='utf-8').splitlines()):
                line = line.strip()
                if not line: continue
                try:
                    json.loads(line)
                    rows.append({'json_data': line, 'source_file': filepath.stem,'source_ext': filepath.suffix})
                except json.JSONDecodeError as e:
                    logger.warning(f'Line {i+1} in {filepath.name}: {e} — skipped')
            logger.info(f'Read: {filepath.name} — {len(rows)} rows')
        except Exception as e:
            logger.warning(f'Cannot read {filepath.name}: {e} — skipped')
        return rows
