import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import joblib
import os

# Set base directory to the 'backend' folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def train_model(processed_data_path, model_output_path):
    # Load processed data
    df = pd.read_csv(processed_data_path)
    
    # Feature columns
    feature_cols = [
        'Brand_encoded', 'Model_encoded', 'YOM', 'Engine (cc)', 
        'Gear', 'Fuel Type_encoded', 'Millage(KM)', 'Town_encoded', 'Condition'
    ]
    X = df[feature_cols]
    y = df['Price']
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train Random Forest model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate model
    predictions = model.predict(X_test)
    print("\n--- Model Evaluation ---")
    print(f"MAE:  {mean_absolute_error(y_test, predictions):.2f}")
    print(f"RMSE: {root_mean_squared_error(y_test, predictions):.2f}")
    print(f"R²:   {r2_score(y_test, predictions):.2f}\n")
    
    # Save the trained model
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(model, model_output_path)
    print(f"Model successfully saved to: {model_output_path}")

if __name__ == "__main__":
    train_model(
        processed_data_path=os.path.join(BASE_DIR, 'data', 'processed', 'processed_car_data.csv'),
        model_output_path=os.path.join(BASE_DIR, 'models', 'car_valuation_model.pkl')
    )