from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import joblib
import json
import pandas as pd

app = FastAPI(title="Sri Lankan Car Valuation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and mappings at startup
try:
    model = joblib.load('models/car_valuation_model.pkl')
    with open('models/target_mappings.json', 'r') as f:
        target_mappings = json.load(f)
except Exception as e:
    print("Error loading models or mappings. Did you run the training scripts?")

class CarFeatures(BaseModel):
    brand: str
    model_name: str
    yom: int
    engine_cc: float
    gear: str
    fuel_type: str
    millage: float
    town: str

@app.post("/predict")
def predict_price(car: CarFeatures):
    try:
        # Encode inputs based on training mappings (using global average as fallback for unseen data)
        brand_enc = target_mappings['Brand'].get(car.brand, sum(target_mappings['Brand'].values()) / len(target_mappings['Brand']))
        model_enc = target_mappings['Model'].get(car.model_name, sum(target_mappings['Model'].values()) / len(target_mappings['Model']))
        fuel_enc = target_mappings['Fuel Type'].get(car.fuel_type, sum(target_mappings['Fuel Type'].values()) / len(target_mappings['Fuel Type']))
        town_enc = target_mappings['Town'].get(car.town, sum(target_mappings['Town'].values()) / len(target_mappings['Town']))
        
        # Binary variables
        gear_val = 1 if car.gear.lower() == 'automatic' else 0
        cond_val = 1 if car.condition.lower() == 'used' else 0
        
        # Prepare input data for the model
        input_data = pd.DataFrame([{
            'Brand_encoded': brand_enc,
            'Model_encoded': model_enc,
            'YOM': car.yom,
            'Engine (cc)': car.engine_cc,
            'Gear': gear_val,
            'Fuel Type_encoded': fuel_enc,
            'Millage(KM)': car.millage,
            'Town_encoded': town_enc,
            'Condition': cond_val
        }])
        
        prediction = model.predict(input_data)[0]
        return {"predicted_price_lkr": round(prediction, 2)}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Run the API from terminal: uvicorn app:app --reload