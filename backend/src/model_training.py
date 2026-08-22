import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import joblib
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def evaluate_and_train(processed_data_path, model_output_path):
    print("Loading data and initializing models...\n")
    df = pd.read_csv(processed_data_path)
    
    # Feature columns (strictly based on EDA correlation results)
    feature_cols = [
        'Brand_encoded', 'Model_encoded', 'YOM', 'Engine (cc)', 
        'Gear', 'Fuel Type_encoded', 'Millage(KM)', 'Town_encoded'
    ]
    X = df[feature_cols]
    y = df['Price']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    models = {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "Lasso Regression": Lasso(alpha=0.1),
        "Decision Tree": DecisionTreeRegressor(random_state=42),
        "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
        "XGBoost": XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42)
    }
    
    results = []
    best_model_name = ""
    best_model_instance = None
    best_mae = float('inf') # Tracking for lowest error

    for name, model in models.items():
        start_time = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start_time
        
        predictions = model.predict(X_test)
        
        mae = mean_absolute_error(y_test, predictions)
        rmse = root_mean_squared_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        
        results.append({
            "Algorithm": name,
            "MAE (Lakhs)": round(mae, 2),
            "RMSE": round(rmse, 2),
            "R2 Score": round(r2, 4),
            "Train Time (s)": round(train_time, 3)
        })
        
        # Select winner based on real-world accuracy (lowest MAE)
        if mae < best_mae:
            best_mae = mae
            best_model_name = name
            best_model_instance = model

    results_df = pd.DataFrame(results).sort_values(by="MAE (Lakhs)", ascending=True)
    
    print("-" * 75)
    print("MODEL EVALUATION COMPARISON MATRIX")
    print("-" * 75)
    print(results_df.to_string(index=False))
    print("-" * 75)
    
    print(f"\nWinner: {best_model_name} (MAE: {best_mae:.2f} Lakhs)")
    
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(best_model_instance, model_output_path)
    print(f"The winning model was successfully saved to: {model_output_path}")

if __name__ == "__main__":
    evaluate_and_train(
        processed_data_path=os.path.join(BASE_DIR, 'data', 'processed', 'processed_car_data.csv'),
        model_output_path=os.path.join(BASE_DIR, 'models', 'car_valuation_model.pkl')
    )