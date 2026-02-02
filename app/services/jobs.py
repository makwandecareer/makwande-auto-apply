import requests, os

def fetch_jobs(q):
    return {
        "query": q,
        "results": [
            {"title":"Engineer","company":"Demo Corp","source":"adzuna"},
            {"title":"Developer","company":"Remote Inc","source":"remotive"}
        ]
    }