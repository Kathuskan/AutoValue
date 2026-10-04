"""Prediction contract for the vehicle-price model; prices are learned in lakhs."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .features import normalize, REFERENCE_YEAR

MODEL_PATH=Path(__file__).resolve().parents[1]/'models/selected_model.joblib'
FIELDS={'brand':'Brand','model_name':'Model','yom':'YOM','engine_cc':'Engine (cc)',
        'gear':'Gear','fuel_type':'Fuel Type','millage':'Millage(KM)','condition':'Condition'}

def load_bundle():
    if not MODEL_PATH.exists():
        raise FileNotFoundError('Run train.py to create the vehicle-price model.')
    return joblib.load(MODEL_PATH)

def predict_car(car,bundle=None):
    bundle=load_bundle() if bundle is None else bundle
    meta=bundle['metadata']; info=meta['metrics']
    if set(car)-set(FIELDS): raise ValueError('Unexpected fields: '+', '.join(sorted(set(car)-set(FIELDS))))
    values=dict(car)
    values.setdefault('condition','USED')
    required={'brand','model_name','yom','gear','fuel_type','condition'}
    if info['use_engine']: required.add('engine_cc')
    if info['use_mileage']: required.add('millage')
    if required-set(values): raise ValueError('Missing fields: '+', '.join(sorted(required-set(values))))
    for key in ['brand','model_name','gear','fuel_type','condition']:
        if not isinstance(values[key],str) or not values[key].strip(): raise ValueError(f'{key} must be nonempty text.')
    if values['condition'].strip().upper() not in {'USED','NEW'}: raise ValueError('condition must be USED or NEW.')
    for key,low,high in [('yom',1886,REFERENCE_YEAR),('engine_cc',0,20000),('millage',0,3000000)]:
        value=values.get(key)
        if isinstance(value, (bool, np.bool_)):
            raise ValueError(f'{key} must be numeric, not true or false.')
        if value is None and key not in required:
            values[key]=np.nan; continue
        try: number=float(value)
        except (TypeError,ValueError): raise ValueError(f'{key} must be numeric.')
        if not np.isfinite(number) or not low<=number<=high: raise ValueError(f'{key} must be between {low} and {high}.')
        if key=='yom' and number!=int(number): raise ValueError('yom must be a whole year.')
        values[key]=number
    frame=normalize(pd.DataFrame([{col:values[key] for key,col in FIELDS.items()}]))
    # Validate supported inputs before calling the model, including direct Python callers.
    row = frame.iloc[0]
    brand, model = row['Brand'], row['Model']
    if brand not in meta['brand_models']:
        raise ValueError('Choose a supported brand.')
    if model not in meta['brand_models'][brand]:
        raise ValueError('Choose a model belonging to the selected brand.')
    if row['Gear'] not in {'AUTOMATIC', 'MANUAL'}:
        raise ValueError('Transmission must be AUTOMATIC or MANUAL.')
    if row['Fuel Type'] not in meta['categories']['Fuel Type']:
        raise ValueError('Choose a supported fuel type.')
    engine = values['engine_cc']
    if np.isfinite(engine):
        if row['Fuel Type'] == 'ELECTRIC' and engine != 0:
            raise ValueError('An electric vehicle must have engine capacity 0 cc.')
        if row['Fuel Type'] != 'ELECTRIC' and engine <= 0:
            raise ValueError('A combustion or hybrid vehicle must have engine capacity greater than 0 cc.')
    warnings=[]
    for col,categories in meta['categories'].items():
        if frame.iloc[0][col] not in categories: warnings.append(f'{col} was not observed in training; this estimate has weaker support.')
    for col,(low,high) in meta['ranges'].items():
        if col=='Millage(KM)' and not info['use_mileage']: continue
        if col=='Engine (cc)' and not info['use_engine']: continue
        if not low<=float(frame.iloc[0][col])<=high: warnings.append(f'{col} is outside the observed training range ({low:g}–{high:g}).')
    brand,model=frame.iloc[0].Brand,frame.iloc[0].Model
    if info['use_engine']:
        observed=meta.get('engine_options',{}).get(brand,{}).get(model,[])
        if values['engine_cc'] not in observed:
            warnings.append('This engine capacity was not recorded for the selected brand and model in training. Confirm it from the vehicle registration or specifications; this combination has weaker support.')
    pred=float(bundle['pipeline'].predict(frame)[0])
    if not np.isfinite(pred) or pred<=0: raise ValueError('A supported positive valuation could not be produced.')
    return {'predicted_price_lakhs':round(pred,4),'predicted_price_lkr':round(pred*100000,2),
            'currency':'LKR','model':info['winner'],'data_period':info['date_range'],
            'valuation_basis':'Vehicle asking-price estimate.',
            'warnings':warnings}
