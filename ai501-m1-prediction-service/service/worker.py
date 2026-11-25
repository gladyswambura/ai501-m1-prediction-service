import time
import uuid
from service.logger import log_event
import queue
import threading

from service.validation import validate
from service.model import score

class PredictionService:
    def __init__(self, workers=4, max_queue=100):
        self.jobs = queue.Queue(maxsize=max_queue)
        self.results = {}
        self.lock = threading.Lock()
        self.threads = [threading.Thread(target=self._work) for _ in range(workers)]
        for thread in self.threads:
            thread.start()

    def submit(self, request_id, request):
        trace_id = str(uuid.uuid4())
        start = time.perf_counter()
        try:
            features = validate(request)
        except ValueError as error:
            result = {"status": "rejected", "reason": str(error)}
            self._save(request_id, result, 400, trace_id, start)
            return
        self.jobs.put((request_id, features, trace_id, start))

    def _work(self):
        while True:
            job = self.jobs.get()
            if job is None:
                break
            request_id, features, trace_id, start = job
            try:
                result = {"status": "ok", "score": score(features)}
                code = 200
            except Exception as error:
                result = {"status": "error", "reason": str(error)}
                code = 500
            self._save(request_id, result, code, trace_id, start)

    def _save(self, request_id, result, code, trace_id, start):
        latency_us = int((time.perf_counter() - start) * 1_000_000)
        with self.lock:
            self.results[request_id] = result
        log_event(trace_id, code, latency_us)

    def stop(self):
        for _ in self.threads:
            self.jobs.put(None)
        for thread in self.threads:
            thread.join()  # wait for the worker to finish