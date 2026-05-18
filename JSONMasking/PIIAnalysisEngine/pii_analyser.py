import json
import hashlib
import logging
import pandas as pd
from QualityEngine import *
import jm_config as config
logger = logging.getLogger(__name__)

def load_classifier(standard_path, project_path, exclusion_path):
    """Load classifiers in correct priority order"""
    with open(standard_path)  as f: standard   = json.load(f)
    with open(project_path)   as f: project    = json.load(f)
    with open(exclusion_path) as f: exclusions = json.load(f)

    # Step 1 — Exclusion list — exact match only — hard stop
    excl = exclusions.get('exclude_fields', {})
    if isinstance(excl, list):
        exclude_fields = [normalise_key(f) for f in excl]
    else:
        exclude_fields = [normalise_key(k) for k in excl.keys()]

    # Step 2 — Project not_pii — project level hard stop
    # Overrides global PII for this project
    for field in project.get('project_not_pii', {}).keys():
        if field != 'comment':
            exclude_fields.append(normalise_key(field))

    # Step 3 — Project PII — loaded first — overrides global if same group
    pii_fields = {}
    for group, rules in project.get('project_pii', {}).items():
        if group not in ('comment',) and isinstance(rules, dict):
            pii_fields[group] = {**rules, 'source': 'project_pii'}

    # Step 4 — Global PII — loaded after — project decisions take precedence
    for group, rules in standard.get('global_pii', {}).items():
        pii_fields[group] = {**rules, 'source': 'global_pii'}

    return {'pii_fields': pii_fields, 'exclude_fields': exclude_fields}

def _yield_primitive(key, value, path, norm_key, pii_fields, excl_fields):
    """Yield a primitive value — exact match first then fuzzy"""

    # Exclusion list — hard stop
    if norm_key in excl_fields:
        yield {'path': path, 'key': key, 'value': value,
               'is_pii': 'No', 'source': 'exclusion_list',
               'rule': 'excluded', 'mask_function': None}
        return

    # Step 1 — Exact match
    for group, rules in pii_fields.items():
        norm_fields = [normalise_key(f) for f in rules.get('fields', [])]
        if norm_key in norm_fields:
            yield {'path': path, 'key': key, 'value': value,
                   'is_pii': 'Yes', 'source': rules['source'],
                   'rule': group, 'mask_function': rules['mask_function']}
            return

    # Step 2 — Fuzzy match
    for group, rules in pii_fields.items():
        norm_fields = [normalise_key(f) for f in rules.get('fields', [])]
        if any(f in norm_key for f in norm_fields):
            yield {'path': path, 'key': key, 'value': value,
                   'is_pii': 'Yes', 'source': rules['source'],
                   'rule': group, 'mask_function': rules['mask_function']}
            return

    # Step 3 — Unknown
    yield {'path': path, 'key': key, 'value': value,
           'is_pii': '?', 'source': 'unknown',
           'rule': 'review_required', 'mask_function': None}


def analyse_json(doc, classifier, path=''):
    """Recursively traverse JSON — yield all findings"""
    excl_fields = classifier['exclude_fields']
    pii_fields  = classifier['pii_fields']
    if isinstance(doc, dict):
        for key, value in doc.items():
            current_path = f'{path}.{key}' if path else key
            norm_key = normalise_key(key)

            if isinstance(value, dict):
                # Dict value — container — show then recurse
                yield {'path': current_path, 'key': key,
                       'value': '{dict}', 'is_pii': 'container',
                       'source': '-', 'rule': '-', 'mask_function': None}
                yield from analyse_json(value, classifier, current_path)

            elif isinstance(value, list):
                has_dicts = any(isinstance(i, dict) for i in value)

                if has_dicts:
                    # List contains dicts — container
                    yield {'path': current_path, 'key': key,
                           'value': '{list}', 'is_pii': 'container',
                           'source': '-', 'rule': '-', 'mask_function': None}
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            yield from analyse_json(item, classifier,
                                                   f'{current_path}[{i}]')
                        elif item is not None and not isinstance(item, bool):
                            # Primitive in mixed list — check parent key
                            yield from _yield_primitive(
                                key, item, f'{current_path}[{i}]',
                                norm_key, pii_fields, excl_fields)
                else:
                    # Pure primitive array — check parent key
                    # NOT a container — flag PII at each index
                    if norm_key in excl_fields:
                        for i, item in enumerate(value):
                            yield {'path': f'{current_path}[{i}]', 'key': key,
                                   'value': item, 'is_pii': 'No',
                                   'source': 'exclusion_list',
                                   'rule': 'excluded', 'mask_function': None}
                    else:
                        for i, item in enumerate(value):
                            yield from _yield_primitive(
                                key, item, f'{current_path}[{i}]',
                                norm_key, pii_fields, excl_fields)
            else:
                # Leaf value — check exclusion then classifier
                if norm_key in excl_fields:
                    yield {'path': current_path, 'key': key, 'value': value,
                           'is_pii': 'No', 'source': 'exclusion_list',
                           'rule': 'excluded', 'mask_function': None}
                else:
                    matched = False
                    for group, rules in pii_fields.items():
                        norm_fields = [normalise_key(f) for f in rules.get('fields', [])]
                        if norm_key in norm_fields:
                            yield {'path': current_path, 'key': key, 'value': value,
                                   'is_pii': 'Yes', 'source': rules['source'],
                                   'rule': group, 'mask_function': rules['mask_function']}
                            matched = True
                            break
                    if not matched:
                        for group, rules in pii_fields.items():
                            norm_fields = [normalise_key(f) for f in rules.get('fields', [])]
                            if any(f in norm_key for f in norm_fields):
                                yield {'path': current_path, 'key': key, 'value': value,
                                       'is_pii': 'Yes', 'source': rules['source'],
                                       'rule': group, 'mask_function': rules['mask_function']}
                                matched = True
                                break
                    if not matched:
                        yield {'path': current_path, 'key': key, 'value': value,
                               'is_pii': '?', 'source': 'unknown',
                               'rule': 'review_required', 'mask_function': None}

    elif isinstance(doc, list):
        for i, item in enumerate(doc):
            if isinstance(item, dict):
                yield from analyse_json(item, classifier, f'{path}[{i}]')

def generate_audit_sheet(df, json_col, classifier, doc_id_col=None):
    """Generate PII audit sheet from dataframe"""
    rows = []
    for idx, row in df.iterrows():
        try:
            json_str = str(row[json_col])
            doc_id = row[doc_id_col] if doc_id_col else \
                     f'row_{idx+1}_{hashlib.md5(json_str.encode()).hexdigest()[:6]}'
            doc = validate_json_string(json_str, doc_id)
            if doc is None: continue
            # Handle root level list — e.g. [{...}, {...}]
            if isinstance(doc, list):
                for i, item in enumerate(doc):
                    if isinstance(item, dict):
                        for finding in analyse_json(item, classifier, f'[{i}]'):
                            rows.append({
                                'project_id': config.PROJECT_ID,
                                'doc_id': doc_id,
                                **finding,
                                'value': partial_mask_value(clean_value(finding['value']),
                                             show_pii=not config.PARTIAL_MASK_IN_AUDIT),
                                'scope':'',
                                'approved': 'No',
                                'approved_by': '',
                                'reason': ''
                            })
            else:
                for finding in analyse_json(doc, classifier):
                    rows.append({
                        'project_id': config.PROJECT_ID,
                        'doc_id': doc_id,
                        **finding,
                        'value': partial_mask_value(clean_value(finding['value']),
                                                    show_pii=not config.PARTIAL_MASK_IN_AUDIT),
                        'scope': '',
                        'approved': 'No',
                        'approved_by': '',
                        'reason': ''
                    })
        except Exception as e:
            logger.warning(f'Row {idx+1}: Analysis failed — {e} — skipped')
            continue
    return pd.DataFrame(rows)
