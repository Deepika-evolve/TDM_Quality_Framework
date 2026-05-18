import os, hashlib, shutil, logging,json,re
import pandas as pd
import stat
import jm_config as config
from datetime import datetime
from QualityEngine import normalise_key
logger = logging.getLogger(__name__)


# ── Hash Functions ───────────────────────────────────────────────
def hash_dataframe(df):
    return hashlib.sha256(df.to_json(orient='records').encode()).hexdigest()

def hash_folder_contents(folder_path):
    """Hash contents of all JSON JSONL TXT files in folder"""
    import hashlib
    from pathlib import Path
    hasher = hashlib.md5()
    supported = ['.json', '.jsonl', '.txt']
    for filepath in sorted(Path(folder_path).iterdir()):
        if filepath.suffix.lower() not in supported:
            continue
        try:
            hasher.update(filepath.name.encode())
            hasher.update(filepath.read_bytes())
        except Exception as e:
            logger.warning(f'Could not hash {filepath.name}: {e}')
    return hasher.hexdigest()


def save_hash(hash_val, hash_file):
    with open(hash_file, 'w') as f: f.write(hash_val)
    logger.info('Hash stored')

def load_hash(hash_file):
    if not os.path.exists(hash_file):return None
    with open(hash_file) as f: return f.read()

def make_readonly(filepath):
    """Make file read only — tamper protection for archives"""
    try:
        os.chmod(filepath, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except Exception as e:
        logger.warning(f'Could not set read-only: {e}')

# ── Archive ──────────────────────────────────────────────────────
def archive_hash_audit(hash_audit_file, archive_dir, project_id=''):
    os.makedirs(archive_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    prefix = f'{project_id}_' if project_id else ''
    dest = os.path.join(archive_dir, f'{prefix}hash_audit_{ts}.xlsx')
    shutil.copy(hash_audit_file, dest)
    make_readonly(dest)
    logger.info(f'Archived: {prefix}hash_audit_{ts}.xlsx')


# ── Validation Layer — Gatekeeper ────────────────────────────────
def validate_audit(approved_df, original_df):
    """Validate approved audit sheet — all checks must pass"""
    try:
        errors = []

        # Step 1 — Skip container rows
        leaf_df     = approved_df[approved_df['is_pii'] != 'container'].copy()
        original_df = original_df[original_df['is_pii'] != 'container'].copy()

        # Step 2 — Block global scope — tool managed only
        global_scope = leaf_df[
            leaf_df['scope'].fillna('').str.strip().isin(['global_pii', 'global_not_pii'])
        ]
        if not global_scope.empty:
            errors.append(
                f'Global scope not allowed — use project_pii or project_not_pii: '
                f'{global_scope["path"].tolist()}'
            )

        # Step 3 — ALL fields must be explicitly approved
        # Both Yes and No must be approved — no silent skips allowed
        not_approved = leaf_df[
            leaf_df['approved'].fillna('').str.upper() != 'YES'
        ]['path'].tolist()
        if not_approved:
            errors.append(
                f'All fields must be approved before masking: {not_approved}'
            )

        # Step 4 — Override must have reason
        merged = leaf_df.merge(
            original_df[['path', 'is_pii']].rename(columns={'is_pii': 'is_pii_orig'}),
            on='path', how='left'
        )
        overrides_no_reason = merged[
            (merged['is_pii'] != merged['is_pii_orig']) &
            (merged['reason'].fillna('').str.strip() == '')
        ]['path'].tolist()
        if overrides_no_reason:
            errors.append(f'Reason missing for overrides: {overrides_no_reason}')

        # Step 5 — Approved fields must have approver name
        approved_no_name = leaf_df[
            (leaf_df['approved'].fillna('').str.upper() == 'YES') &
            (leaf_df['approved_by'].fillna('').str.strip().str.match(r'^(null|none|na|n/a|nan|undefined|unknown|unavailable)?$'))
        ]['path'].tolist()
        if approved_no_name:
            errors.append(f'Approver name missing: {approved_no_name}')

        # Step 6 — No unresolved fields
        unresolved = leaf_df[
            leaf_df['is_pii'] == '?'
        ]['path'].tolist()
        if unresolved:
            errors.append(f'Unresolved fields — resolve before masking: {unresolved}')

        # Step 7 — Hard block — known PII cannot go to global exclusion
        no_pii_global = leaf_df[
            (leaf_df['is_pii'].str.upper() == 'NO') &
            (leaf_df['scope'].fillna('').str.strip() == 'global_not_pii')
        ]
        for _, row in no_pii_global.iterrows():
            if not validate_exclusion_addition(row['key'], config.STANDARD_CLASSIFIER):
                errors.append(
                    f"Cannot exclude known PII field: {row['key']} — "
                    f"use project_not_pii instead"
                )
    except ValueError:
        raise  # re-raise for main to catch
    except Exception as e:
        logger.error(f'Unexpected error in validate_audit: {e}')
        raise
    return errors


# ── Generate Hash Audit — only after validation passes ────────────
def generate_hash_audit(approved_df, original_df, hash_audit_file, hash_file, archive_dir):
    """Merge mask_function from original — save hash_audit with all columns"""
    # Merge mask_function and rule back from original
    try:
        internal_cols = original_df[['path', 'mask_function', 'rule']].drop_duplicates(subset='path').copy()
        full_df = approved_df.merge(internal_cols, on='path', how='left')
        full_df.to_excel(hash_audit_file, index=False)
        hash_df=pd.read_excel(hash_audit_file)
        h = hash_dataframe(full_df)
        save_hash(h, hash_file)
        archive_hash_audit(hash_audit_file, archive_dir)
        logger.info('hash_audit.xlsx generated and archived')
    ##print(f"h {h}")
    except ValueError:
        raise  # re-raise for main to catch
    except Exception as e:
        logger.error(f'Unexpected error in generate_hash_audit: {e}')
        raise
    return h,hash_df


# ── Verify Hash Before Masking ────────────────────────────────────
def verify_hash_audit(hash_audit_file, hash_file):
    """Verify hash_audit not tampered — return True if valid"""
    df = pd.read_excel(hash_audit_file)
    current = hash_dataframe(df)
    stored  = load_hash(hash_file)
    if stored==None:
        logger.error('Hash file not found - Audit integrity cannot be verified - re-run from approval step to regenerate hash file')
        return False, df
    if current != stored:
        logger.error('Hash mismatch — hash_audit may be tampered')
        return False, df
    logger.info('Hash verified — hash_audit intact')
    return True, df


# ── Get Approved Fields for Masking ──────────────────────────────
def get_approved_fields(hash_audit_df):
    approved = hash_audit_df[
        (hash_audit_df['is_pii'].str.upper() == 'YES') &
        (hash_audit_df['approved'].str.upper() == 'YES')&
        (hash_audit_df['is_pii'].str.upper() != 'container')
    ]
    result = {}
    for _, row in approved.iterrows():
        key = str(row['key']).strip().lower()
        fn  = str(row.get('mask_function', '')).strip()
        if fn in ['', 'nan', 'None']:
            fn = 'mask_generic'
        result[key] = fn
    return result

def remove_from_project_pii(key, project):
    """Remove field from project_pii groups if present"""
    to_delete = []
    for group_name, rules in project.get('project_pii', {}).items():
        if not isinstance(rules, dict): continue
        fields = [normalise_key(f) for f in rules.get('fields', [])]
        if key in fields:
            to_delete.append(group_name)
    for group_name in to_delete:
        del project['project_pii'][group_name]
        logger.info(f'Removed {key} from project_pii: {group_name}')
    return project

def remove_from_project_not_pii(key, project):
    """Remove field from project_not_pii if present"""
    if key in project.get('project_not_pii', {}):
        del project['project_not_pii'][key]
        logger.info(f'Removed {key} from project_not_pii')
    return project

##Routes decisions to correct classifier based on scope
def save_decisions(approved_df, project_path, exclusion_path):
    """Save user decisions to project classifier only — standard is read only"""
    with open(project_path)   as f: project    = json.load(f)
    with open(exclusion_path) as f: exclusions = json.load(f)

    today = str(datetime.now().date())
    user_rows = approved_df[approved_df['approved'].fillna('').str.upper()== 'YES'].copy()

    for _, row in user_rows.iterrows():
        key        = normalise_key(str(row['key']))
        scope      = str(row.get('scope',  '')).strip()
        is_pii     = str(row.get('is_pii', '')).strip().upper()
        reason     = str(row.get('reason', '')).strip()
        decided_by = str(row.get('approved_by', '')).strip()
        fn         = str(row.get('mask_function', 'mask_generic')).strip()
        if fn in ['', 'nan', 'None']: fn = 'mask_generic'
        logger.info(f"inside save decisions| key:{key} ispii:{is_pii}|scope :{scope}")
        if is_pii == 'YES' and scope == 'project_pii':
            # Remove from project_not_pii first if previously there
            logger.info(f"inside save decisions project pii {scope}")
            project = remove_from_project_not_pii(key, project)
            entry = {'fields': [key], 'mask_function': fn,
                     'decided_by': decided_by, 'decided_on': today}
            project.setdefault('project_pii', {})[f'{key}_group'] = entry
            logger.info(f'Saved to project_pii|Accountability lies with the approver: {key}')

        elif is_pii == 'NO' and scope == 'project_not_pii':
            # Remove from project_pii first if previously there
            logger.info(f"inside save decisions projectnot pii {scope}")
            project = remove_from_project_pii(key, project)
            project.setdefault('project_not_pii', {})[key] = {
                'reason': reason,
                'decided_by': decided_by,
                'decided_on': today
            }
            logger.info(f'Saved to project_not_pii|Accountability lies with the approver: {key}')

        elif is_pii == 'NO' and scope == 'global_not_pii':
            # global_not_pii → exclusion_list only — not standard.json
            excl = exclusions.setdefault('exclude_fields', {})
            if isinstance(excl, list):
                excl_dict = {f: {'reason': 'system default', 'decided_by': 'system', 'decided_on': today} for f in excl}
                exclusions['exclude_fields'] = excl_dict
            exclusions['exclude_fields'][key] = {
                'reason': reason, 'decided_by': decided_by, 'decided_on': today
            }
            logger.info(f'Saved to exclusion: {key}')

    # Only write project and exclusion — NEVER standard
    with open(project_path,   'w') as f: json.dump(project,    f, indent=2)
    with open(exclusion_path, 'w') as f: json.dump(exclusions, f, indent=2)
    logger.info('User decisions saved — standard classifier unchanged')

def validate_exclusion_addition(field, standard_path):
    """Block adding known PII fields to exclusion — sensitive data protection"""
    try:
        with open(standard_path) as f: standard = json.load(f)
        norm = normalise_key(field)
        for group, rules in standard.get('global_pii', {}).items():
            if isinstance(rules, dict):
                if norm in [normalise_key(f) for f in rules.get('fields', [])]:
                    logger.error(
                        f'BLOCKED: {field} is a GDPR PII field — '
                        f'cannot add to exclusion — sensitive data would be exposed'
                    )
                    return False
        return True
    except Exception as e:
        logger.warning(f'Exclusion validation failed: {e}')
        return True


def dedup_classifier(classifier_path, section_key):
    """Remove duplicate fields across groups in classifier section"""
    try:
        with open(classifier_path) as f: data = json.load(f)

        section = data.get(section_key, {})
        if not isinstance(section, dict):
            return  # exclusion_list may be list format — skip

        seen_fields = set()
        clean_section = {}

        for group_name, rules in section.items():
            if group_name == 'comment': continue
            if not isinstance(rules, dict): continue

            clean_fields = []
            for field in rules.get('fields', []):
                norm = normalise_key(field)
                if norm not in seen_fields:
                    clean_fields.append(field)
                    seen_fields.add(norm)

            if clean_fields:
                rules['fields'] = clean_fields
                clean_section[group_name] = rules

        data[section_key] = clean_section
        with open(classifier_path, 'w') as f: json.dump(data, f, indent=2)
        logger.info(f'Deduplicated {section_key} in {classifier_path}')

    except Exception as e:
        logger.warning(f'Dedup failed for {classifier_path}: {e}')

# ── Restart ───────────────────────────────────────────────────────
def clear_for_restart(files_to_clear):
    """Clear previous approval — explicit restart only"""
    for f in files_to_clear:
        if os.path.exists(f):
            os.remove(f)
            logger.info(f'Cleared: {f}')
    logger.info('Restart — previous approval cleared')


def hash_input_data(filepath):
    """Hash input file data content only- ignores excel metadata"""
    df=pd.read_excel(filepath)
    content=df.to_json(orient='records')
    return hashlib.sha256(content.encode()).hexdigest()

def input_file_changed(input_file, input_hash_file):
    """Returns True if input file changed since last run"""
    if not os.path.exists(input_hash_file):
        return True  # first run — always fresh
    current  = hash_input_data(input_file)
    stored   = load_hash(input_hash_file)
    if current != stored:
        logger.info('Input file content changed — PII Analysis in progress')
        return True
    return False
