from fastapi import FastAPI
import requests
import os
from urllib.parse import urlparse, parse_qs

app = FastAPI()

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
