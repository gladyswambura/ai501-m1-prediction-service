import queue
import random
import threading
import time
import uuid

from service.logger import log_event
from service.model import score
from service.validation import validate
from service.wal import WriteAheadLog

class PredictionService:
    def __init__(self, workers=4, max_queue=100, failure_rate=0.0,
                 max_attempts=20, wal_path="wal.log", fsync=True):
        self.jobs = queue.Queue(maxsize=max_queue)
        self.results = {}
        self.retries = 0
        self.failure_rate = failure_rate
        self.max_attempts = max_attempts
        self.wal = WriteAheadLog(wal_path, fsync)
        self.latencies = []
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
        # Write it down BEFORE doing the work
        self.wal.append({"type": "accepted", "id": request_id, "features": features})
        self.jobs.put((request_id, features, trace_id, start))

    def recover(self):
        """Queue again everything that was not finished last time."""
        waiting = self.wal.pending()
        for request_id, features in waiting.items():
            self.jobs.put((request_id, features, str(uuid.uuid4()), time.perf_counter()))
        return len(waiting)

    def _process(self, features):
        if random.random() < self.failure_rate:  # failure injection
            raise ConnectionError("simulated failure")
        return score(features)

    def _work(self):
        while True:
            job = self.jobs.get()
            if job is None:
                break
            try:
                self._handle(*job)
            except Exception as error:  # keep the worker alive
                print("unexpected error:", error)

    def _handle(self, request_id, features, trace_id, start):
        for attempt in range(self.max_attempts):
            try:
                value = self._process(features)
            except ConnectionError:
                log_event(trace_id, 503, int((time.perf_counter() - start) * 1_000_000))
                with self.lock:
                    self.retries += 1
                # exponential backoff with jitter
                time.sleep(random.uniform(0, min(0.05, 0.001 * 2 ** attempt)))
                continue
            self.wal.append({"type": "done", "id": request_id})
            self._save(request_id, {"status": "ok", "score": value}, 200, trace_id, start)
            return
        # Not marked done, so recover() will try it again
        result = {"status": "error", "reason": "all attempts failed"}
        self._save(request_id, result, 500, trace_id, start)

    def _save(self, request_id, result, code, trace_id, start):
        latency_us = int((time.perf_counter() - start) * 1_000_000)
        with self.lock:
            self.results[request_id] = result
            self.latencies.append(latency_us)
        log_event(trace_id, code, latency_us)

    def stop(self):
        for _ in self.threads:
            self.jobs.put(None)
        for thread in self.threads:
            thread.join()
        self.wal.close()