try:
    import pandas as pd
except ImportError:
    pd = None
    print("[train_model] pandas is not installed; synthetic data generation will fail")

try:
    import numpy as np
except ImportError:
    np = None
    print("[train_model] numpy is not installed; synthetic data generation will fail")

# optional imports with fallback
try:
    import xgboost as xgb
except ImportError:
    xgb = None

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import pickle
import os

def generate_synthetic_data(num_records=500):
    np.random.seed(42)
    
    # Features
    land_size = np.random.uniform(0.5, 20.0, num_records) # in acres
    irrigation_availability = np.random.choice([0, 1], num_records, p=[0.3, 0.7])
    avg_yield_last_3_seasons = np.random.uniform(10, 100, num_records) # quintals
    yield_consistency_index = np.random.uniform(0, 1, num_records) 
    soil_health_index = np.random.uniform(0, 100, num_records)
    rainfall_deviation = np.random.uniform(-30, 30, num_records) # percentage deviation
    previous_repayment_status = np.random.choice([0, 1], num_records, p=[0.2, 0.8])
    loan_to_income_ratio = np.random.uniform(0.1, 0.9, num_records)
    crop_failure_history = np.random.choice([0, 1], num_records, p=[0.8, 0.2])
    district_average_yield_deviation = np.random.uniform(-20, 20, num_records)

    df = pd.DataFrame({
        'land_size': land_size,
        'irrigation_availability': irrigation_availability,
        'avg_yield_last_3_seasons': avg_yield_last_3_seasons,
        'yield_consistency_index': yield_consistency_index,
        'soil_health_index': soil_health_index,
        'rainfall_deviation': rainfall_deviation,
        'previous_repayment_status': previous_repayment_status,
        'loan_to_income_ratio': loan_to_income_ratio,
        'crop_failure_history': crop_failure_history,
        'district_average_yield_deviation': district_average_yield_deviation
    })

    # Create roughly realistic target variable (1 = Repay, 0 = Default)
    # Higher scores in good traits increase chance of 1
    score = (
        (irrigation_availability * 2) +
        (yield_consistency_index * 3) +
        (soil_health_index / 20) +
        (previous_repayment_status * 4) -
        (loan_to_income_ratio * 3) -
        (crop_failure_history * 3) +
        (district_average_yield_deviation / 10) -
        (np.abs(rainfall_deviation) / 10)
    )
    
    # Adding some noise
    score += np.random.normal(0, 1, num_records)
    
    # Threshold for repayment
    threshold = np.percentile(score, 30) # 70% repayment rate approximately
    
    df['target'] = (score >= threshold).astype(int)
    
    return df

def train_and_save_model():
    print("Generating synthetic data...")
    df = generate_synthetic_data(500)
    
    X = df.drop('target', axis=1)
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    if xgb is None:
        raise ImportError("xgboost is not installed; install it to train the model")
    print("Training XGBoost Classifier...")
    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print("Confusion Matrix:")
    print(conf_matrix)
    
    # Save the model
    os.makedirs('models', exist_ok=True)
    model_path = os.path.join('models', 'credit_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to {model_path}")

    # Save test set and metrics for the performance dashboard later if needed
    # (Optional: save to a json or just let the dashboard run inference)
    
if __name__ == '__main__':
    train_and_save_model()
