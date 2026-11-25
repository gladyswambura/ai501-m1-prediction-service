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
        try:
            features = validate(request)
        except ValueError as error:
            self._save(request_id, {"status": "rejected", "reason": str(error)})
            return
        self.jobs.put((request_id, features))  # waits if the queue is full

    def _work(self):
        while True:
            job = self.jobs.get()
            if job is None:  # signal to stop
                break
            request_id, features = job
            try:
                self._save(request_id, {"status": "ok", "score": score(features)})
            except Exception as error:  # one bad job must not kill the worker
                self._save(request_id, {"status": "error", "reason": str(error)})

    def _save(self, request_id, result):
        with self.lock:  # only one thread writes at a time
            self.results[request_id] = result

    def stop(self):
        for _ in self.threads:
            self.jobs.put(None)
        for thread in self.threads:
            thread.join()  # wait for the worker to finish