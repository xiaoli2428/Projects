from fastapi import FastAPI
from pydantic import BaseModel

class PredictionRequest(BaseModel):
    symbol: str

app = FastAPI()

@app.post("/predict")
def predict_market(req: PredictionRequest):
    # Dummy AI logic: always 60% buy confidence for demo
    return {
        "symbol": req.symbol,
        "suggest_buy": True,
        "confidence": 0.6,
        "analysis_text": f"Market analysis for {req.symbol} (dummy): Uptrend detected. Suggest to consider buying."
    }

# To run: uvicorn ai_predict:app --reload --port 8000
