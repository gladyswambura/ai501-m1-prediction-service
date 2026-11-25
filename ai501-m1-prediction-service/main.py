from service.worker import PredictionService

service = PredictionService(workers=4)

for i in range(10):
    features = "hello" if i == 5 else [i, i + 1]
    service.submit(i, {"features": features})

service.stop()

for request_id in sorted(service.results):
    print(request_id, service.results[request_id])