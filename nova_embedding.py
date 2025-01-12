import os
import pandas as pd
from dotenv import load_dotenv
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import Chroma
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings

# 환경 변수 로드
load_dotenv()
gemini_api_key = os.getenv('GOOGLE_API_KEY')

# 논문 CSV 파일 로드
# file path 경로 설정 필요
loader = CSVLoader(
    file_path="nova_arxiv_csv.csv", encoding="utf-8"
)
pages = loader.load()

# Google Generative AI 임베딩 모델 사용
emb_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.environ["GOOGLE_API_KEY"],
)

# Chroma 벡터 저장소 생성
# persist_directory 경로 설정 필요
vectordb = Chroma.from_documents(
    pages,
    emb_model,
    persist_directory="database",
)