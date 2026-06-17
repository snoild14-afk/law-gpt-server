from fastapi import FastAPI
import requests
import os

app = FastAPI()

LAW_API_OC = os.getenv("LAW_API_OC")

@app.get("/")
def root():
    return {"message": "Law GPT Server Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
def search(query: str):

    url = "https://www.law.go.kr/DRF/lawSearch.do"

    params = {
        "OC": LAW_API_OC,
        "target": "law",
        "type": "JSON",
        "query": query
    }

    response = requests.get(url, params=params)

    return {
        "status_code": response.status_code,
        "text": response.text[:3000]
    }
