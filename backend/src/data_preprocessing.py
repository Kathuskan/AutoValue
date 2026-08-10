import pandas as pd
import json
import os

# Base directory relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def preprocess_data(raw_data_path, processed_data_path, mapping_path):
    # Load dataset
    df = pd.read_csv(raw_data_path)
    
    # Drop redundant or zero-variance columns
    cols_to_drop = ['Unnamed: 0', 'AIR CONDITION', 'POWER STEERING', 'POWER MIRROR', 'POWER WINDOW', 'Leasing', 'Date']
    df.drop(columns=[col for col in cols_to_drop if col in df.columns], inplace=True)
    
    # Binary encoding
    df['Gear'] = df['Gear'].map({'Automatic': 1, 'Manual': 0})
    df['Condition'] = df['Condition'].apply(lambda x: 1 if str(x).strip().upper() == 'USED' else 0)
    
    # Target Encoding for High-Cardinality Categorical Features
    target_enc_cols = ['Brand', 'Model', 'Fuel Type', 'Town']
    target_mappings = {}
    
    for col in target_enc_cols:
        mapping = df.groupby(col)['Price'].mean().to_dict()
        target_mappings[col] = mapping
        df[col + '_encoded'] = df[col].map(mapping)
    
    # Save target mappings
    os.makedirs(os.path.dirname(mapping_path), exist_ok=True)
    with open(mapping_path, 'w') as f:
        json.dump(target_mappings, f)
    
    # Save processed dataset
    os.makedirs(os.path.dirname(processed_data_path), exist_ok=True)
    df.to_csv(processed_data_path, index=False)
    print(f"Preprocessing complete. Mappings saved to {mapping_path}")

if __name__ == "__main__":
    preprocess_data(
        raw_data_path=os.path.join(BASE_DIR, 'data', 'raw', 'car_price_dataset.csv'),
        processed_data_path=os.path.join(BASE_DIR, 'data', 'processed', 'processed_car_data.csv'),
        mapping_path=os.path.join(BASE_DIR, 'models', 'target_mappings.json')
    )