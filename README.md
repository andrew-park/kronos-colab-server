# Kronos Colab Server

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/andrew-park/kronos-colab-server/blob/main/run_colab.ipynb)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

Google Colab(NVIDIA L4 GPU) 환경에서 `Kronos-base` 금융 시계열 파운데이션 모델을 구동하고, Cloudflare Tunnel을 통해 외부(로컬 대시보드, 트레이딩 봇)에서 접근 가능한 HTTPS REST API를 제공하는 백엔드 추론 서버입니다.

## 빠른 시작 (Colab)

1. 상단의 **[Open In Colab]** 배지를 클릭하여 노트북을 엽니다.
2. 런타임 유형을 **L4 GPU**로 설정합니다.
3. 노트북의 셀을 차례대로 실행하면 콘솔에 공용 URL(`https://*.trycloudflare.com`)이 출력됩니다.

## API 엔드포인트 명세

### 1. 헬스 체크
* **Method:** `GET /health`
* **Response:**
```json
{
  "status": "healthy",
  "model": "NeoQuasar/Kronos-base",
  "device": "cuda",
  "cuda_memory_allocated_mb": 450.25
}
```

### 2. K-line 미래 예측
* **Method:** `POST /predict`
* **Request Body:**
```json
{
  "history": [
    {"timestamp": "2026-11-06 15:00:00", "open": 70000, "high": 70500, "low": 69800, "close": 70200, "volume": 12000, "amount": 842400000}
  ],
  "future_timestamps": [
    "2026-11-06 15:05:00",
    "2026-11-06 15:10:00"
  ],
  "temperature": 0.8,
  "top_p": 0.9,
  "sample_count": 2
}
```
* **Response Body:**
```json
{
  "status": "success",
  "predictions": [
    {"timestamp": "2026-11-06 15:05:00", "open": 70250.2, "high": 70600.1, "low": 70100.0, "close": 70400.5, "volume": 11500.0, "amount": 809605750.0}
  ]
}
```
