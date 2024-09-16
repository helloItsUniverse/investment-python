import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

BACKEND_URL = "http://localhost:8000"

def register_user(username, investment_preference, risk_tolerance):
    try:
        response = requests.post(f"{BACKEND_URL}/register", json={
            "username": username,
            "investment_preference": investment_preference,
            "risk_tolerance": risk_tolerance
        })
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"사용자 등록 중 오류 발생: {str(e)}")
        return None

def get_investment_advice(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/advanced_investment_advice", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"투자 조언을 가져오는 중 오류 발생: {str(e)}")
        return None

def calculate_investment(amount, days):
    try:
        response = requests.post(f"{BACKEND_URL}/calculate", json={"amount": amount, "days": days})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"투자 계산 중 오류 발생: {str(e)}")
        return None

st.set_page_config(page_title="고급 달러 투자 결정 도우미", page_icon="💰", layout="wide")

# Initialize session state for advice
if 'advice_data' not in st.session_state:
    st.session_state.advice_data = None

# 사이드바 - 사용자 정보 및 로그인/로그아웃
with st.sidebar:
    st.title("사용자 정보")
    if "user_token" not in st.session_state:
        st.subheader("새 사용자 등록")
        username = st.text_input("사용자 이름")
        investment_preference = st.selectbox("투자 선호도", ["안정적", "균형", "공격적"])
        risk_tolerance = st.selectbox("위험 감수성", ["낮음", "중간", "높음"])
        if st.button("등록"):
            result = register_user(username, investment_preference, risk_tolerance)
            if result and "message" in result:
                st.success(result["message"])
                st.session_state.user_token = username  # 간단한 토큰 처리
            else:
                st.error("등록 실패")
    else:
        st.success(f"로그인 상태: {st.session_state.user_token}")
        if st.button("로그아웃"):
            del st.session_state.user_token
            st.session_state.advice_data = None  # Clear advice data on logout
            st.experimental_rerun()

# 메인 페이지
st.title("고급 달러 투자 결정 도우미 💰")

# 탭 생성
tab1, tab2, tab3 = st.tabs(["투자 조언", "투자 계산기", "시장 동향"])

# 투자 조언 탭
with tab1:
    st.header("AI 투자 조언")
    if "user_token" in st.session_state:
        if st.button("투자 조언 받기", key="advice_button"):
            with st.spinner("AI 금융 어드바이저가 분석 중..."):
                st.session_state.advice_data = get_investment_advice(st.session_state.user_token)
        
        if st.session_state.advice_data:
            advice_data = st.session_state.advice_data
            if 'current_rate' in advice_data:
                st.metric("현재 환율", f"1 USD = {advice_data['current_rate']:.2f} KRW")
            else:
                st.warning("현재 환율 정보를 받아오지 못했습니다.")
            
            if 'advice' in advice_data:
                st.subheader("AI 금융 어드바이저 조언")
                st.write(advice_data['advice'])
            else:
                st.warning("투자 조언을 받아오지 못했습니다.")
            
            if 'historical_rates' in advice_data:
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
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("과거 환율 데이터를 받아오지 못했습니다.")
    else:
        st.warning("투자 조언을 받으려면 먼저 로그인하세요.")

# 투자 계산기 탭
with tab2:
    st.header("투자 계산기")
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("투자 금액 (USD)", min_value=0.01, value=1000.0, step=100.0)
    with col2:
        days = st.number_input("투자 기간 (일)", min_value=1, value=30, step=1)
    
    if st.button("계산하기", key="calculate_button"):
        result = calculate_investment(amount, days)
        if result:
            initial_amount = amount
            final_amount = result.get('final_amount')
            if final_amount is not None:
                profit = final_amount - initial_amount
                profit_percentage = (profit / initial_amount) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("초기 투자금", f"${initial_amount:,.2f}")
                col2.metric("최종 금액", f"${final_amount:,.2f}")
                col3.metric("수익률", f"{profit_percentage:.2f}%", f"{profit:+,.2f}")
            else:
                st.warning("최종 금액 정보를 받아오지 못했습니다.")

# 시장 동향 탭
with tab3:
    st.header("시장 동향")
    st.info("이 섹션은 현재 개발 중입니다. 곧 실시간 시장 동향과 뉴스를 제공할 예정입니다.")

# 주의사항
st.markdown("""
---
### 주의사항
- 이 앱에서 제공하는 조언은 참고용으로만 사용해 주세요.
- 실제 투자 결정은 개인의 재정 상황, 위험 선호도, 그리고 추가적인 시장 분석을 고려해야 합니다.
- AI 금융 어드바이저의 조언은 전문 금융 자문가의 조언을 대체할 수 없습니다.
- 투자에는 항상 위험이 따릅니다. 손실 가능성을 항상 염두에 두시기 바랍니다.
""")

# 푸터
st.markdown("""
---
Made with ❤️ by AI Assistant | Data provided by [Alpha Vantage](https://www.alphavantage.co/)
""")