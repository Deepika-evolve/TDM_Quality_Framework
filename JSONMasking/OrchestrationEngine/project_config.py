import re, sys, os, json, logging
from datetime import datetime

logger = logging.getLogger(__name__)

SOURCE_MODE = 'excel'  # 'excel' or 'filesystem'
INPUT_FOLDER = 'inputfiles/'  # filesystem mode — all file types here
MAX_FILES_PER_RUN = 10  # filesystem mode — hard stop
def generate_project_id(project_name):
    """Generate clean project_id from project name"""
    return re.sub(r'[^a-zA-Z0-9]', '_', project_name.strip().upper())


def create_project_classifier_if_missing(project_classifier_path):
    """Create empty project classifier if it doesnt exist"""
    if not os.path.exists(project_classifier_path):
        empty = {'project_pii': {}, 'project_not_pii': {}}
        with open(project_classifier_path, 'w') as f:
            json.dump(empty, f, indent=2)
        logger.info(f'Created project classifier: {project_classifier_path}')


def setup_project(config):
    """Validate project name — generate id — set classifier path"""
    if not config.PROJECT_NAME or config.PROJECT_NAME.strip() == '':
        logger.error('PROJECT_NAME is required — set in jm_config.py')
        sys.exit(1)

    config.PROJECT_ID = generate_project_id(config.PROJECT_NAME)

    os.makedirs(config.PROJECTS_DIR, exist_ok=True)
    config.PROJECT_CLASSIFIER = os.path.join(
        config.PROJECTS_DIR, f'{config.PROJECT_ID}_classifier.json'
    )
    create_project_classifier_if_missing(config.PROJECT_CLASSIFIER)

    logger.info(f'Project Name : {config.PROJECT_NAME}')
    logger.info(f'Project ID   : {config.PROJECT_ID}')
    logger.info(f'Classifier   : {config.PROJECT_CLASSIFIER}')
    return config

