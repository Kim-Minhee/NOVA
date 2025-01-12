import os, re
from dotenv import load_dotenv
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import Chroma

load_dotenv()
gemini_api_key = os.getenv('GOOGLE_API_KEY')

# 논문 내용 추출 함수
def extract_info(text):

    # 타이틀(Title) 추출
    title_pattern = r"arXiv:.*\n(.*?)\n"
    title_match = re.search(title_pattern, text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "제목을 찾을 수 없습니다."

    # # 요약(Abstract) 추출
    abstract_pattern = r"Abstract\s*(.*?)(?=\n[1-9]+\s+[A-Za-z]|\n[A-Z][a-z])"
    abstract_match = re.search(abstract_pattern, text, re.DOTALL)
    abstract = abstract_match.group(1).strip() if abstract_match else "요약을 찾을 수 없습니다."

    # 결론(Conclusion) 추출
    conclusion_pattern = r"(?<=\n)(\d+\s)?(Conclusion|Concluding(?:\s\w+)?)\s*(.*?)(?=\n[A-Z][a-z]+|\Z)"
    conclusion_match = re.search(conclusion_pattern, text, re.DOTALL)
    conclusion = conclusion_match.group(3).strip() if conclusion_match else "결론을 찾을 수 없습니다."

    return title, abstract, conclusion

# 논문 ID 추출
def extract_arxiv_id(page_content):
    arxiv_id_start = page_content.find("arXiv_ID:") + len("arXiv_ID:")
    arxiv_id = page_content[arxiv_id_start:].split()[0].strip()  # 첫 번째 공백 전까지 추출
    return arxiv_id if arxiv_id else "없음"

# 논문 제목 추출
def extract_title(page_content):
    title_start = page_content.find("Title:") + len("Title:")
    title_end = page_content.find("Year:")  
    title = page_content[title_start:title_end].strip()
    return title if title else "없음"

# 논문 요약 추출
def extract_abstract(page_content):
    abstract_start = page_content.find("Abstract:") + len("Abstract:")
    abstract_end = page_content.find("Conclusion:")  
    abstract = page_content[abstract_start:abstract_end].strip()
    return abstract if abstract else "없음"

# 논문 결론 추출
def extract_conclusion(page_content):
    conclusion_start = page_content.find("Conclusion:") + len("Conclusion:")
    conclusion = page_content[conclusion_start:].strip()
    return conclusion if conclusion else "없음"

# RAG 활용
def use_rag(user_query):
    try:
        emb_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.environ["GOOGLE_API_KEY"],
        )

        vector_store = Chroma(
            # persist_directory 경로 설정
            persist_directory="nova/database", 
            embedding_function=emb_model
        )

        retriever = vector_store.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": 5, "fetch_k": 10}
        )

        documents = retriever.get_relevant_documents(user_query)

        dict_response = {}
        if documents:
            document = documents[0]  # 첫 번째 검색 결과 문서
            dict_response = {
                "Title": extract_title(document.page_content),
                "Abstract": extract_abstract(document.page_content),
                "Conclusion": extract_conclusion(document.page_content),
                "arXiv_id": extract_arxiv_id(document.page_content)
            }
        return dict_response        

    except Exception as e:
        print(f"오류 발생: {e}")
        return "죄송합니다. 요청을 처리하는 중 문제가 발생했습니다."