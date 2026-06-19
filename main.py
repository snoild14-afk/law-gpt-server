import re
from fastapi import FastAPI
import requests
import os
from urllib.parse import urlparse, parse_qs

app = FastAPI(
    title="Law GPT Server",
    version="1.0",
    servers=[
        {
            "url": "https://law-gpt-server.onrender.com"
        }
    ]
)

LAW_API_OC = os.getenv("LAW_API_OC")


@app.get("/")
def root():
    return {"message": "Law GPT Server Running"}


@app.get("/health")
def health():
    return {"status": "ok"}


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_mst(detail_link: str):
    if not detail_link:
        return None
    parsed = urlparse(detail_link)
    query = parse_qs(parsed.query)
    mst = query.get("MST")
    return mst[0] if mst else None


@app.get("/search")
def search(query: str, target: str = "law"):
    url = "https://www.law.go.kr/DRF/lawSearch.do"

    params = {
        "OC": LAW_API_OC,
        "target": target,
        "type": "JSON",
        "query": query,
        "display": 10,
        "page": 1
    }

    response = requests.get(url, params=params)
    data = response.json()

    law_search = data.get("LawSearch", {})
    raw_items = law_search.get("law", [])

    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    results = []

    for item in raw_items:
        detail_link = item.get("법령상세링크")
        mst = extract_mst(detail_link)

        results.append({
            "법령명": item.get("법령명한글"),
            "법령ID": item.get("법령ID"),
            "MST": mst,
            "공포번호": item.get("공포번호"),
            "공포일자": item.get("공포일자"),
            "시행일자": item.get("시행일자"),
            "소관부처": item.get("소관부처명"),
            "법령상세링크": detail_link
        })

    return {
        "검색어": query,
        "검색대상": target,
        "결과수": law_search.get("totalCnt"),
        "결과": results
    }


@app.get("/law-detail")
def law_detail(mst: str):
    url = "https://www.law.go.kr/DRF/lawService.do"

    params = {
        "OC": LAW_API_OC,
        "target": "law",
        "type": "JSON",
        "MST": mst
    }

    response = requests.get(url, params=params)
    data = response.json()

    law = data.get("법령", {})
    basic = law.get("기본정보", {})

    articles_raw = (
        law.get("조문", {})
        .get("조문단위", [])
    )

    articles = []

    for article in ensure_list(articles_raw):
        articles.append({
            "조문키": article.get("조문키"),
            "조문번호": article.get("조문번호"),
            "조문가지번호": article.get("조문가지번호"),
            "조문여부": article.get("조문여부"),
            "조문제목": article.get("조문제목"),
            "조문시행일자": article.get("조문시행일자"),
            "조문내용": article.get("조문내용"),
            "항": article.get("항")
        })

    department = basic.get("소관부처")
    if isinstance(department, dict):
        department_name = department.get("content")
    else:
        department_name = department

    return {
        "MST": mst,
        "법령명": basic.get("법령명_한글"),
        "법령ID": basic.get("법령ID"),
        "공포번호": basic.get("공포번호"),
        "공포일자": basic.get("공포일자"),
        "시행일자": basic.get("시행일자"),
        "소관부처": department_name,
        "조문수": len(articles),
        "조문": articles
    }


@app.get("/law-article")
def law_article(mst: str, article: str):
    detail = law_detail(mst)
    articles = detail.get("조문", [])

    matched = []

    for item in articles:
        article_no = str(item.get("조문번호", ""))
        article_branch = item.get("조문가지번호")

        full_no = article_no
        if article_branch:
            full_no = f"{article_no}의{article_branch}"

        if (
            article_no == article
            or full_no == article
            or item.get("조문내용", "").startswith(f"제{article}조")
            or item.get("조문내용", "").startswith(f"제{article}조의")
        ) and item.get("조문여부") == "조문":
            matched.append(item)

    return {
        "MST": mst,
        "법령명": detail.get("법령명"),
        "검색조문": article,
        "결과수": len(matched),
        "결과": matched
    }

@app.get("/interpretation-search")
def interpretation_search(query: str):
    url = "https://www.law.go.kr/DRF/lawSearch.do"

    params = {
        "OC": LAW_API_OC,
        "target": "expc",
        "type": "JSON",
        "query": query,
        "display": 10,
        "page": 1
    }

    response = requests.get(url, params=params)
    data = response.json()

    search_data = data.get("Expc", {})
    raw_items = search_data.get("expc", [])

    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    results = []

    for item in raw_items:
        results.append({
            "안건명": item.get("안건명"),
            "안건번호": item.get("안건번호"),
            "회신일자": item.get("회신일자"),
            "질의기관": item.get("질의기관명"),
            "해석기관": item.get("회신기관명"),
            "상세링크": item.get("법령해석례상세링크"),
            "원본필드": item
        })

    return {
        "검색어": query,
        "검색대상": "법령해석례",
        "결과수": search_data.get("totalCnt"),
        "결과": results
    }

@app.get("/precedent-search")
def precedent_search(query: str):
    url = "https://www.law.go.kr/DRF/lawSearch.do"

    params = {
        "OC": LAW_API_OC,
        "target": "prec",
        "type": "JSON",
        "query": query,
        "display": 10,
        "page": 1
    }

    response = requests.get(url, params=params)
    data = response.json()

    search_data = data.get("PrecSearch", {})
    raw_items = search_data.get("prec", [])

    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    results = []

    for item in raw_items:
        results.append({
            "사건명": item.get("사건명"),
            "사건번호": item.get("사건번호"),
            "선고일자": item.get("선고일자"),
            "법원명": item.get("법원명"),
            "사건종류": item.get("사건종류명"),
            "판례일련번호": item.get("판례일련번호"),
            "상세링크": item.get("판례상세링크"),
            "원본": item
        })

    return {
        "검색어": query,
        "검색대상": "판례",
        "결과수": search_data.get("totalCnt"),
        "결과": results
    }

@app.get("/tax-appeal-search")
def tax_appeal_search(query: str, case_no: str = "", pages: int = 5):
    url = "https://www.law.go.kr/DRF/lawSearch.do"

    def normalize(text):
        if not text:
            return ""
        return re.sub(r"[\s\-]", "", str(text))

    if not case_no and re.search(r"조심\s*\d{4}[가-힣]\d+", query):
        case_no = query

    normalized_case_no = normalize(case_no)

    search_keywords = list(dict.fromkeys([
        query,
        normalize(query),
        case_no,
        normalize(case_no),
        query.replace(" ", ""),
        query.replace("조심", "조심 ")
    ]))

    all_results = []
    seen_ids = set()

    for keyword in search_keywords:
        if not keyword:
            continue

        for page in range(1, pages + 1):
            params = {
                "OC": LAW_API_OC,
                "target": "ttSpecialDecc",
                "type": "JSON",
                "query": keyword,
                "display": 100,
                "page": page
            }

            response = requests.get(url, params=params)
            data = response.json()

            search_data = data.get("Decc", {})
            raw_items = search_data.get("decc", [])

            if isinstance(raw_items, dict):
                raw_items = [raw_items]

            for item in raw_items:
                appeal_id = item.get("특별행정심판재결례일련번호")
                if not appeal_id:
                    continue

                detail_link = item.get("행정심판재결례상세링크", "")
                safe_link = detail_link.replace(LAW_API_OC, "***") if LAW_API_OC else detail_link

                result_item = {
                    "일련번호": appeal_id,
                    "청구번호": item.get("청구번호"),
                    "사건명": item.get("사건명"),
                    "재결청": item.get("재결청"),
                    "재결구분": item.get("재결구분명"),
                    "의결일자": item.get("의결일자"),
                    "처분일자": item.get("처분일자"),
                    "데이터기준일시": item.get("데이터기준일시"),
                    "상세링크": safe_link,
                    "공식출처": "국가법령정보센터 조세심판례"
                }

                current_case_no = normalize(item.get("청구번호"))

                if normalized_case_no and current_case_no == normalized_case_no:
                    return {
                        "검색어": query,
                        "사건번호검색": case_no,
                        "검색페이지수": page,
                        "전체결과수": 1,
                        "정확일치수": 1,
                        "정확일치결과": [result_item],
                        "결과": [result_item]
                    }

                if appeal_id in seen_ids:
                    continue

                seen_ids.add(appeal_id)
                all_results.append(result_item)

    return {
        "검색어": query,
        "사건번호검색": case_no,
        "검색페이지수": pages,
        "전체결과수": len(all_results),
        "정확일치수": 0,
        "정확일치결과": [],
        "결과": all_results[:30]
    }

@app.get("/tax-appeal-smart-search")
def tax_appeal_smart_search(query: str, pages: int = 2, max_keywords: int = 15, limit: int = 20):
    def make_keywords(text):
        text = text.strip()

        stopwords = {
            "경우", "여부", "대한", "따른", "적용", "관련", "대상",
            "있는", "없는", "하여", "하고", "또는", "및", "그", "이",
            "것", "수", "볼", "하는", "한", "의", "를", "을", "가", "이",
            "청구법인이", "아닌", "에게", "인지"
        }

        words = re.findall(r"[가-힣A-Za-z0-9]+", text)
        words = [w for w in words if len(w) >= 2 and w not in stopwords]

        important_words = []
        for w in words:
            if w not in important_words:
                important_words.append(w)

        keywords = [
            text,
            text.replace(" ", "")
        ]

        article_matches = re.findall(r"제\s*\d+조(?:의\s*\d+)?", text)
        for article in article_matches:
            article_clean = article.replace(" ", "")
            keywords.insert(0, article_clean)

            if "지방세특례제한법" in text:
                keywords.insert(0, f"지방세특례제한법 {article_clean}")
            if "지방세법" in text:
                keywords.insert(0, f"지방세법 {article_clean}")
            if "지방세징수법" in text:
                keywords.insert(0, f"지방세징수법 {article_clean}")

        # 핵심어 2~3개 조합을 단일어보다 먼저
        for i in range(len(important_words)):
            for j in range(i + 1, min(i + 5, len(important_words))):
                keywords.append(f"{important_words[i]} {important_words[j]}")

        for i in range(len(important_words)):
            for j in range(i + 1, min(i + 4, len(important_words))):
                for k in range(j + 1, min(j + 4, len(important_words))):
                    keywords.append(f"{important_words[i]} {important_words[j]} {important_words[k]}")

        # 단일어는 뒤로
        for w in important_words:
            keywords.append(w)

        return list(dict.fromkeys([k for k in keywords if k]))

    def score_item(item, original_query):
        title = item.get("사건명") or ""
        case_no = item.get("청구번호") or ""
        used_keyword = item.get("검색에사용된키워드") or ""

        words = re.findall(r"[가-힣A-Za-z0-9]+", original_query)
        words = [w for w in words if len(w) >= 2]

        score = 0

        # 사건명에 원문 핵심어가 많이 들어갈수록 가점
        for w in words:
            if w in title:
                score += 3

        # 사용된 검색어가 길수록 가점
        score += min(len(used_keyword), 30) / 3

        # 법령 조문 직접 관련 가점
        if "제31조의5" in title or "제31조의5" in used_keyword:
            score += 20

        # 지방세 사건 우대
        if "지" in case_no:
            score += 10

        # 정확 쟁점어 가점
        bonus_terms = ["오피스텔", "공공주택사업자", "취득세", "감면", "경감", "제31조의5"]
        for term in bonus_terms:
            if term in title:
                score += 10

        return score

    keywords = make_keywords(query)[:max_keywords]

    results_by_id = {}

    for keyword in keywords:
        result = tax_appeal_search(query=keyword, pages=pages)
        for item in result.get("결과", []):
            appeal_id = item.get("일련번호")
            if not appeal_id:
                continue

            item["검색에사용된키워드"] = keyword
            item["관련도점수"] = score_item(item, query)

            if appeal_id not in results_by_id:
                results_by_id[appeal_id] = item
            else:
                if item["관련도점수"] > results_by_id[appeal_id].get("관련도점수", 0):
                    results_by_id[appeal_id] = item

    sorted_results = sorted(
        results_by_id.values(),
        key=lambda x: x.get("관련도점수", 0),
        reverse=True
    )

    return {
        "원검색어": query,
        "생성검색어수": len(keywords),
        "생성검색어": keywords,
        "결과수": len(sorted_results),
        "결과": sorted_results[:limit]
    }

@app.get("/tax-appeal-find")
def tax_appeal_find(query: str, pages: int = 2, max_keywords: int = 15, limit: int = 10):
    search_result = tax_appeal_smart_search(
        query=query,
        pages=pages,
        max_keywords=max_keywords,
        limit=limit
    )

    results = search_result.get("결과", [])

    if not results:
        return {
            "원검색어": query,
            "찾음": False,
            "메시지": "국가법령정보센터 조세심판례 공개 DB에서 유사 조세심판례를 확인하지 못했습니다.",
            "공식출처": "국가법령정보센터 조세심판례"
        }

    representative = results[0]
    representative_id = representative.get("일련번호")

    representative_summary = None
    if representative_id:
        representative_summary = tax_appeal_summary(representative_id)

    similar_cases = []

    for item in results[1:6]:
        similar_cases.append({
            "청구번호": item.get("청구번호"),
            "일련번호": item.get("일련번호"),
            "의결일자": item.get("의결일자"),
            "사건명": item.get("사건명"),
            "관련도점수": item.get("관련도점수"),
            "검색에사용된키워드": item.get("검색에사용된키워드"),
            "공식출처": item.get("공식출처")
        })
    distinguishable_cases = []

   for item in results[1:10]:
        title = item.get("사건명") or ""

        if any(word in title for word in [
            "부인", "추징", "제외", "기각",
            "해당하지", "볼 수 없는"
    ]):
            distinguishable_cases.append({
                "청구번호": item.get("청구번호"),
                "일련번호": item.get("일련번호"),
                "의결일자": item.get("의결일자"),
                "사건명": title,
                "관련도점수": item.get("관련도점수"),
                "공식출처": item.get("공식출처")
            })
        
    return {
    "원검색어": query,
    "찾음": True,
    "공식출처": "국가법령정보센터 조세심판례",

    "대표사례": {
        ...
    },

    "유사사례": similar_cases,

    "구별사례후보": distinguishable_cases[:3],

    "전체검색결과수": search_result.get("결과수")
}
    
from bs4 import BeautifulSoup

@app.get("/tax-appeal-case")
def tax_appeal_case(case_no: str, pages: int = 10):
    search_result = tax_appeal_search(query=case_no, case_no=case_no, pages=pages)

    exact_results = search_result.get("정확일치결과", [])

    if not exact_results:
        return {
            "사건번호": case_no,
            "찾음": False,
            "메시지": "정확히 일치하는 조세심판례를 찾지 못했습니다.",
            "유사결과수": search_result.get("전체결과수"),
            "유사결과": search_result.get("결과", [])[:10]
        }

    first = exact_results[0]
    appeal_id = first.get("일련번호")

    detail = tax_appeal_detail(appeal_id)

    return {
        "사건번호": case_no,
        "찾음": True,
        "일련번호": appeal_id,
        "검색결과": first,
        "상세": detail
    }

@app.get("/precedent-detail")
def precedent_detail(id: str):
    url = "https://www.law.go.kr/DRF/lawService.do"

    params = {
        "OC": LAW_API_OC,
        "target": "prec",
        "ID": id,
        "type": "JSON"
    }

    response = requests.get(url, params=params)
    data = response.json()

    detail = data.get("PrecService", {})

    return {
        "판례일련번호": detail.get("판례정보일련번호"),
        "사건명": detail.get("사건명"),
        "사건번호": detail.get("사건번호"),
        "법원명": detail.get("법원명"),
        "선고일자": detail.get("선고일자"),
        "판결유형": detail.get("판결유형"),
        "사건종류": detail.get("사건종류명"),
        "판시사항": detail.get("판시사항"),
        "판결요지": detail.get("판결요지"),
        "참조조문": detail.get("참조조문"),
        "참조판례": detail.get("참조판례"),
        "판례내용": detail.get("판례내용")
    }

from bs4 import BeautifulSoup

@app.get("/interpretation-detail")
def interpretation_detail(id: str):
    url = "https://www.law.go.kr/DRF/lawService.do"

    params = {
        "OC": LAW_API_OC,
        "target": "expc",
        "ID": id,
        "type": "JSON"
    }

    response = requests.get(url, params=params)

    return {
        "요청URL": response.url.replace(LAW_API_OC, "***"),
        "status_code": response.status_code,
        "text": response.text[:15000]
    }

@app.get("/tax-appeal-detail")
def tax_appeal_detail(id: str):
    url = "https://www.law.go.kr/DRF/lawService.do"

    params = {
        "OC": LAW_API_OC,
        "target": "ttSpecialDecc",
        "ID": id,
        "type": "JSON"
    }

    response = requests.get(url, params=params)
    data = response.json()

    detail = data.get("SpecialDeccService", {})

    return {
        "일련번호": detail.get("특별행정심판재결례일련번호"),
        "사건명": detail.get("사건명"),
        "재결청": detail.get("재결청"),
        "세목": detail.get("세목"),
        "의결일자": detail.get("의결일자"),
        "처분일자": detail.get("처분일자"),
        "주문": detail.get("주문"),
        "재결요지": detail.get("재결요지"),
        "관련법령": detail.get("관련법령"),
        "참조결정": detail.get("참조결정"),
        "따른결정": detail.get("따른결정"),
        "이유": detail.get("이유")
    }

@app.get("/tax-appeal-summary")
def tax_appeal_summary(id: str):
    url = "https://www.law.go.kr/DRF/lawService.do"

    params = {
        "OC": LAW_API_OC,
        "target": "ttSpecialDecc",
        "ID": id,
        "type": "JSON"
    }

    response = requests.get(url, params=params)
    data = response.json()

    detail = data.get("SpecialDeccService", {})

    return {
        "사건명": detail.get("사건명"),
        "세목": detail.get("세목"),
        "의결일자": detail.get("의결일자"),
        "재결요지": detail.get("재결요지"),
        "주문": detail.get("주문"),
        "관련법령": detail.get("관련법령")
    }

@app.get("/interpretation-summary")
def interpretation_summary(id: str):
    url = "https://www.law.go.kr/DRF/lawService.do"

    params = {
        "OC": LAW_API_OC,
        "target": "expc",
        "ID": id,
        "type": "JSON"
    }

    response = requests.get(url, params=params)
    data = response.json()

    detail = data.get("ExpcService", {})

    return {
        "안건명": detail.get("안건명"),
        "질의요지": detail.get("질의요지"),
        "회답": detail.get("회답"),
        "해석일자": detail.get("해석일자")
    }
