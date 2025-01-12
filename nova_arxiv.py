import arxiv
import os
import re
import tarfile
import pandas as pd
import shutil

# 논문 내용 추출 함수 - 요약 및 결론 후처리
def clean_text(text):
    if text is None:
        return None

    # LaTeX 명령어들 제거
    text = re.sub(r"\\(emph|textbf|url|textcolor|textsuperscript|[a-zA-Z]+)\{.*?\}", "", text)  # LaTeX 명령어 제거

    # 중괄호 {} 안의 내용 제거
    text = re.sub(r"\{(.*?)\}", "", text)  # {} 안의 내용 제거 (Deep reinforcement learning)

    # 괄호 () 안의 내용 제거
    text = re.sub(r"\((.*?)\)", "", text)  # () 안의 내용 제거 (RL)

    # \begin{...}와 \end{...} 환경 제거
    text = re.sub(r"\\begin\{.*?\}|\\end\{.*?\}", "", text)  # \begin{...}, \end{...} 제거

    # LaTeX에서 사용하는 다른 명령어들 제거 (\, \,, \text{ 등)
    text = re.sub(r"\\[a-zA-Z]+", "", text)  # 남아있는 \ 명령어 제거

    # %로 시작하는 주석 제거
    text = re.sub(r"%.*?$", "", text, flags=re.MULTILINE)  # %로 시작하는 주석 제거

    # 불필요한 공백 제거
    text = re.sub(r"\s*\.\s*\}", "", text)  # . } 같은 구문 제거
    text = re.sub(r"\s*\}", "", text)  # 남은 } 제거
    text = re.sub(r"\s+", " ", text).strip()  # 다중 공백을 단일 공백으로 변경

    return text

# 논문 내용 추출 함수 - 저자 후처리
def clean_authors(authors_text):

    if authors_text is None:
        return []
    
    # 저자 내용 중 불필요 내용 제거
    authors_text = re.sub(r"%.*?$", "", authors_text, flags=re.MULTILINE) # %로 시작하는 주석 제거
    authors_text = re.sub(r"\\thanks\{.*?\}", "", authors_text) # 감사 문구 제거
    authors_text = re.sub(r"\\textsuperscript\{.*?\}", "", authors_text) # \textsuperscript 제거
    authors_text = re.sub(r"\\and", ",", authors_text) # and를 쉼표로 변경
    authors_text = re.sub(r"\\[a-zA-Z]+", "", authors_text) # 남아있는 \ 명령어 제거
    authors_text = re.sub(r"[\{\}]", "", authors_text) # { } 제거
    authors = re.split(r",+", authors_text)  # 쉼표로 분할
    authors = [clean_text(author.strip()) for author in authors] # 공백 제거 및 후처리
    authors = [author for author in authors if author] # 빈 문자열 제거

    return authors

# 논문 내용 추출 함수
# download_dir 경로 설정 필요
def extract_info(arxiv_id, download_dir="nova_arxiv_papers"):
    try:
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(search.results())
        tex_file_path = os.path.join(download_dir, "main.tex")

        # 폴더 생성
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        # arXiv에서 논문 파일 다운로드
        source_file_path = paper.download_source(dirpath=download_dir)

        # tar 파일 압축 해제
        if source_file_path.endswith(".tar.gz"):
            with tarfile.open(source_file_path, "r:gz") as tar:
                tar.extractall(path=download_dir)

            # main.tex가 존재하지 않으면 -arxiv.tex 또는 _arxiv.tex 파일을 찾음
            if not os.path.exists(tex_file_path):
                # 해당 디렉토리에서 -arxiv.tex 또는 _arxiv.tex 파일을 대소문자 구분 없이 검색
                tex_files = [f for f in os.listdir(download_dir) if re.search(r"[-_arxiv_-_review]\.tex$", f, re.IGNORECASE)]
                
                if tex_files:
                    # 첫 번째 파일을 선택
                    tex_file_path = os.path.join(download_dir, tex_files[0])
            
            print(f"tex 파일 : {tex_file_path} ")
        else:
            print(f"다른 파일 형식 : {source_file_path}")
            return None

        # .tex 파일 정보 추출
        with open(tex_file_path, "r", encoding="utf-8") as f:
            content = f.read()

            # 타이틀(Title) 추출
            title_match = re.search(r"\\title\{(.*?)\}", content, re.DOTALL)
            title = title_match.group(1).strip() if title_match else None

            # 요약(Abstract) 추출
            abstract_match = None

            abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL)
            if abstract_match:
                abstract = abstract_match.group(1).strip()
            
            else:
                abstract_match = re.search(r"\\abstract\{(.*?)\}", content, re.DOTALL)

                # 추출된 요약
                if abstract_match:
                    abstract_start = abstract_match.end()
                    next_section_match = re.search(r"\\section\*?\{", content[abstract_start:])
                    if next_section_match:
                        # \section을 만나면 그 위치까지만 추출
                        abstract = content[abstract_start:abstract_start + next_section_match.start()].strip()
                    else:
                        # \section이 없다면, 끝까지 추출
                        abstract = content[abstract_start:].strip()
                else:
                    abstract = None                

            # 결론(Conclusion) 추출
            conclusion_match = re.search(r"\\section\{(.*[Cc]onclu.*)\}", content, re.IGNORECASE)

            if conclusion_match:
                conclusion_start = conclusion_match.end()
                next_section_match = re.search(r"\\section\*?\{", content[conclusion_start:])
                if next_section_match:
                    # \section을 만나면 그 위치까지만 추출
                    conclusion = content[conclusion_start:conclusion_start + next_section_match.start()].strip()
                else:
                    # \section이 없다면, 끝까지 추출
                    conclusion = content[conclusion_start:].strip()
            else:
                conclusion = None

            # 저자(Authors) 추출
            authors_match = re.search(r"\\author\{(.*?)\}", content, re.DOTALL)
            authors = authors_match.group(1).strip() if authors_match else None

            # 저자 후처리
            authors = clean_authors(authors)
        
        shutil.rmtree(download_dir)
        print("title >> ",title)
        print("abstract >> ",abstract)
        print("conclusion >> ",conclusion)

        # 요약 및 결론 후처리
        abstract = clean_text(abstract)
        conclusion = clean_text(conclusion)

        # 논문 내용 딕셔너리 생성
        result = {
            "arxiv_id": arxiv_id,
            "title": title,
            "year": paper.published.year,
            "authors": authors,
            "abstract": abstract,
            "conclusion": conclusion,
        }

        return result

    except Exception as e:
        print(f"Error: {e}")
        return None

# 논문 중복 방지 함수
# csv_file 경로 설정 필요
def check_arxiv_id(arxiv_id, csv_file="nova_arxiv_csv.csv"):
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)

        if "arXiv_ID" in df.columns:
            df["arXiv_ID"] = df["arXiv_ID"].astype(str).fillna("")

            arxiv_id = arxiv_id.strip().lower()
            existing_arxiv_ids = df["arXiv_ID"].str.strip().str.lower()

            return arxiv_id in existing_arxiv_ids.values
        else:
            print("CSV 파일에 arXiv_ID 컬럼이 없습니다.")
            return False
    return False

# 논문 내용 -> csv 파일 저장 함수
# csv_file 경로 설정 필요
def save_csv(paper_info, csv_file="nova_arxiv_csv.csv"):

    # 논문 정보
    data = {
        "arXiv_ID": paper_info["arxiv_id"],
        "Title": paper_info["title"],
        "Year": paper_info["year"],
        "Authors": ", ".join(paper_info["authors"]),
        "Abstract": paper_info["abstract"],
        "Conclusion": paper_info["conclusion"]
    }
    
    # 기존 CSV 파일 존재 확인
    if os.path.exists(csv_file):
        # 기존 파일 읽기
        df = pd.read_csv(csv_file)
    else:
        # 새로운 DataFrame 생성
        df = pd.DataFrame(columns=data.keys())

    # 새로운 행 추가
    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)

    # CSV 파일 저장
    df.to_csv(csv_file, index=False, encoding="utf-8")
    print(f"논문 정보가 {csv_file}에 저장되었습니다.")


# 논문 정보 추출 및 CSV 파일 저장 프로세스 함수
# csv_file 경로 설정 필요
def process_paper(arxiv_id, csv_file="nova_arxiv_csv.csv"):

    # 논문 중복 방지
    if check_arxiv_id(arxiv_id, csv_file):
        print(f"arXiv_ID : {arxiv_id}는 이미 CSV 파일에 존재합니다. 프로세스를 종료합니다.")
        return
    
    # 논문 정보 추출
    paper_info = extract_info(arxiv_id)
    
    # 논문 정보 있을 시
    if paper_info:
        print(f"arXiv_ID : {paper_info['arxiv_id']}")
        print(f"Title : {paper_info['title']}")
        print(f"Year : {paper_info['year']}")
        print(f"Authors : {paper_info['authors']}")
        print(f"Abstract : {paper_info['abstract']}")
        print(f"Conclusion : {paper_info['conclusion']}")    
        save_csv(paper_info, csv_file)

        # 논문 정보 초기화
        paper_info = None
    else:
        print(f"arXiv_ID : {arxiv_id}에 대한 정보를 추출 할 수 없습니다.")

# arXiv ID 입력
arxiv_id = "2501.03225"

# 프로세스 실행
# csv_file 경로 설정 필요
process_paper(arxiv_id, "nova_arxiv_csv.csv")