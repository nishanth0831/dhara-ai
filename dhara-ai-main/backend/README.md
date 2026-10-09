## Dhara AI Backend (Flask)

This is a **separate backend service** for Dhara AI. It reuses the existing project logic:
- verification: `verification/engine.py`
- scoring: `services/model_service.py`
- weather: `services/weather_service.py`
- pdf report: `reports/pdf_generator.py`

### Run (Windows PowerShell)

```powershell
cd "c:\Hackathons\Dhara"
pip install -r backend\requirements.txt
python backend\app.py
```

Backend will start on `http://localhost:8000`.

### API Endpoints

- `GET /health`
- `GET /weather?district=...&state=...`
- `POST /score`
- `POST /report` (returns a PDF)

### Retraining the credit model

If you need to rebuild the ML models (for improved accuracy or after updating `crop_yield.csv`), run one of the training scripts from the project root. These will produce `credit_model.pkl` and `model_features.pkl` under the `models/` directory.

```powershell
# install full dependencies before retraining (make sure joblib, xgboost, scikit-learn, pandas, etc. are available)
pip install -r requirements.txt

# simple synthetic example
python models/train_model.py

# or use real crop yield data for more realistic model
python models/train_xgb.py
```

Both scripts gracefully report missing packages or data and use `pickle` when `joblib` is unavailable.

### Example requests

Score:

```powershell
$body = @{
  farmer_type = "Existing Farmer"
  farmer_data = @{
    name="Ramesh"
    district="Hyderabad"
    state="Telangana"
    loan_amount=50000
    land_size=2
    irrigation_availability=1
    avg_yield_last_3_seasons=20
    yield_consistency_index=0.7
    soil_health_index=65
    rainfall_deviation=5
    previous_repayment_status=1
    loan_to_income_ratio=0.4
    crop_failure_history=0
    district_average_yield_deviation=0
  }
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/score" -ContentType "application/json" -Body $body
```

Weather:

```powershell
Invoke-RestMethod "http://localhost:8000/weather?district=Hyderabad&state=Telangana"
```

