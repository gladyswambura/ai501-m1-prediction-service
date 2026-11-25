import os
import sys

from service.worker import PredictionService

if sys.argv[1] == "crash":
    if os.path.exists("crash.log"):
        os.remove("crash.log")
    service = PredictionService(workers=0, wal_path="crash.log")
    for i in range(10):
        service.submit(i, {"features": [i]})
    print("accepted 10 requests, now crashing")
    sys.stdout.flush()
    os._exit(1)  # stop suddenly, like a power cut

service = PredictionService(wal_path="crash.log")
print("recovered:", service.recover())
service.stop()
print("finished:", len(service.results))
print("unfinished:", len(service.wal.pending()))