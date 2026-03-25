import sys
import os
import time
import logging
from utils import get_logger
from datetime import datetime

# ================================
# Path Setup
# ================================
MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(MODULE_DIR, 'ComparisonEngine'))
sys.path.insert(0, os.path.join(MODULE_DIR, 'OutputEngine'))
sys.path.insert(0, os.path.join(MODULE_DIR, 'QualityEngine'))

from config       import PREVIOUS_AUDIT, CURRENT_AUDIT, OUTPUT_DIR
from compare      import compare_pii_audit
from report_excel import write_excel_report
from report_html  import write_html_report
import metrics as metrics_module

# ================================
# Logging Setup
# ================================
timestamp    = datetime.today().strftime('%Y%m%d_%H%M%S')
log_file     = os.path.join(OUTPUT_DIR, f"drift_detection_{timestamp}.log")
output_excel = os.path.join(OUTPUT_DIR, f"PII_Audit_Drift_Detection_{timestamp}.xlsx")
output_html  = os.path.join(OUTPUT_DIR, f"PII_Audit_Drift_Detection_{timestamp}.html")

logging.basicConfig(
    level    = logging.INFO,
    format   = '%(asctime)s — %(levelname)s — %(name)s — %(message)s',
    handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = get_logger(__name__)


def run():
    logger.info("=" * 45)
    logger.info("  TDM Quality Framework")
    logger.info("  PII Audit Drift Detection Engine")
    logger.info("=" * 45)

    total_start = time.time()

    try:
        # Step 1 — Compare
        logger.info("[Step 1] Running drift detection...")
        start   = time.time()
        results, counts_dict = compare_pii_audit(PREVIOUS_AUDIT, CURRENT_AUDIT)
        logger.info(f"  Comparison time  : {time.time() - start:.2f}s")
        logger.info(f"  Total changes    : {len(results)}")

        # Set counts once
        metrics_module.set_counts(counts_dict)

        # Step 2 — Excel Report
        logger.info("[Step 2] Generating Excel report...")
        start = time.time()
        try:
            write_excel_report(results, CURRENT_AUDIT, output_excel)
            logger.info(f"  Excel build time : {time.time() - start:.2f}s")
        except Exception as e:
            logger.error(f"  Excel report failed: {e}")

        # Step 3 — HTML Report
        logger.info("[Step 3] Generating HTML report...")
        start = time.time()
        try:
            write_html_report(results, output_html)
            logger.info(f"  HTML build time  : {time.time() - start:.2f}s")
        except Exception as e:
            logger.error(f"  HTML report failed: {e}")

        logger.info(f"  Total time       : {time.time() - total_start:.2f}s")
        logger.info(f"  Log file         : {log_file}")
        logger.info("=" * 45)

        # Exit codes for CI/CD
        if counts_dict['sheets_with_errors'] > 0:
            logger.warning(f"Partial comparison completed - {counts_dict['sheets_with_errors']} connection(s) failed.\n"
                            f"Results may be incomplete. Please review log file and rerun.\n"
                            f"Exit code 3 - rerun required")
            sys.exit(3) ##rerun required- partial results with error
        elif results:
            logger.warning("Drift detected — review required")
            sys.exit(1)
        else:
            logger.info("No drift detected — pipeline can proceed")
            sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(2)
    except ValueError as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    run()
