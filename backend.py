# backend.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import requests
import openai
import os

app = FastAPI()

# OpenAI API 키 설정 (환경 변수에서 가져오거나 직접 설정)
openai.api_key = os.getenv("OPENAI_API_KEY") or "your_openai_api_key_here"

# 환율 API 키 (예: Alpha Vantage)
EXCHANGE_RATE_API_KEY = "your_exchange_rate_api_key_here"

class Investment(BaseModel):
    amount: float
    days: int

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('투자 금액은 0보다 커야 합니다')
        return v

    @validator('days')
    def days_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('투자 기간은 0보다 커야 합니다')
        return v

def get_exchange_rate():
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=KRW&apikey={EXCHANGE_RATE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])

def get_historical_rates(days=30):
    url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=USD&to_symbol=KRW&apikey={EXCHANGE_RATE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    rates = []
    for date, values in list(data["Time Series FX (Daily)"].items())[:days]:
        rates.append(float(values["4. close"]))
    return rates[::-1]  # 최근 날짜가 마지막에 오도록 역순 정렬

def get_gpt_investment_advice(current_rate, historical_rates):
    # GPT-3.5-turbo에 보낼 프롬프트 구성
    prompt = f"""
    현재 USD/KRW 환율: {current_rate:.2f}
    최근 30일 USD/KRW 환율 데이터: {historical_rates}

    위 정보를 바탕으로 달러 투자에 대한 조언을 해주세요. 다음 사항을 고려해 주세요:
    1. 현재 환율이 과거 30일 대비 어떤 수준인지
    2. 환율의 추세 (상승, 하락, 횡보)
    3. 매수, 매도, 또는 관망에 대한 추천과 그 이유
    4. 잠재적 리스크와 주의사항

    조언은 간결하고 명확해야 하며, 전문가처럼 설명해 주세요.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 외환 투자 전문가입니다. 사용자에게 현재 시장 상황을 바탕으로 달러 투자에 대한 전문적인 조언을 제공합니다."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"GPT 조언을 생성하는 중 오류가 발생했습니다: {str(e)}"

@app.get("/gpt_investment_advice")
async def get_investment_advice():
    try:
        current_rate = get_exchange_rate()
        historical_rates = get_historical_rates()
        gpt_advice = get_gpt_investment_advice(current_rate, historical_rates)
        return {
            "current_rate": current_rate,
            "historical_rates": historical_rates,
            "gpt_advice": gpt_advice
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 기존의 /calculate와 /future_value 엔드포인트는 유지