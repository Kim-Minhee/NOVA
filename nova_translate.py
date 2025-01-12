import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

import re
from googletrans import Translator  # 번역 기능 추가

# 환경변수 로드(API KEY 보안용)
load_dotenv()
gemeni_key  = os.getenv("GOOGLE_API_KEY")

# API KEY 적용 및 모델 로드
genai.configure(api_key=gemeni_key)
model = genai.GenerativeModel('gemini-1.5-pro')

#후처리 함수
def clean_spacing(translated_text):
    # 여러 공백을 하나로 줄임
    cleaned_text = re.sub(r"\s+", " ", translated_text)

    # 문장 끝에 붙은 공백 제거 및 줄바꿈 처리
    cleaned_text = re.sub(r"\s([,.!?])", r"\1", cleaned_text)  # , . ! ? 앞의 공백 제거
    cleaned_text = re.sub(r"([.!?])\s+", r"\1\n", cleaned_text)  # 문장 끝 뒤에 줄바꿈 추가
    cleaned_text = re.sub(r"(\n\s+)", "\n", cleaned_text)  # 불필요한 공백 제거

    return cleaned_text.strip()

#번역함수 정의
def extract_and_translate(input_text, target_language="ko"):
    # 번역기 초기화
    translator = Translator()

    # 번역 요청 문구 제거 및 영어만 추출
    pattern = r"(?:다음을 번역해줘[:：]?\s*|번역[:：]?\s*)?([A-Za-z].+)"
    match = re.search(pattern, input_text, re.DOTALL)

    if match:
        english_text = match.group(1).strip()
        try:
            # 제목 감지
            title_pattern = r"^\s*(Abstract|Conclusion)\b"
            title_match = re.match(title_pattern, english_text, re.IGNORECASE)
            translated_title = ""

            if title_match:
                # 제목 번역 및 줄바꿈 추가
                title = title_match.group(1).lower()
                translated_title = "초록<br><br>" if title == "abstract" else "결론<br><br>"
                
                # 제목 제거
                english_text = english_text[len(title_match.group(0)):].strip()

            # 약어 처리: 약어 뒤에 붙은 점을 공백으로 대체
            english_text = re.sub(r"\b(Dr|Mr|Ms|Inc|Ltd|Etc)\.", r"\1 ", english_text)

            # 문장 분리
            sentences = re.split(r"(?<=[.!?])\s+", english_text)

            # 각 문장 번역
            translated_sentences = []
            for sentence in sentences:
                # 문장 정리
                cleaned_sentence = re.sub(r"(?<![.!?])\n", " ", sentence.strip())
                cleaned_sentence = re.sub(r"\s+", " ", cleaned_sentence).strip()

                if cleaned_sentence:  # 빈 문장은 제외
                    try:
                        translated = translator.translate(cleaned_sentence, dest=target_language).text
                        translated_sentences.append(translated)
                    except Exception as e:
                        translated_sentences.append(f"[번역 오류: {sentence}]")

            translated_text = translated_title + " ".join(translated_sentences)
            return clean_spacing(translated_text)
        except Exception as e:
            return f"번역 중 오류 발생: {e}"
    else:
        return "번역할 영어 문장을 찾을 수 없습니다."

#사이드 바(파일 업로드)
with st.sidebar:
    uploaded_file = st.sidebar.file_uploader("번역 및 요약이 필요한 논문 PDF파일", type=["pdf"])

# 대화 내역 초기화
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# 대화 내역 표시
for message in st.session_state["chat_history"]:
    with st.chat_message("ai" if message["role"] == "ai" else "user"):
        st.markdown(message["text"])


if prompt := st.chat_input("Hi, Nova"):

    # 사용자 입력을 대화 내역에 추가
    st.session_state["chat_history"].append({"role": "user", "text": prompt})

    # 유지 대화 출력
    with st.chat_message("user"):
        st.markdown(prompt)

    # 번역 요청 처리
    if re.search(r"(?:다음을 번역해줘[:：]?\s*|번역[:：]?\s*)", prompt, re.DOTALL):  # 번역 요청 감지
        # st.write("번역 요청 감지됨: extract_and_translate 함수 호출")
        try:
            translated_result = extract_and_translate(prompt)
            st.session_state["chat_history"].append(
                {"role": "ai", "text": translated_result.replace("<br>", "\n")})
            with st.chat_message("ai"):
                # st.markdown(f"[googletrans 사용]")
                st.markdown(translated_result, unsafe_allow_html=True)

        except Exception as e:
            st.session_state["chat_history"].append({"role": "ai", "text": f"번역 중 오류 발생: {e}"})
            with st.chat_message("ai"):
                st.error(f"번역 중 오류 발생: {e}")
    else:
        # 일반 대화 처리
        try:
            response = model.start_chat().send_message(prompt)
            st.session_state["chat_history"].append({"role": "ai", "text": f"{response.text}"})
            with st.chat_message("ai"):
                st.markdown(f"{response.text}")
        except Exception as e:
            st.session_state["chat_history"].append({"role": "ai", "text": f"에러 발생: {e}"})
            with st.chat_message("ai"):
                st.error(f"에러 발생: {e}")
