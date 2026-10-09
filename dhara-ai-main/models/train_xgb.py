try:
    import pandas as pd
except ImportError:
    pd = None
    print("[train_xgb] pandas is not installed; cannot load dataset")

try:
    import numpy as np
except ImportError:
    np = None
    print("[train_xgb] numpy is not installed; synthetic operations will fail")

import os

# xgboost may not be installed in constrained environments
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# joblib fallback to pickle if missing
try:
    import joblib
except ImportError:
    import pickle as _pickle

    class _JoblibFallback:
        @staticmethod
        def dump(obj, f):
            return _pickle.dump(obj, f)
        @staticmethod
        def load(f):
            return _pickle.load(f)
    joblib = _JoblibFallback()

def train_and_save():
    # =========================
    # STEP 1: Load Dataset
    # =========================
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "crop_yield.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Training data not found at {data_path}")
    data = pd.read_csv(data_path)

    print("Dataset Shape:", data.shape)
    print("\nColumns:", data.columns)

    # =========================
    # STEP 2: Create Credit Risk Target (BALANCED & LOGICAL)
    # Using Yield Percentiles (Industry-acceptable proxy)
    # =========================
    low_threshold = data["Yield"].quantile(0.33)
    high_threshold = data["Yield"].quantile(0.66)

    def assign_risk(yield_value):
        if yield_value >= high_threshold:
            return 1   # Low Risk (High productivity farmer)
        elif yield_value <= low_threshold:
            return 0   # High Risk (Low productivity farmer)
        else:
            return -1  # Middle group (remove for clarity)

    data["credit_risk"] = data["Yield"].apply(assign_risk)

    # Remove middle ambiguous rows (IMPORTANT)
    data = data[data["credit_risk"] != -1]

    print("\nBalanced Target Distribution:")
    print(data["credit_risk"].value_counts())

    # =========================
    # STEP 3: Drop Leakage & Unnecessary Columns
    # =========================
    data = data.drop(["Yield", "Production", "Crop_Year"], axis=1)

    # =========================
    # STEP 4: Encode Categorical Columns
    # =========================
    categorical_cols = ["Crop", "Season", "State"]
    data = pd.get_dummies(data, columns=categorical_cols, drop_first=True)

    # =========================
    # STEP 5: Define Features (X) and Target (y) - LEAKAGE FREE
    # =========================
    X = data.drop("credit_risk", axis=1)
    y = data["credit_risk"]

    print("\nFinal Feature Count:", X.shape[1])

    # =========================
    # STEP 6: Train-Test Split (Proper Evaluation)
    # =========================
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        shuffle=True
    )

    print("Train Shape:", X_train.shape)
    print("Test Shape:", X_test.shape)

    # =========================
    # STEP 7: Initialize XGBoost Model (Optimized for Tabular Data)
    # =========================
    if XGBClassifier is None:
        raise ImportError("xgboost is not installed; install it to train the model")

    model = XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
    )

    # =========================
    # STEP 8: Train the Model
    # =========================
    print("\nTraining XGBoost Model...")
    model.fit(X_train, y_train)

    # =========================
    # STEP 9: Model Prediction
    # =========================
    y_pred = model.predict(X_test)

    # =========================
    # STEP 10: Evaluation (For Report & Viva)
    # =========================
    accuracy = accuracy_score(y_test, y_pred)

    print("\nTest Set Class Distribution:")
    print(y_test.value_counts())

    print("\n================ MODEL RESULTS ================")
    print("Model Accuracy:", round(accuracy, 4))
    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred))

    # =========================
    # STEP 11: Save Model for FastAPI & Streamlit
    # =========================
    os.makedirs(os.path.join(os.path.dirname(__file__)), exist_ok=True)
    model_path = os.path.join(os.path.dirname(__file__), "credit_model.pkl")
    features_path = os.path.join(os.path.dirname(__file__), "model_features.pkl")
    joblib.dump(model, model_path)

    # Save feature columns (MANDATORY for prediction alignment)
    joblib.dump(X.columns.tolist(), features_path)

    print(f"\nModel saved as: {model_path}")
    print(f"Feature list saved as: {features_path}")

if __name__ == "__main__":
    train_and_save()
