# frontend.py
import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

BACKEND_URL = "http://localhost:8000"

st.title("달러 투자 결정 도우미 (GPT-3.5-turbo 조언)")

# GPT-3.5-turbo 투자 조언 섹션
st.subheader("GPT-3.5-turbo 투자 조언")
if st.button("GPT-3.5-turbo 조언 받기"):
    try:
        with st.spinner("GPT-3.5-turbo로부터 조언을 받아오는 중..."):
            response = requests.get(f"{BACKEND_URL}/gpt_investment_advice")
            response.raise_for_status()
            advice_data = response.json()
        
        st.write(f"현재 환율: 1 USD = {advice_data['current_rate']:.2f} KRW")
        
        # GPT-3.5-turbo 조언 표시
        st.markdown("### GPT-3.5-turbo 조언")
        st.write(advice_data['gpt_advice'])
        
        # 과거 30일 환율 그래프
        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=advice_data['historical_rates'],
            mode='lines+markers',
            name='USD/KRW 환율'
        ))
        fig.update_layout(
            title='USD/KRW 환율 추이 (최근 30일)',
            xaxis_title='날짜',
            yaxis_title='환율 (KRW)'
        )
        st.plotly_chart(fig)
        
    except requests.RequestException as e:
        st.error(f"투자 조언을 가져오는 중 오류가 발생했습니다: {str(e)}")

# 기존의 투자 계산기 기능 유지
st.subheader("투자 계산기")
amount = st.number_input("투자 금액 (USD)", min_value=0.01, value=1000.0, step=100.0)
days = st.number_input("투자 기간 (일)", min_value=1, value=30, step=1)

if st.button("계산하기"):
    try:
        response = requests.post(f"{BACKEND_URL}/calculate", json={"amount": amount, "days": days})
        response.raise_for_status()
        result = response.json()
        st.success(f"{days}일 후 예상 금액: ${result['final_amount']:,.2f}")
    except requests.RequestException as e:
        st.error(f"계산 중 오류가 발생했습니다: {str(e)}")

# 주의사항
st.markdown("""
### 주의사항
- 이 앱에서 제공하는 조언은 참고용으로만 사용해 주세요.
- 실제 투자 결정은 개인의 재정 상황, 위험 선호도, 그리고 추가적인 시장 분석을 고려해야 합니다.
- GPT-3.5-turbo의 조언은 AI가 생성한 것으로, 전문 금융 자문가의 조언을 대체할 수 없습니다.
- 투자에는 항상 위험이 따릅니다. 손실 가능성을 항상 염두에 두시기 바랍니다.
""")