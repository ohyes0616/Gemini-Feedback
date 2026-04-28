import streamlit as st
import google.generativeai as genai
import requests
import uuid
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="Gemini Pulse",
    page_icon="💬",
    layout="centered",
)

# ── 스타일 ───────────────────────────────────────────────
st.markdown("""
<style>
    .notice-box {
        background-color: #E1F5EE;
        border-left: 4px solid #0F6E56;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 13px;
        color: #085041;
        margin-bottom: 1rem;
    }
    .stChatMessage { font-size: 15px; }
</style>
""", unsafe_allow_html=True)

# ── 시스템 프롬프트 ──────────────────────────────────────
SYSTEM_PROMPT = """당신은 스마트워크 TF 소속의 친근한 동료입니다.
회사에서 제공한 AI(Gemini) 계정 활용에 대한 직원들의 솔직한 피드백을 수집합니다.

규칙:
1. 해요체를 사용하세요. 친근하고 가볍게 동료처럼 대화하세요.
2. 상대방의 직무, 부서, 이름 등 식별 가능한 개인정보를 절대 묻지 마세요.
3. 미공개 특허 기술, 환자 정보, 개인정보 입력을 유도하지 마세요.
4. 불만이나 단점을 토로하더라도 절대 방어하지 말고 적극 공감하세요.
5. 각 답변에 1문장 공감 + 꼬리 질문 1개만 생성하세요.
6. 응답은 3~5문장 이내로 짧게 유지하세요."""

CLOSING_PROMPT = """당신은 스마트워크 TF 소속의 친근한 동료입니다. 해요체를 사용하세요.
사용자가 마지막 질문에 답변했습니다. 따뜻한 감사 인사로 2~3문장 이내에 대화를 마무리하세요.
추가 질문은 절대 하지 마세요."""

MAX_FOLLOW_UPS = 3
WELCOME = "안녕하세요! 스마트워크 TF에서 AI 활용 경험을 모아보려고 이렇게 찾아왔어요 :)\n\nGemini 써보신 소감이 어떠세요? 좋았던 점, 아쉬웠던 점 모두 편하게 말씀해 주세요!"

# ── 세션 초기화 ──────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
if "follow_up_count" not in st.session_state:
    st.session_state.follow_up_count = 0
if "closed" not in st.session_state:
    st.session_state.closed = False

# ── Google Sheets 저장 ───────────────────────────────────
def save_to_sheets(role: str, content: str):
    webhook_url = st.secrets.get("WEBHOOK_URL", "")
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={
            "timestamp": datetime.utcnow().isoformat(),
            "session_uuid": st.session_state.session_id,
            "role": role,
            "message_content": content,
        }, timeout=3)
    except Exception:
        pass

# ── Gemini API 호출 ──────────────────────────────────────
def get_ai_response(is_closing: bool) -> str:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return "API 키가 설정되지 않았어요. secrets 설정을 확인해 주세요."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=CLOSING_PROMPT if is_closing else SYSTEM_PROMPT,
    )

    history = []
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [msg["content"]]})

    try:
        response = model.generate_content(history)
        return response.text
    except Exception as e:
        return f"오류가 발생했어요: {str(e)}"

# ── UI ───────────────────────────────────────────────────
st.markdown('<div class="notice-box">💡 익명이 보장되니 편하게 말씀해 주세요. 단, 미공개 기술 자산이나 환자 정보, 개인정보는 입력하지 않도록 주의해 주세요.</div>', unsafe_allow_html=True)
st.markdown("#### 💬 Gemini Pulse &nbsp; <span style='font-size:13px;color:gray;font-weight:400'>스마트워크 TF</span>", unsafe_allow_html=True)

if not st.session_state.closed and st.session_state.follow_up_count > 0:
    st.caption(f"질문 {st.session_state.follow_up_count} / {MAX_FOLLOW_UPS}")

# 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 입력창
if not st.session_state.closed:
    user_input = st.chat_input("AI를 사용해 본 경험을 자유롭게 말씀해 주세요...")
    if user_input:
        # 사용자 메시지 저장 및 표시
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_to_sheets("User", user_input)
        with st.chat_message("user"):
            st.write(user_input)

        is_closing = st.session_state.follow_up_count >= MAX_FOLLOW_UPS

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner(""):
                ai_text = get_ai_response(is_closing)
            st.write(ai_text)

        st.session_state.messages.append({"role": "assistant", "content": ai_text})
        save_to_sheets("AI", ai_text)

        if is_closing:
            st.session_state.closed = True
        else:
            st.session_state.follow_up_count += 1

        st.rerun()
else:
    st.success("대화가 종료되었어요. 소중한 의견 감사합니다! 🙏")
