import os
import time

from service.worker import PredictionService

def percentile(values, p):
    ordered = sorted(values)
    index = max(0, -(-len(ordered) * p // 100) - 1)  # nearest-rank method
    return ordered[int(index)]

def run(rate, failure_rate, fsync, seconds=5):
    if os.path.exists("load.log"):
        os.remove("load.log")
    service = PredictionService(workers=8, max_queue=1000, fsync=fsync,
                                failure_rate=failure_rate, wal_path="load.log")
    total = rate * seconds
    begin = time.perf_counter()
    for i in range(total):
        delay = begin + i / rate - time.perf_counter()
        if delay > 0:
            time.sleep(delay)  # sleeping lets the workers run
        service.submit(i, {"features": [1, 2, 3]})
    service.stop()
    elapsed = time.perf_counter() - begin

    ok = sum(r["status"] == "ok" for r in service.results.values())
    print(f"\ntarget={rate}/s failures={failure_rate:.0%} fsync={fsync}")
    print(f"sent={total} ok={ok} lost={total - len(service.results)} "
          f"unfinished={len(service.wal.pending())} retries={service.retries}")
    print(f"achieved={total / elapsed:.0f}/s")
    for p in (50, 90, 99, 99.9):
        print(f"P{p}={percentile(service.latencies, p) / 1000:.2f} ms")

for fsync in (True, False):
    for failure_rate in (0.0, 0.3):
        for rate in (1000, 10000):
            run(rate, failure_rate, fsync)