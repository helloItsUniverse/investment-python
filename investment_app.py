import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Backend URL
BACKEND_URL = "http://0.0.0.0:8000"

# Helper functions
def login(username, password):
    try:
        response = requests.post(f"{BACKEND_URL}/token", data={
            "username": username,
            "password": password
        })
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"로그인 중 오류 발생: {str(e)}")
        return None

def register_user(email, username, password, investment_preference, risk_tolerance):
    try:
        response = requests.post(f"{BACKEND_URL}/register", json={
            "email": email,
            "username": username,
            "password": password,
            "investment_preference": investment_preference,
            "risk_tolerance": risk_tolerance
        })
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"사용자 등록 중 오류 발생: {str(e)}")
        return None

def request_verification_code(email):
    try:
        response = requests.post(f"{BACKEND_URL}/request-verification", json={"email": email})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"인증 코드 요청 중 오류 발생: {str(e)}")
        return None

def verify_email(email, code):
    try:
        response = requests.post(f"{BACKEND_URL}/verify-email", json={"email": email, "code": code})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"이메일 인증 중 오류 발생: {str(e)}")
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

# Page configuration
st.set_page_config(page_title="고급 달러 투자 결정 도우미", page_icon="💰", layout="wide")

# Initialize session state
if 'user_token' not in st.session_state:
    st.session_state.user_token = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'advice_data' not in st.session_state:
    st.session_state.advice_data = None

# Main function
def main():
    st.title("고급 달러 투자 결정 도우미 🚀")

    if st.session_state.user_token:
        show_logged_in_view()
    else:
        show_login_register()

# Login and Register view
def show_login_register():
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_register_form()

def show_login_form():
    st.header("로그인")
    username = st.text_input("사용자명", key="login_username")
    password = st.text_input("비밀번호", type="password", key="login_password")
    if st.button("로그인"):
        result = login(username, password)
        if result and "access_token" in result:
            st.session_state.user_token = result["access_token"]
            st.session_state.username = username
            st.success("로그인 성공!")
            st.rerun()

def show_register_form():
    st.header("회원가입")
    
    email = st.text_input("이메일", key="register_email")
    
    if st.button("인증번호 받기"):
        result = request_verification_code(email)
        if result and "message" in result:
            st.success(result["message"])
            st.session_state.email_for_verification = email
    
    verification_code = st.text_input("인증번호", key="verification_code")

    if st.button("인증번호 확인"):
        if st.session_state.get('email_for_verification'):
            result = verify_email(st.session_state.email_for_verification, verification_code)
            if result and "message" in result:
                st.success(result["message"])
                st.session_state.email_verified = True
        else:
            st.error("먼저 인증번호를 요청해주세요.")
    
    username = st.text_input("사용자명", key="register_username")
    password = st.text_input("비밀번호", type="password", key="register_password")
    investment_preference = st.selectbox("투자 선호도", ["안정적", "균형", "공격적"])
    risk_tolerance = st.selectbox("위험 감수성", ["낮음", "중간", "높음"])
    
    if st.button("회원가입"):
        if not st.session_state.get('email_verified'):
            st.error("이메일 인증을 먼저 완료해주세요.")
        elif not email or not username or not password or not investment_preference or not risk_tolerance:
            st.error("모든 필드를 입력해주세요.")
        else:
            result = register_user(email, username, password, investment_preference, risk_tolerance)
            if result and "message" in result:
                st.success(result["message"])
                st.info("이제 로그인할 수 있습니다.")
                st.session_state.email_verified = False  # Reset for next registration
                st.rerun()

# Logged in view
def show_logged_in_view():
    st.sidebar.title(f"환영합니다, {st.session_state.username}님!")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_token = None
        st.session_state.username = None
        st.session_state.advice_data = None
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["투자 조언", "투자 계산기", "시장 동향"])

    with tab1:
        show_investment_advice()

    with tab2:
        show_investment_calculator()

    with tab3:
        show_market_trends()

# Investment Advice Tab
def show_investment_advice():
    st.header("AI 투자 조언")
    if st.button("투자 조언 받기", key="advice_button"):
        with st.spinner("AI 금융 어드바이저가 분석 중..."):
            st.session_state.advice_data = get_investment_advice(st.session_state.user_token)
    
    if st.session_state.advice_data:
        advice_data = st.session_state.advice_data
        if 'current_rate' in advice_data:
            st.metric("현재 환율", f"1 USD = {advice_data['current_rate']:.2f} KRW")
        
        if 'advice' in advice_data:
            st.subheader("AI 금융 어드바이저 조언")
            st.write(advice_data['advice'])
        
        if 'historical_rates' in advice_data:
            show_historical_rates_chart(advice_data['historical_rates'])

# Investment Calculator Tab
def show_investment_calculator():
    st.header("투자 계산기")
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("투자 금액 (USD)", min_value=0.01, value=1000.0, step=100.0)
    with col2:
        days = st.number_input("투자 기간 (일)", min_value=1, value=30, step=1)
    
    if st.button("계산하기", key="calculate_button"):
        result = calculate_investment(amount, days)
        if result:
            show_investment_result(amount, result)

# Market Trends Tab
def show_market_trends():
    st.header("시장 동향")
    st.info("이 섹션은 현재 개발 중입니다. 곧 실시간 시장 동향과 뉴스를 제공할 예정입니다.")

# Helper function to show historical rates chart
def show_historical_rates_chart(historical_rates):
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=historical_rates,
        mode='lines+markers',
        name='USD/KRW 환율'
    ))
    fig.update_layout(
        title='USD/KRW 환율 추이 (최근 30일)',
        xaxis_title='날짜',
        yaxis_title='환율 (KRW)'
    )
    st.plotly_chart(fig, use_container_width=True)

# Helper function to show investment calculation result
def show_investment_result(initial_amount, result):
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

# Run the app
if __name__ == "__main__":
    main()