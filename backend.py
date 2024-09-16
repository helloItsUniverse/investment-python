# backend.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, field_validator
from typing import Annotated, List, Optional, Union
import requests
import os
import yfinance as yf
from datetime import datetime, timedelta
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableSequence
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
import logging
from dotenv import load_dotenv
from langchain.callbacks.tracers.langchain import LangChainTracer
from langchain.callbacks.manager import CallbackManager
from langsmith import Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# API key setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EXCHANGE_RATE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# LangSmith setup
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")

client = Client()
tracer = LangChainTracer()
callback_manager = CallbackManager([tracer])

# Simple dictionary for user storage (use a database in production)
users_db = {}

class User(BaseModel):
    username: str
    investment_preference: str
    risk_tolerance: str

class Investment(BaseModel):
    amount: Annotated[float, field_validator('amount')]
    days: Annotated[int, field_validator('days')]

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Investment amount must be greater than 0')
        return v

    @field_validator('days')
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Investment period must be greater than 0 days')
        return v

# Simple token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    user = users_db.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

def get_exchange_rate() -> float:
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=KRW&apikey={EXCHANGE_RATE_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
    except requests.RequestException as e:
        logger.error(f"Error fetching exchange rate: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch exchange rate")

def get_historical_rates(days: int = 30) -> List[float]:
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        usd_krw = yf.Ticker("USDKRW=X")
        history = usd_krw.history(start=start_date, end=end_date)
        return history['Close'].tolist()
    except Exception as e:
        logger.error(f"Error fetching historical rates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical rates")

def get_economic_news(_=None):  # 인자를 받을 수 있도록 수정
    try:
        search = DuckDuckGoSearchRun()
        news = search.run("Latest economic news Korea US exchange rate")
        return news
    except Exception as e:
        logger.error(f"Error fetching economic news: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch economic news")

def get_advanced_investment_advice(current_rate: float, historical_rates: List[float], user: User) -> str:
    try:
        llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY)
        
        analysis_prompt = ChatPromptTemplate.from_template(
            """You are an AI financial advisor specialized in USD to KRW investments. 
            Given the following information:
            
            Current exchange rate: {current_rate}
            Historical rates: {historical_rates}
            Latest economic news: {economic_news}
            User's investment preference: {investment_preference}
            User's risk tolerance: {risk_tolerance}
            
            Provide a comprehensive analysis and clear recommendation for USD to KRW investment.
            """
        )

        translation_prompt = ChatPromptTemplate.from_template(
            """Translate the following investment advice to Korean. 
            Maintain a formal and professional tone:

            {english_advice}
            """
        )

        chain = RunnableSequence(
            {
                "current_rate": lambda x: current_rate,
                "historical_rates": lambda x: historical_rates,
                "economic_news": get_economic_news,
                "investment_preference": lambda x: user.investment_preference,
                "risk_tolerance": lambda x: user.risk_tolerance,
            }
            | analysis_prompt
            | llm
            | StrOutputParser()
            | (lambda english_advice: {"english_advice": english_advice})
            | translation_prompt
            | llm
            | StrOutputParser()
        )

        return chain.invoke({}, config={"callbacks": callback_manager})
    except Exception as e:
        logger.error(f"Error generating investment advice: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate investment advice")

@app.post("/register")
async def register_user(user: User):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    users_db[user.username] = user
    return {"message": "User registered successfully"}

@app.get("/advanced_investment_advice")
async def get_investment_advice(current_user: User = Depends(get_current_user)):
    try:
        current_rate = get_exchange_rate()
        historical_rates = get_historical_rates()
        advice = get_advanced_investment_advice(current_rate, historical_rates, current_user)
        return {
            "current_rate": current_rate,
            "historical_rates": historical_rates,
            "advice": advice
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_investment_advice: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@app.post("/calculate")
async def calculate_investment(investment: Investment):
    try:
        # Implement your investment calculation logic here
        # This is a placeholder implementation
        final_amount = investment.amount * (1 + 0.05) ** (investment.days / 365)
        return {"final_amount": final_amount}
    except Exception as e:
        logger.error(f"Error calculating investment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate investment")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)