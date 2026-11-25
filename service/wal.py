import json
import os
import threading

class WriteAheadLog:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.file = open(path, "a", encoding="utf-8")

    def append(self, record):
        with self.lock:
            self.file.write(json.dumps(record) + "\n")
            self.file.flush()
            os.fsync(self.file.fileno())  # force it onto the disk

    def pending(self):
        """Requests that were accepted but never finished."""
        waiting = {}
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue  # half-written line after a crash
                if record["type"] == "accepted":
                    waiting[record["id"]] = record["features"]
                else:
                    waiting.pop(record["id"], None)
        return waiting

    def close(self):
        self.file.close()