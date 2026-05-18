##Imports and Setup
import hashlib
import random
import re
from datetime import datetime, timedelta
from faker import Faker
from QualityEngine import *

# Faker with fixed seed — consistent output across runs
fake = Faker('en_IN')
Faker.seed(42)

# Pools — generated once at startup — same every run
FIRST_NAME_POOL   = [fake.first_name().lower()  for _ in range(500)]
LAST_NAME_POOL    = [fake.last_name().lower()   for _ in range(500)]
STREET_NAME_POOL  = [fake.street_name()         for _ in range(200)]
CITY_POOL         = [fake.city()                for _ in range(200)]
COUNTRY_POOL      = [fake.country()             for _ in range(200)]
# IATA airport codes — curated pool for city code masking
IATA_CODE_POOL = [
    'BLR', 'BOM', 'DEL', 'MAA', 'HYD', 'CCU', 'AMD', 'PNQ', 'COK', 'IXC',
    'JFK', 'LAX', 'ORD', 'SFO', 'ATL', 'DFW', 'MIA', 'SEA', 'BOS', 'DEN',
    'LHR', 'LGW', 'MAN', 'CDG', 'AMS', 'FRA', 'MUC', 'ZRH', 'MAD', 'FCO',
    'DXB', 'AUH', 'DOH', 'KWI', 'RUH', 'BAH', 'MCT', 'AMM', 'CAI', 'ADD',
    'SYD', 'MEL', 'BNE', 'PER', 'SIN', 'KUL', 'BKK', 'HKG', 'NRT', 'ICN',
    'PEK', 'PVG', 'CGK', 'MNL', 'SGN', 'DAD', 'GRU', 'BOG', 'LIM', 'SCL',
    'JNB', 'CPT', 'NBO', 'LOS', 'ACC', 'ABV', 'CMN', 'TUN', 'ALG', 'CAI'
]

# ISO country codes — curated pool for country code masking
COUNTRY_CODE_POOL = [
    'US', 'GB', 'DE', 'FR', 'AU', 'CA', 'JP', 'BR', 'ZA', 'NZ',
    'IN', 'CN', 'SG', 'AE', 'SA', 'QA', 'KW', 'OM', 'BH', 'JO',
    'IT', 'ES', 'NL', 'CH', 'SE', 'NO', 'DK', 'FI', 'BE', 'AT',
    'MX', 'AR', 'CO', 'PE', 'CL', 'NG', 'KE', 'GH', 'ET', 'TZ',
    'MY', 'TH', 'VN', 'ID', 'PH', 'KR', 'HK', 'TW', 'NP', 'LK'
]


##Core Hash Seed
def get_seed(value):
    if is_empty_value(value):
        return value
    return int(hashlib.md5(str(value).encode()).hexdigest(), 16)

##Helper — is_name_format
def is_name_format(local):
    """Detect if email local part is a name format"""
    return bool(re.match(r'^[a-z]+[._\-][a-z]+$', local.lower()))

##mask_name — with field_type
def mask_name(value, field_type='name'):
    """Mask name — field_type: name or email"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_name_pattern(value):
        return value  # digits only — return as-is

    try:
        if field_type == 'email':
            local         = str(value).strip().lower()
            parts         = re.split(r'[._\-]+', local)
            name_parts    = [p for p in parts if len(p) >= 2]
            initial_parts = [p for p in parts if len(p) == 1]

            if len(name_parts) >= 2:
                first = FIRST_NAME_POOL[get_seed(name_parts[0].strip().lower()) % len(FIRST_NAME_POOL)]
                last  = LAST_NAME_POOL[get_seed(name_parts[-1].strip().lower()) % len(LAST_NAME_POOL)]
            elif len(name_parts) == 1 and initial_parts:
                if len(parts[0]) == 1:
                    # d.mothilal — initial first
                    first = FIRST_NAME_POOL[get_seed(initial_parts[0].strip().lower()) % len(FIRST_NAME_POOL)]
                    last  = LAST_NAME_POOL[get_seed(name_parts[0].strip().lower()) % len(LAST_NAME_POOL)]
                else:
                    # deepika.m — initial last
                    first = FIRST_NAME_POOL[get_seed(name_parts[0].strip().lower()) % len(FIRST_NAME_POOL)]
                    last  = LAST_NAME_POOL[get_seed(initial_parts[0].strip().lower()) % len(LAST_NAME_POOL)]
            else:
                return FIRST_NAME_POOL[get_seed(local.strip().lower()) % len(FIRST_NAME_POOL)].title()
            return f'{first.title()} {last.title()}'

        else:
            parts = str(value).strip().split()
            if len(parts) >= 2:
                first = FIRST_NAME_POOL[get_seed(parts[0].strip().lower()) % len(FIRST_NAME_POOL)]
                last  = LAST_NAME_POOL[get_seed(parts[-1].strip().lower()) % len(LAST_NAME_POOL)]
                return f'{first.title()} {last.title()}'
            return FIRST_NAME_POOL[get_seed(str(value).strip().lower()) % len(FIRST_NAME_POOL)].title()
    except:
        return 'Masked Name'


##mask_email — Format Aware
def mask_email(value):
    """Mask email — detect format — correlate with name if name format"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_email_pattern(value):
        return value  # wrong pattern — return as-is — report will flag
    try:
        local, domain = str(value).strip().lower().split('@')

        if is_name_format(local):
            masked_name  = mask_name(local, field_type='email')
            name_parts   = masked_name.lower().split()
            first_masked = name_parts[0]
            last_masked  = name_parts[-1] if len(name_parts) > 1 else ''

            original_parts  = re.split(r'[._\-]+', local)
            first_is_initial = len(original_parts[0]) == 1
            last_is_initial  = len(original_parts[-1]) == 1 if len(original_parts) > 1 else False

            sep = '.' if '.' in local else '_' if '_' in local else '-'

            if first_is_initial:
                # d.mothilal → i.chand
                masked_local = f'{first_masked[0]}{sep}{last_masked}'
            elif last_is_initial:
                # deepika.m → ishani.c
                masked_local = f'{first_masked}{sep}{last_masked[0]}'
            else:
                # deepika.mothilal → ishani.chand
                masked_local = f'{first_masked}{sep}{last_masked}'
        else:
            # Not name format — random from pool
            masked_local = FIRST_NAME_POOL[get_seed(local) % len(FIRST_NAME_POOL)].lower()

        return f'{masked_local}@{domain}'

    except:
        idx = get_seed(str(value)) % len(FIRST_NAME_POOL)
        return f'{FIRST_NAME_POOL[idx].lower()}@testing.com'


##mask_phone / mask_number
def mask_number(value):
    """Format preserving — retain first N digits — preserve type"""
    if is_empty_value(value): return value
    if not is_valid_phone_pattern(value):
        return value  # wrong pattern — return as-is
    if isinstance(value, bool): return value
    try:
        original_is_int   = isinstance(value, int)
        original_is_float = isinstance(value, float)
        rng = random.Random(get_seed(value))
        s   = str(value)

        digit_count  = sum(1 for c in s if c.isdigit())
        retain_count = 1 if digit_count <= 5 else 2

        result      = ''
        digits_seen = 0
        for c in s:
            if c.isdigit():
                digits_seen += 1
                if digits_seen <= retain_count:
                    result += c
                else:
                    result += str(rng.randint(0, 9))
            else:
                result += c

        if original_is_int:   return int(result)
        if original_is_float: return float(result)
        return result
    except:
        return '***REDACTED***'

def mask_postal(value):
    """Mask postal code — validates format first"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    try:
        s = str(value).strip()
        # Postal code must contain at least one digit
        if not any(c.isdigit() for c in s):
            return value  # letters only — Wrong Pattern — return as-is
        # Valid postal format — delegate to mask_alphanumeric
        return mask_alphanumeric(value)
    except:
        return '***REDACTED***'

def mask_partial(value, show_last=4, mask_char='X'):
    """Partial masking — retain last N alphanumeric characters — mask rest with X"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    try:
        s = str(value).strip()
        alnum = [c for c in s if c.isalnum()]
        if len(alnum) <= show_last:
            return s  # too short — return as-is
        masked_count = len(alnum) - show_last
        result = ''
        replaced = 0
        for c in s:
            if c.isalnum() and replaced < masked_count:
                result += mask_char
                replaced += 1
            else:
                result += c
        return result
    except:
        return '***REDACTED***'

def mask_alphanumeric(value):
    """Smart masking based on value format"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    try:
        s   = str(value).strip()
        rng = random.Random(get_seed(s))

        has_digits = any(c.isdigit() for c in s)
        has_alpha  = any(c.isalpha() for c in s)

        if has_digits and not has_alpha:
            # Only digits — delegate to mask_number
            return mask_number(value)

        elif has_alpha and not has_digits:
            if s.isupper() and len(s) <= 5:
                # Short uppercase — likely a code — random letters
                return ''.join(
                    chr(rng.randint(65, 90)) if c.isalpha() else c
                    for c in s
                )
            else:
                # Longer or mixed case — likely a name
                return mask_name(value)

        else:
            # Mixed alphanumeric — mask digits and letters both
            digit_count  = sum(1 for c in s if c.isdigit())
            retain_count = 1 if digit_count <= 5 else 2
            digits_seen  = 0
            result = ''
            for c in s:
                if c.isdigit():
                    digits_seen += 1
                    if digits_seen <= retain_count:
                        result += c
                    else:
                        result += str(rng.randint(0, 9))
                elif c.isalpha():
                    if c.isupper():
                        result += chr(rng.randint(65, 90))
                    else:
                        result += chr(rng.randint(97, 122))
                else:
                    result += c
            return result

    except:
        return '***REDACTED***'


def mask_phone(value):    return mask_number(value)
def mask_ssn(value):      return mask_number(value)
def mask_pan(value):      return mask_number(value)
def mask_aadhaar(value):  return mask_number(value)
def mask_passport(value): return mask_number(value)

###mask_dob
def mask_dob(value):
    """Date shifting — preserve format and type"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_date_pattern(value):
        return value  # digits only — return as-is
    formats = ['%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%m/%d/%Y']
    for fmt in formats:
        try:
            dob   = datetime.strptime(str(value).strip(), fmt)
            shift = (get_seed(str(value)) % 730) - 365
            return (dob + timedelta(days=shift)).strftime(fmt)
        except: continue
    return '1900-01-01'

##mask_address / mask_city / mask_country / mask_ip
def mask_address(value):
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_address_pattern(value):
        return value  # Wrong Pattern — digits only
    try:
        parts = str(value).strip().split()
        masked_street = STREET_NAME_POOL[get_seed(value) % len(STREET_NAME_POOL)]
        if parts and parts[0].replace('-','').isdigit():
            return f'{parts[0]} {masked_street}'
        return masked_street
    except: return '*** Masked Address ***'

def mask_city(value):
    """Mask city — detect code vs name — use IATA pool for codes"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_city_country_pattern(value):
        return value  # Wrong Pattern — digits in city
    try:
        s = str(value).strip()
        # Short uppercase — likely city/airport code
        if s.isupper() and len(s) <= 5 and s.isalpha():
            return IATA_CODE_POOL[get_seed(s) % len(IATA_CODE_POOL)]
        # Full city name — Faker pool
        return CITY_POOL[get_seed(s) % len(CITY_POOL)]
    except:
        return 'Masked City'

def mask_country(value):
    """Mask country — detect code vs name — use ISO pool for codes"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_city_country_pattern(value):
        return value  # Wrong Pattern — digits in country
    try:
        s = str(value).strip()
        # Short uppercase — likely ISO country code
        if s.isupper() and len(s) <= 3 and s.isalpha():
            return COUNTRY_CODE_POOL[get_seed(s) % len(COUNTRY_CODE_POOL)]
        # Full country name — Faker pool
        return COUNTRY_POOL[get_seed(s) % len(COUNTRY_POOL)]
    except:
        return '***REDACTED***'

def mask_url(value):
    """Mask URL — replace with dummy endpoint — real URL not exposed"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    if not is_valid_url_pattern(value):
        return value
    try:
        s = str(value).strip()
        if s.startswith('http') or s.startswith('https') or s.startswith('/'):
            return 'https://masked.example.com/api/resource'
        return mask_generic(value)
    except:
        return '***REDACTED***'


def mask_ip(value):
    """Mask IP — validates format and octet range — IPv4 and IPv6"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    try:
        s   = str(value).strip()
        rng = random.Random(get_seed(s))

        if ':' in s:
            # IPv6
            segments = s.split(':')
            masked = []
            for seg in segments:
                if seg == '':
                    masked.append('')
                else:
                    masked.append(hex(rng.randint(0, 65535))[2:].zfill(4))
            return ':'.join(masked)

        elif '.' in s:
            # IPv4 — validate octets in range 0-255
            octets = s.split('.')
            if len(octets) != 4:
                return value  # Wrong Pattern
            for o in octets:
                if not o.isdigit() or not (0 <= int(o) <= 255):
                    return value  # Wrong Pattern — out of range
            return '.'.join(str(rng.randint(1, 254)) for _ in octets)

        else:
            return value  # Wrong Pattern — not IP format

    except:
        return '***REDACTED***'

def mask_handle(value):
    """Mask social media handle — detect format — digits only is Wrong Pattern"""
    if is_empty_value(value): return value
    if isinstance(value, bool): return value
    try:
        s = str(value).strip()
        # Digits only — not a valid handle
        inner = s.replace('@', '')
        if not any(c.isalpha() for c in inner):
            return value  # Wrong Pattern — return as-is

        if s.startswith('@'):
            parts = re.split(r'[_\-\.]+', inner)
            name_parts = [p for p in parts if p.isalpha() and len(p) >= 2]
            seed_val = name_parts[0] if name_parts else inner
            masked = FIRST_NAME_POOL[get_seed(seed_val) % len(FIRST_NAME_POOL)]
            return f'@{masked.lower()}'

        masked = FIRST_NAME_POOL[get_seed(s) % len(FIRST_NAME_POOL)]
        return masked.lower()

    except:
        return '***REDACTED***'



def mask_generic(value):
    if is_empty_value(value):
        return value
    if isinstance(value, bool): return value
    return '***REDACTED***'

##MASK_FUNCTIONS Registry
MASK_FUNCTIONS = {
    'mask_name'    : mask_name,
    'mask_email'   : mask_email,
    'mask_phone'   : mask_phone,
    'mask_ssn'     : mask_ssn,
    'mask_pan'     : mask_pan,
    'mask_aadhaar' : mask_aadhaar,
    'mask_passport': mask_passport,
    'mask_number'  : mask_number,
    'mask_dob'     : mask_dob,
    'mask_address' : mask_address,
    'mask_city'    : mask_city,
    'mask_country' : mask_country,
    'mask_ip'      : mask_ip,
    'mask_url'     : mask_url,
    'mask_handle'  : mask_handle,
    'mask_postal'  : mask_postal,
    'mask_partial' : mask_partial,
    'mask_alphanumeric': mask_alphanumeric,
    'mask_generic' : mask_generic,
}

##mask_json — Core Masking
def mask_json(doc, approved_fields):
    """Mask JSON doc — approved_fields: {normalised_key: mask_function_name}"""
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            norm_key = normalise_key(key)
            fn_name  = approved_fields.get(norm_key)
            fn       = MASK_FUNCTIONS.get(fn_name, mask_generic) if fn_name else None

            if fn and isinstance(value, list):
                # PII key with list value — mask each item
                masked_list = []
                for item in value:
                    if item is None:
                        masked_list.append(None)
                    elif isinstance(item, bool):
                        masked_list.append(item)
                    elif isinstance(item, dict):
                        masked_list.append(mask_json(item, approved_fields))
                    else:
                        masked_list.append(fn(item))
                result[key] = masked_list

            elif fn:
                # PII leaf value — mask
                result[key] = fn(value)

            elif isinstance(value, (dict, list)):
                # Not PII — recurse into nested structure
                result[key] = mask_json(value, approved_fields)

            else:
                # Not PII leaf — keep unchanged
                result[key] = value

        return result

    elif isinstance(doc, list):
        return [mask_json(item, approved_fields)
                if isinstance(item, dict) else item
                for item in doc]

    return doc

