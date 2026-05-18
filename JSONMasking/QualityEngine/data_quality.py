import json
import logging
import math,re
from datetime import datetime
logger = logging.getLogger(__name__)

def validate_json_string(json_str, doc_id):
    """Validate JSON string — return parsed dict or None"""
    if not json_str or str(json_str).strip() in ['', 'nan', 'None']:
        logger.warning(f'{doc_id} — empty JSON string — skipped')
        return None
    try:
        return json.loads(str(json_str).strip())
    except json.JSONDecodeError as e:
        logger.error(f'{doc_id} - invalid JSON - {e}')
        return None

def normalise_key(key):
    """Normalise key for matching — lowercase strip"""
    return str(key).strip().lower()

def partial_mask_value(value, show_pii=False):
    """Partially mask value for audit sheet — show enough to judge not expose"""
    if show_pii:
        return value  # trusted environment — show full value
    if value!="container":
        s = str(value).strip()
        if len(s) <= 4:
            return '***'
        return s[:2] + '*' * (len(s) - 4) + s[-2:]
    # deepika@company.com → de**************om
    # 9876543210         → 98******10

def is_primitive_array(value):
    """Check if value is a list — may contain mix of primitives and dicts"""
    return isinstance(value, list)

def is_empty_value(value):
    """Check if value is empty, null, or NaN"""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if str(value).strip() == '':
        return True
    return False

def clean_value(val):
    """Convert NaN from pandas Excel read to empty string"""
    if val is None: return ''
    if isinstance(val, float) and math.isnan(val): return ''
    return val

def is_valid_email_pattern(value):
    """Email must have at least one letter in local part + valid domain"""
    try:
        s = str(value).strip()
        pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9._+\-]*@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
        return bool(pattern.match(s))
    except: return False

def is_valid_phone_pattern(value):
    """Phone should contain only digits, spaces, hyphens, brackets, + sign"""
    try:
        s = str(value).strip()
        if isinstance(value, bool): return False
        pattern = re.compile(r'^[+\d][\d\s\-().]{3,}$')
        return bool(pattern.match(s))
    except: return False

def is_valid_name_pattern(value):
    """Name must contain at least one alphabetic character"""
    try:
        if isinstance(value, bool): return False
        return any(c.isalpha() for c in str(value))
    except: return False

def is_valid_date_pattern(value):
    """Date must be parseable in known formats"""
    formats = ['%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%m/%d/%Y']
    for fmt in formats:
        try:
            datetime.strptime(str(value).strip(), fmt)
            return True
        except: continue
    return False

def is_valid_ip_pattern(value):
    """IP must match IPv4 or IPv6 pattern"""
    try:
        s = str(value).strip()
        ipv4 = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        ipv6 = re.compile(r'^[0-9a-fA-F:]+$')
        return bool(ipv4.match(s) or ipv6.match(s))
    except: return False

def is_valid_url_pattern(value):
    """URL must start with http or /"""
    try:
        s = str(value).strip()
        return s.startswith('http') or s.startswith('https') or s.startswith('/')
    except: return False

def is_valid_city_country_pattern(value):
    """City and country must not contain digits"""
    try:
        s = str(value).strip()
        if not s: return False
        return not any(c.isdigit() for c in s)
    except: return False

def is_valid_address_pattern(value):
    """Street and address must have at least one letter — digits alone not valid"""
    try:
        s = str(value).strip()
        if not s: return False
        return any(c.isalpha() for c in s)
    except: return False
