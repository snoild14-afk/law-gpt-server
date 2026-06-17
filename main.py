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

    return {
        "MST": mst,
        "status_code": response.status_code,
        "text": response.text[:5000]
    }
