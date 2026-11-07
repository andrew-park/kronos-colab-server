# Kronos Colab Server

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/andrew-park/kronos-colab-server/blob/main/run_colab.ipynb)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

Google Colab(NVIDIA L4/T4 GPU) 환경에서 `Kronos` 금융 시계열 파운데이션 모델 제품군을 구동하고, Cloudflare Tunnel을 통해 외부(로컬 대시보드, 트레이딩 봇)에서 접근 가능한 HTTPS REST API를 제공하는 백엔드 추론 서버입니다.

## 지원 모델 제품군 (Model Zoo)

`KRONOS_MODEL_SIZE` 환경 변수 또는 `--model` 인자로 모델을 선택하여 구동할 수 있습니다.

| 모델 옵션 | Hugging Face 모델명 | 토크나이저 | 최대 컨텍스트 | 파라미터 | 특징 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **mini** | `NeoQuasar/Kronos-mini` | `NeoQuasar/Kronos-Tokenizer-2k` | **2048** | 4.1M | 초경량, 빠른 추론, 긴 시계열 컨텍스트 |
| **small** | `NeoQuasar/Kronos-small` | `NeoQuasar/Kronos-Tokenizer-base` | 512 | 24.7M | 경량, 저지연(Low-latency) |
| **base** (기본) | `NeoQuasar/Kronos-base` | `NeoQuasar/Kronos-Tokenizer-base` | 512 | 102.3M | 표준 균형 모델 (기본값) |
| **large** | `NeoQuasar/Kronos-large` | `NeoQuasar/Kronos-Tokenizer-base` | 512 | 499.2M | 최고 정밀도 예측 모델 |

## 빠른 시작 (Colab)

1. 상단의 **[Open In Colab]** 배지를 클릭하여 노트북을 엽니다.
2. 런타임 유형을 **L4 GPU**로 설정합니다.
3. 셀 1을 실행하여 환경을 구성한 뒤, 셀 2에서 원하는 모델 플래그(`--model base`, `--model small`, `--model mini`)를 지정하여 실행합니다.
```bash
# 환경 변수로 실행 시
!KRONOS_MODEL_SIZE=mini python run_server.py

# CLI 플래그로 실행 시
!python run_server.py --model mini
```
4. 콘솔에 출력되는 공용 URL(`https://*.trycloudflare.com`)을 통해 외부에서 API를 호출합니다.

## API 엔드포인트 명세

### 1. 헬스 체크
* **Method:** `GET /health`
* **Response:**
```json
{
  "status": "healthy",
  "model_size": "base",
  "model": "NeoQuasar/Kronos-base",
  "tokenizer": "NeoQuasar/Kronos-Tokenizer-base",
  "max_context": 512,
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
  "model_size": "base",
  "predictions": [
    {"timestamp": "2026-11-06 15:05:00", "open": 70250.2, "high": 70600.1, "low": 70100.0, "close": 70400.5, "volume": 11500.0, "amount": 809605750.0}
  ]
}
```
