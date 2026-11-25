from collections import Counter

from service.worker import PredictionService

service = PredictionService(workers=4, failure_rate=0.3)

for i in range(100):
    features = "hello" if i == 5 else [i, i + 1]
    service.submit(i, {"features": features})

service.stop()

print(Counter(result["status"] for result in service.results.values()))
print("retries:", service.retries)
print("unfinished:", len(service.wal.pending()))