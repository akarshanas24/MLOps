import requests
import time

BASE = "http://127.0.0.1:8000"

def ingest(paths):
    r = requests.post(f"{BASE}/ingest", json={"paths": paths})
    print(r.json())

def query(q):
    r = requests.post(f"{BASE}/query", json={"query": q})
    print(r.json())

if __name__ == '__main__':
    # Example usage: start server, then run this script
    # ingest sample files (adjust paths)
    # ingest(["/path/to/PM-KISAN.pdf"])
    time.sleep(0.5)
    query("Any subsidy for rice farming?")
