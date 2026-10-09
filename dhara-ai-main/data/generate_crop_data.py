import pandas as pd
import numpy as np

def generate_crop_data(num_rows=1000):
    np.random.seed(42)
    
    crops = ["Rice", "Wheat", "Cotton", "Sugarcane", "Maize", "Pulses", "Groundnut"]
    seasons = ["Kharif", "Rabi", "Whole Year"]
    states = ["Maharashtra", "Punjab", "Andhra Pradesh", "Uttar Pradesh", "Madhya Pradesh", "Karnataka"]
    
    crop_col = np.random.choice(crops, num_rows)
    season_col = np.random.choice(seasons, num_rows)
    state_col = np.random.choice(states, num_rows)
    
    area_col = np.random.uniform(1.0, 50.0, num_rows)
    rainfall_col = np.random.uniform(400, 2000, num_rows)
    fert_col = np.random.uniform(20.0, 250.0, num_rows)
    pest_col = np.random.uniform(1.0, 10.0, num_rows)
    
    # Generate yield roughly based on area, rainfall, fert, pest
    # Higher area, avg rainfall, moderate fert gives better yield
    yield_col = (area_col * 2.5) + (rainfall_col * 0.01) + (fert_col * 0.1) - (pest_col * 0.5) + np.random.normal(0, 5, num_rows)
    production_col = yield_col * area_col # Strong correlation
    crop_year_col = np.random.choice([2020, 2021, 2022, 2023], num_rows)
    
    df = pd.DataFrame({
        "Yield": yield_col,
        "Production": production_col,
        "Crop_Year": crop_year_col,
        "Crop": crop_col,
        "Season": season_col,
        "State": state_col,
        "Area": area_col,
        "Annual_Rainfall": rainfall_col,
        "Fertilizer": fert_col,
        "Pesticide": pest_col
    })
    
    df.to_csv("c:/Hackathons/Dhara/crop_yield.csv", index=False)
    print(f"Generated synthetic dataset with {num_rows} rows at c:/Hackathons/Dhara/crop_yield.csv")

if __name__ == "__main__":
    generate_crop_data()
