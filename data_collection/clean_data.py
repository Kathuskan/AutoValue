from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit
import hashlib
import html
import json
import re
import unicodedata
import numpy as np
import pandas as pd
from IPython.display import display

def locate_folder():
    here = Path.cwd().resolve()
    candidates = [here, here / 'data_collection', here / 'AutoValue/data_collection']
    if '__file__' in globals():
        candidates.insert(0, Path(__file__).resolve().parent)
    return next(p for p in candidates if (p / 'ikman_vehicle_data.csv').exists())

BASE = locate_folder()
AUDIT = BASE / 'cleaning_audit'
AUDIT.mkdir(exist_ok=True)
AS_OF_DATE = date(2026, 9, 27)
INPUT_NAMES = ['ikman_vehicle_data.csv', 'ikman_vehicle_data_1.csv', 'ikman_vehicle_data_2.csv']
OLD_PATH = BASE.parent / 'data/raw/car_price_dataset.csv'
SOURCE_COLUMNS = ['Brand', 'Model', 'Manufacture Year', 'Engine Capacity', 'Transmission',
                  'Fuel Type', 'Condition', 'Mileage', 'Asking Price', 'Publication Date', 'URL']
FEATURES = ['Brand', 'Model', 'YOM', 'Engine (cc)', 'Gear', 'Fuel Type', 'Millage(KM)']
CORE = FEATURES + ['Price']

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

input_hashes = {name: sha256(BASE / name) for name in INPUT_NAMES}
old_hash = sha256(OLD_PATH)
old = pd.read_csv(OLD_PATH)
frames = []
for name in INPUT_NAMES:
    frame = pd.read_csv(BASE / name, dtype='string', keep_default_na=False)
    frame.columns = [html.unescape(c).strip().strip('*').strip() for c in frame.columns]
    if set(frame.columns) != set(SOURCE_COLUMNS):
        raise ValueError(f'Unexpected columns in {name}: {frame.columns.tolist()}')
    frame = frame[SOURCE_COLUMNS].copy()
    frame['Source File'] = name
    frame['Source Row'] = np.arange(2, len(frame) + 2)  # CSV header is row 1
    frames.append(frame)
raw = pd.concat(frames, ignore_index=True)
raw.to_csv(BASE / 'merged_raw.csv', index=False)
display(raw.groupby('Source File').size().rename('Rows').to_frame())
display(raw.head(5))
print(f'Total source rows: {len(raw):,}')


# %% [markdown]
# ## Inspect the source values
# Empty values, duplicate rows, and duplicate listing URLs are checked separately.
# %%

missing_tokens = {'', 'N/A', 'NA', 'NULL', 'NONE', 'NAN', '-', 'NOT SPECIFIED'}
def text(value):
    s = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', html.unescape(str(value)))).strip()
    return '' if s.upper() in missing_tokens else s

missing_before = pd.DataFrame({c: raw[c].map(text).eq('').sum() for c in SOURCE_COLUMNS}, index=['Missing']).T
display(missing_before)
print('Exact duplicate rows:', raw.duplicated(SOURCE_COLUMNS).sum())
print('Repeated raw URLs:', raw.duplicated('URL').sum())
display(pd.crosstab(raw['Condition'], raw['Fuel Type']))


# %% [markdown]
# ## Normalize names, units, and dates
# Price is converted from rupees to lakhs by dividing by 100,000. Mileage stays in
# advertised kilometres. Publication dates without a year remain unknown.
# URL is used internally for deduplication but is excluded from the final CSV.
# %%
def upper(value):
    return text(value).upper()

def model_key(value):
    return re.sub(r'[^A-Z0-9]', '', upper(value))

brand_aliases = {'LAND ROVER': 'LAND-ROVER', 'MERCEDES BENZ': 'MERCEDES-BENZ'}
model_lookup = {}
for (brand, key), group in old.assign(_brand=old.Brand.map(upper), _key=old.Model.map(model_key)).groupby(['_brand', '_key']):
    options = set(group.Model.map(upper))
    if len(options) == 1:
        model_lookup[(brand, key)] = next(iter(options))

NUMBER = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
def parse_number(value, unit):
    s = text(value)
    patterns = {'year': r'(\d{4})', 'cc': rf'({NUMBER})\s*cc',
                'km': rf'({NUMBER})\s*km', 'lkr': rf'(?:Rs\.?|LKR)\s*({NUMBER})'}
    match = re.fullmatch(patterns[unit], s, flags=re.I)
    return float(match.group(1).replace(',', '')) if match else np.nan

def canonical_url(value):
    try:
        parts = urlsplit(text(value))
        if (parts.scheme not in {'http', 'https'} or parts.hostname != 'ikman.lk'
                or parts.username or parts.password or parts.port not in {None, 80, 443}
                or not parts.path.startswith('/en/ad/') or parts.path == '/en/ad/'):
            return ''
        return urlunsplit(('https', 'ikman.lk', parts.path.rstrip('/'), '', ''))
    except ValueError:
        return ''

d = pd.DataFrame(index=raw.index)
d['Brand'] = raw.Brand.map(upper).replace(brand_aliases)
d['Model'] = [model_lookup.get((b, model_key(m)), upper(m)) for b, m in zip(d.Brand, raw.Model)]
d['YOM'] = raw['Manufacture Year'].map(lambda v: parse_number(v, 'year'))
d['Engine (cc)'] = raw['Engine Capacity'].map(lambda v: parse_number(v, 'cc'))
d['Gear'] = raw.Transmission.map(upper)
d['Fuel Type'] = raw['Fuel Type'].map(upper)
d['Millage(KM)'] = raw.Mileage.map(lambda v: parse_number(v, 'km'))
d['Price LKR'] = raw['Asking Price'].map(lambda v: parse_number(v, 'lkr'))
d['Price'] = d['Price LKR'] / 100000
d['Condition'] = raw.Condition.map(upper).replace({'BRAND NEW': 'NEW'})
d['URL'] = raw.URL.map(canonical_url)
d['Publication Date Raw'] = raw['Publication Date'].map(text)

def explicit_date(value):
    s = text(value)
    # Never let a date parser supply a missing year, day, or month.
    for fmt in ['%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%d %b %Y %I:%M %p']:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ''

d['Date'] = d['Publication Date Raw'].map(explicit_date)
d['Date Status'] = np.where(d.Date.eq(''), 'unknown_publication_year_or_format', 'explicit_publication_date')
d['Data Source'] = 'ikman_user_scrape'
d['Mileage Source'] = 'advertised_km'
d['Source File'] = raw['Source File']
d['Source Row'] = raw['Source Row']
d['Record ID'] = [hashlib.sha256((u or f'{f}:{r}').encode()).hexdigest()[:20]
                  for u, f, r in zip(d.URL, d['Source File'], d['Source Row'])]
display(d[CORE + ['Condition', 'Date', 'Date Status']].head())
display(d[['YOM', 'Engine (cc)', 'Millage(KM)', 'Price']].describe())

# %% [markdown]
# ## Consolidate repeated listing URLs
# Preserve source references and all observed date text. Different URLs with matching
# profiles remain separate records and share a profile grouping key for later evaluation.
# %%
FACTS = CORE + ['Condition', 'Price LKR']
groups = []
conflicting_ids = set()
for record_id, group in d.groupby('Record ID', sort=False):
    representative = group.iloc[0].copy()
    if len(group[FACTS].drop_duplicates()) > 1:
        conflicting_ids.add(record_id)
    dates = sorted(set(group['Date']) - {''})
    if len(dates) > 1:
        representative['Date'] = ''
        representative['Date Status'] = 'conflicting_explicit_dates'
    elif len(dates) == 1:
        representative['Date'] = dates[0]
        representative['Date Status'] = 'explicit_publication_date'
    representative['Source Files'] = '; '.join(sorted(group['Source File'].unique()))
    representative['Source References'] = json.dumps(
        [{'file': r['Source File'], 'row': int(r['Source Row'])} for _, r in group.iterrows()])
    representative['Publication Date Observations'] = json.dumps(sorted(set(group['Publication Date Raw'])))
    representative['Observation Count'] = len(group)
    groups.append(representative)
unique = pd.DataFrame(groups).reset_index(drop=True)
unique['Profile Group'] = pd.util.hash_pandas_object(unique[FEATURES], index=False).astype(str)
unique['Similar Profile Count'] = unique.groupby('Profile Group')['Record ID'].transform('size')
print(f'Unique listings: {len(unique):,}; redundant URL observations: {len(d) - len(unique):,}')
print('Listings with conflicting vehicle/price fields:', len(conflicting_ids))
print('Listings with a matching profile at another URL:', unique['Similar Profile Count'].gt(1).sum())

# %% [markdown]
# ## Exclude flagged listings
# Check missing or generic inputs, implausible price/unit values, ambiguous electric
# engine capacities, suspect mileage, and conflicting observations. These rules use
# the original condition labels; changing condition later does not restore excluded rows.
# The exclusion audit preserves the reasons. It is not part of the prepared dataset.
# %%
def quality(row):
    reasons = []
    warnings = []
    for col in CORE:
        value = row[col]
        if pd.isna(value) or (isinstance(value, str) and not value):
            reasons.append('missing_or_unparsed_' + col)
    if row['Brand'] in {'OTHER BRAND', 'OTHER'} or row['Model'] in {'OTHER MODEL', 'OTHER'}:
        reasons.append('generic_brand_or_model')
    if not row['URL']:
        reasons.append('invalid_listing_url')
    if row['Record ID'] in conflicting_ids:
        reasons.append('conflicting_observations')
    if pd.notna(row.YOM) and not (1886 <= row.YOM <= AS_OF_DATE.year and row.YOM.is_integer()):
        reasons.append('year_outside_supported_range')
    if pd.notna(row['Price LKR']) and row['Price LKR'] < 100000:
        reasons.append('price_below_100000_lkr_check_units_or_placeholder')
    engine = row['Engine (cc)']
    if pd.notna(engine):
        if row['Fuel Type'] == 'ELECTRIC' and engine != 0:
            reasons.append('electric_nonzero_cc_ambiguous_unit')
        elif row['Fuel Type'] != 'ELECTRIC' and not 200 <= engine <= 8000:
            reasons.append('engine_cc_outside_screening_range')
    mileage = row['Millage(KM)']
    if pd.notna(mileage):
        if not 0 <= mileage <= 3000000:
            reasons.append('mileage_outside_supported_range')
        if row.Condition in {'USED', 'RECONDITIONED'}:
            if mileage == 0:
                reasons.append('zero_mileage_used_or_reconditioned')
            elif pd.notna(row.YOM) and AS_OF_DATE.year - row.YOM >= 3 and mileage <= 100:
                reasons.append('very_low_mileage_older_vehicle_check_units')
        if row.Condition == 'NEW' and mileage > 1000:
            warnings.append('new_condition_with_mileage_above_1000')
    if row.Gear not in {'AUTOMATIC', 'MANUAL', 'TIPTRONIC'}:
        reasons.append('unrecognized_transmission')
    if row['Fuel Type'] not in {'PETROL', 'DIESEL', 'HYBRID', 'ELECTRIC'}:
        reasons.append('unrecognized_fuel')
    if row.Condition not in {'USED', 'NEW', 'RECONDITIONED', 'IMPORT'}:
        reasons.append('unrecognized_condition')
    if not row.Date:
        warnings.append(row['Date Status'])
    elif date.fromisoformat(row.Date) > AS_OF_DATE:
        reasons.append('publication_date_in_future')
    if row.Condition == 'IMPORT':
        warnings.append('import_does_not_establish_used_or_new')
    if row['Similar Profile Count'] > 1:
        warnings.append('matching_profile_at_another_url_keep_grouped')
    if re.search(r'(?:down-payment|monthly-payment|lease-rental|finance-only)', row.URL, re.I):
        reasons.append('possible_finance_amount_in_url')
    return '; '.join(reasons), '; '.join(warnings)

checks = unique.apply(quality, axis=1)
unique['Review Reasons'] = [x[0] for x in checks]
unique['Data Warnings'] = [x[1] for x in checks]
clean = unique.loc[unique['Review Reasons'].eq('')].copy()
review = unique.loc[unique['Review Reasons'].ne('')].copy()
reason_counts = review['Review Reasons'].str.split('; ').explode().value_counts().rename_axis('Reason').to_frame('Listings')
display(reason_counts)
print(f'Accepted listings: {len(clean):,}; excluded flagged listings: {len(review):,}')

# %% [markdown]
# ## Apply the requested condition rules
# RECONDITIONED becomes USED. IMPORT becomes USED if mileage is greater than zero,
# otherwise NEW (zero or missing mileage). Missing required mileage still fails the
# earlier quality check, so this rule never invents a mileage value or restores a row.
# This is the requested classification rule, not independent verification of condition.
# All original condition labels remain available in the source-row audit.
# %%
def final_condition(condition, mileage):
    if condition == 'RECONDITIONED':
        return 'USED'
    if condition == 'IMPORT':
        return 'USED' if pd.notna(mileage) and mileage > 0 else 'NEW'
    return condition

condition_changes = clean[['Record ID', 'Condition', 'Millage(KM)']].copy()
condition_changes = condition_changes.rename(columns={'Condition': 'Original Condition'})
clean['Condition'] = [final_condition(c, m) for c, m in zip(clean.Condition, clean['Millage(KM)'])]
condition_changes['Final Condition'] = clean['Condition']
clean['Data Warnings'] = clean['Data Warnings'].map(lambda value: '; '.join(
    w for w in value.split('; ') if w != 'import_does_not_establish_used_or_new'))
condition_changes.to_csv(AUDIT / 'condition_changes.csv', index=False)
display(pd.crosstab(condition_changes['Original Condition'], condition_changes['Final Condition']))

# %% [markdown]
# ## Compare with the old dataset
# Do not merge or retrain here. The old mileage is age-derived, and training currently
# assumes 2025. A later training task must handle these differences and unknown dates.
# %%
old_normal = old.copy()
for col in ['Brand', 'Model', 'Gear', 'Fuel Type']:
    old_normal[col] = old_normal[col].map(upper)
old_groups = pd.util.hash_pandas_object(old_normal[FEATURES].astype(
    {'YOM': float, 'Engine (cc)': float, 'Millage(KM)': float}), index=False).astype(str)
clean['Profile Matches Old Dataset'] = clean['Profile Group'].isin(set(old_groups))
old_derived_mileage = bool(np.allclose(old['Millage(KM)'], (2025 - old.YOM) * 11000))
comparison = pd.DataFrame({
    'Measure': ['Rows', 'Minimum manufacture year', 'Maximum manufacture year',
                'Median price (lakhs)', 'Median mileage (km)', 'Dates missing a confirmed year'],
    'Existing raw': [len(old), old.YOM.min(), old.YOM.max(), old.Price.median(),
                     old['Millage(KM)'].median(), old.Date.isna().sum()],
    'New accepted': [len(clean), clean.YOM.min(), clean.YOM.max(), clean.Price.median(),
                     clean['Millage(KM)'].median(), clean.Date.eq('').sum()]})
display(comparison)
display(clean.Condition.value_counts().rename('Accepted listings').to_frame())
print('Old mileage follows the age formula for every row:', old_derived_mileage)
print('New accepted profiles also present in old data:', clean['Profile Matches Old Dataset'].sum())


# %% [markdown]
# ## Export the prepared CSV
# Only accepted listings are exported, with USED/NEW condition labels and no URL column.
# Audit files retain the original evidence and excluded records separately.
# Price LKR and provenance fields are metadata, not model inputs (Price LKR leaks the target).
# %%
def export_date(value):
    """Preserve explicit years; use the user's requested 2026 for yearless dates."""
    known = explicit_date(value)
    if known:
        return known
    for fmt in ['%d %b %I:%M %p %Y', '%d %B %I:%M %p %Y', '%d %b %Y', '%d %B %Y']:
        try:
            return datetime.strptime(text(value) + ' 2026', fmt).date().isoformat()
        except ValueError:
            pass
    return ''

META = ['Condition', 'Date']
final = clean[CORE + META].copy()
# Apply the requested year assumption only at export, preserving quality exclusions.
# The source text remains unchanged; duplicate observations use the first source row.
final['Date'] = clean['Publication Date Raw'].map(export_date)
if final['Date'].eq('').any():
    raise ValueError('Some publication dates cannot be parsed; inspect the source text.')
for col in ['YOM', 'Engine (cc)', 'Millage(KM)']:
    if (final[col].dropna() % 1 == 0).all():
        final[col] = final[col].astype('Int64')
final.to_csv(BASE / 'cleaned_new_data.csv', index=False)
review.to_csv(AUDIT / 'needs_review.csv', index=False)
decisions = unique[['Record ID', 'Review Reasons', 'Data Warnings', 'Observation Count']].copy()
decisions['Decision'] = np.where(decisions['Review Reasons'].eq(''), 'accepted', 'needs_review')
lineage = raw.copy()
lineage['Record ID'] = d['Record ID']
lineage = lineage.merge(decisions, on='Record ID', how='left', validate='many_to_one')
lineage['Repeated URL Observation'] = lineage['Record ID'].duplicated()
lineage.to_csv(AUDIT / 'source_row_audit.csv', index=False)
reason_counts.to_csv(AUDIT / 'review_reason_counts.csv')
comparison.to_csv(AUDIT / 'old_new_comparison.csv', index=False)
unique[unique['Similar Profile Count'].gt(1)].to_csv(AUDIT / 'matching_profiles.csv', index=False)

summary = {
    'cleaning_reference_date': AS_OF_DATE.isoformat(),
    'input_rows_by_file': {f['Source File'].iloc[0]: len(f) for f in frames},
    'total_input_rows': len(raw),
    'exact_duplicate_rows': int(raw.duplicated(SOURCE_COLUMNS).sum()),
    'redundant_url_observations': len(raw) - len(unique),
    'unique_listings': len(unique), 'accepted_listings': len(final),
    'review_listings': len(review), 'excluded_flagged_listings': len(review),
    'conflicting_fact_urls': len(conflicting_ids),
    'condition_rule': 'RECONDITIONED -> USED; IMPORT -> USED if mileage > 0, otherwise NEW',
    'url_in_final_csv': False,
    'export_date_rule': 'YYYY-MM-DD; missing publication year assumed 2026 at user request',
    'accepted_assumed_publication_year': int(clean.Date.eq('').sum()),
    'accepted_unknown_publication_date': int(final.Date.eq('').sum()),
    'accepted_2026_vehicles': int(final.YOM.eq(2026).sum()),
    'accepted_condition_counts': final.Condition.value_counts().to_dict(),
    'review_reason_counts': reason_counts.Listings.to_dict(),
    'price_unit': 'LKR lakhs (100000 rupees)',
    'old_mileage_is_age_derived': old_derived_mileage,
    'publication_coverage_confirmed': False,
    'existing_dataset_merged': False, 'model_retrained': False,
    'source_sha256': input_hashes, 'old_dataset_sha256': old_hash,
}
(AUDIT / 'cleaning_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
display(pd.DataFrame({'Stage': ['Input rows', 'Repeated URL observations removed',
                               'Unique listings', 'Excluded flagged listings', 'Accepted CSV rows'],
                      'Rows': [len(raw), len(raw)-len(unique), len(unique), len(review), len(final)]}))

# %% [markdown]
# ## Verify saved results
# Check units, complete row accounting, exclusion of every flagged listing, requested
# condition mapping, absence of URL, and unchanged source files.
# %%
saved = pd.read_csv(BASE / 'cleaned_new_data.csv', keep_default_na=False)
assert set(CORE).issubset(saved.columns)
assert not saved[CORE].isna().any().any()
assert not saved[CORE].eq('').any().any()
assert saved.columns.tolist() == CORE + META
assert clean['Record ID'].is_unique
assert saved.Date.str.fullmatch(r'\d{4}-\d{2}-\d{2}').all()
pd.to_datetime(saved.Date, format='%Y-%m-%d', errors='raise')
assert clean.URL.is_unique
assert set(saved.Condition) <= {'USED', 'NEW'}
assert final_condition('RECONDITIONED', 30000) == 'USED'
assert final_condition('IMPORT', 1) == 'USED'
assert final_condition('IMPORT', 0) == 'NEW'
assert final_condition('IMPORT', np.nan) == 'NEW'
expected_conditions = [final_condition(c, m) for c, m in zip(
    condition_changes['Original Condition'], condition_changes['Millage(KM)'])]
assert saved.Condition.tolist() == expected_conditions
assert np.allclose(saved.Price * 100000, clean['Price LKR'])
assert saved.YOM.between(1886, AS_OF_DATE.year).all()
assert saved['Millage(KM)'].between(0, 3000000).all()
assert len(raw) == len(raw) - len(unique) + len(final) + len(review)
assert len(lineage) == len(raw) and lineage.Decision.notna().all()
assert set(clean['Record ID']).isdisjoint(set(review['Record ID']))
assert input_hashes == {name: sha256(BASE / name) for name in INPUT_NAMES}
assert sha256(OLD_PATH) == old_hash
assert parse_number('Rs 8,875,000', 'lkr') / 100000 == 88.75
assert parse_number('97,000 km', 'km') == 97000
assert np.isnan(parse_number('97,000 miles', 'km'))
assert np.isnan(parse_number('Rs 10,000 monthly', 'lkr'))
assert np.isnan(parse_number('48 kWh', 'cc'))
assert explicit_date('26 Sep 2:52 am') == ''
assert explicit_date('2025-02-05') == '2025-02-05'
assert export_date('26 Sep 2:52 am') == '2026-09-26'
assert export_date('2024-12-21') == '2024-12-21'
assert canonical_url('https://ikman.lk/en/ad/example?tracking=1#section') == 'https://ikman.lk/en/ad/example'
assert canonical_url('https://example.com/en/ad/car') == ''
print('All checks passed. Source files and existing dataset are unchanged.')
print('Saved:', BASE / 'cleaned_new_data.csv')
display(saved.head(5)[CORE + ['Condition', 'Date']])
