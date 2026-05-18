import logging
from OrchestrationEngine import ExcelAdapter, FilesystemAdapter

logger = logging.getLogger(__name__)


def load_source(config):
    """Load input from configured source — returns unified dataframe"""
    if config.SOURCE_MODE == 'excel':
        logger.info('Source mode: Excel adapter')
        return ExcelAdapter(config).read()
    elif config.SOURCE_MODE == 'filesystem':
        logger.info('Source mode: Filesystem adapter')
        return FilesystemAdapter(config).read()
    else:
        raise ValueError(f'Unknown SOURCE_MODE: {config.SOURCE_MODE}')
