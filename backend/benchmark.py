"""Measure the running catalog API; no catalog or history records are modified."""
import argparse
import asyncio
import getpass
import json
import math
import statistics
import time
import httpx

async def run(args):
    password = getpass.getpass("Password: ")
    async with httpx.AsyncClient(base_url=args.url, timeout=30) as client:
        response = await client.post("/api/auth/login",json={"username":args.username,"password":password})
        response.raise_for_status()
        try:
            for concurrency in args.concurrency:
                gate = asyncio.Semaphore(concurrency)
                timings, errors = [], []
                async def request():
                    async with gate:
                        start = time.perf_counter()
                        try:
                            result = await client.get("/api/catalog",params={"limit":24,"q":args.query})
                            result.raise_for_status()
                            timings.append((time.perf_counter()-start)*1000)
                        except Exception as exc:
                            errors.append(type(exc).__name__)
                start = time.perf_counter()
                await asyncio.gather(*(request() for _ in range(args.requests)))
                elapsed = time.perf_counter()-start
                ordered = sorted(timings)
                print(json.dumps({"concurrency":concurrency,"requests":args.requests,
                    "errors":len(errors),"successful_requests_per_second":round(len(timings)/elapsed,2),
                    "median_ms":round(statistics.median(timings),2) if timings else None,
                    "p95_ms":round(ordered[math.ceil(.95*len(ordered))-1],2) if ordered else None}))
        finally:
            await client.post("/api/auth/logout")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",default="http://127.0.0.1:8000")
    parser.add_argument("--username",required=True)
    parser.add_argument("--requests",type=int,default=200)
    parser.add_argument("--concurrency",type=int,nargs="+",default=[1,10,25])
    parser.add_argument("--query",default="")
    args = parser.parse_args()
    if args.requests<1 or any(value<1 for value in args.concurrency):
        parser.error("Requests and concurrency must be positive.")
    asyncio.run(run(args))
