import os
import sys
import asyncio
from typing import List, Optional

import torch
import pandas as pd
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Upstream Kronos 레포지토리 경로를 sys.path에 동적 추가
KRONOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "Kronos"))
if KRONOS_DIR not in sys.path:
    sys.path.append(KRONOS_DIR)

from model import Kronos, KronosTokenizer, KronosPredictor  # type: ignore

app = FastAPI(
    title="Kronos Financial Forecast API",
    description="Kronos-base financial candlestick autoregressive inference engine",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# 1. Pydantic 요청/응답 스키마
# ---------------------------------------------------------------------------
class Candle(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 형식 (예: '2026-11-06 15:00:00')")
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = 0.0
    amount: Optional[float] = 0.0

class PredictRequest(BaseModel):
    history: List[Candle] = Field(..., description="과거 K-line 캔들 리스트 (최소 10개, 최대 450개 권장)")
    future_timestamps: List[str] = Field(..., description="예측할 미래 시점 타임스탬프 리스트")
    temperature: Optional[float] = Field(1.0, ge=0.1, le=2.0, description="생성 다양성 조절")
    top_p: Optional[float] = Field(0.9, ge=0.1, le=1.0, description="Nucleus sampling 확률")
    sample_count: Optional[int] = Field(1, ge=1, le=10, description="앙상블 예측 샘플링 수")

class PredictedCandle(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float

class PredictResponse(BaseModel):
    status: str
    predictions: List[PredictedCandle]

# ---------------------------------------------------------------------------
# 2. 전역 싱글톤 리소스 및 GPU 동시성 제어 락
# ---------------------------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
gpu_lock = asyncio.Lock()
predictor: Optional[KronosPredictor] = None

@app.on_event("startup")
def startup_event():
    global predictor
    print(f"[Kronos Server] Initializing model on device: {device}...")
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-base").to(device)
    predictor = KronosPredictor(model, tokenizer, max_context=512, device=device)
    print("[Kronos Server] Model successfully loaded and ready for inference.")

# ---------------------------------------------------------------------------
# 3. 라우터 엔드포인트
# ---------------------------------------------------------------------------
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    allocated_mb = 0
    if device == "cuda":
        allocated_mb = round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
    return {
        "status": "healthy",
        "model": "NeoQuasar/Kronos-base",
        "device": device,
        "cuda_memory_allocated_mb": allocated_mb
    }

@app.post("/predict", response_model=PredictResponse, status_code=status.HTTP_200_OK)
async def predict_candlesticks(req: PredictRequest):
    lookback = len(req.history)
    pred_len = len(req.future_timestamps)

    if lookback < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="과거 캔들(history)은 최소 10개 이상이어야 합니다."
        )
    if lookback + pred_len > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"컨텍스트 한도 초과: history({lookback}) + future({pred_len})는 512를 넘을 수 없습니다."
        )

    try:
        raw_df = pd.DataFrame([c.model_dump() for c in req.history])
        raw_df['timestamps'] = pd.to_datetime(raw_df['timestamp'])
        
        x_df = raw_df[['open', 'high', 'low', 'close', 'volume', 'amount']]
        x_timestamp = raw_df['timestamps']
        y_timestamp = pd.Series(pd.to_datetime(req.future_timestamps))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"데이터프레임 전처리 실패: {str(e)}"
        )

    # 비동기 락을 통해 다중 동시 요청 간 CUDA 메모리 충돌 방지
    async with gpu_lock:
        try:
            loop = asyncio.get_event_loop()
            pred_df = await loop.run_in_executor(
                None,
                lambda: predictor.predict(
                    df=x_df,
                    x_timestamp=x_timestamp,
                    y_timestamp=y_timestamp,
                    pred_len=pred_len,
                    T=req.temperature,
                    top_p=req.top_p,
                    sample_count=req.sample_count
                )
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Kronos 연산 중 오류 발생: {str(e)}"
            )

    pred_df['timestamp'] = y_timestamp.dt.strftime('%Y-%m-%d %H:%M:%S').values
    result = pred_df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount']].to_dict(orient="records")
    return PredictResponse(status="success", predictions=result)
