import logging


def get_logger(name):
    """
    Returns a logger for the given module name.
    All loggers inherit configuration from main.py setup.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
