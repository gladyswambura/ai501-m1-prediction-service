import pytest

from service.model import score
from service.validation import validate
from service.wal import WriteAheadLog
from service.worker import PredictionService

@pytest.mark.parametrize("bad", [
    "not a dict", {}, {"features": []}, {"features": "hello"},
    {"features": [True]}, {"features": ["1"]},
    {"features": [float("nan")]}, {"features": [float("inf")]},
    {"features": [10 ** 400]},
])
def test_bad_requests_are_rejected(bad):
    with pytest.raises(ValueError):
        validate(bad)

def test_good_request_is_accepted():
    assert validate({"features": [1, 2.5]}) == [1, 2.5]

def test_score_values():
    assert score([0]) == 0.5
    assert score([1000]) == 1.0
    assert score([-1000]) == 0.0

def test_wal_skips_finished_and_broken_lines(tmp_path):
    path = tmp_path / "wal.log"
    wal = WriteAheadLog(path)
    wal.append({"type": "accepted", "id": 1, "features": [1]})
    wal.append({"type": "accepted", "id": 2, "features": [2]})
    wal.append({"type": "done", "id": 1})
    wal.file.write('{"type": "acc')
    wal.file.flush()
    assert wal.pending() == {2: [2]}
    wal.close()

def make(tmp_path, **options):
    return PredictionService(wal_path=tmp_path / "wal.log", **options)

def test_success_and_rejection(tmp_path):
    service = make(tmp_path)
    service.submit(1, {"features": [0]})
    service.submit(2, {"features": "x"})
    service.stop()
    assert service.results[1] == {"status": "ok", "score": 0.5}
    assert service.results[2]["status"] == "rejected"

def test_nothing_lost_with_30_percent_failures(tmp_path):
    service = make(tmp_path, failure_rate=0.3, fsync=False)
    for i in range(500):
        service.submit(i, {"features": [i]})
    service.stop()
    assert len(service.results) == 500
    assert all(r["status"] == "ok" for r in service.results.values())
    assert service.retries > 0
    assert service.wal.pending() == {}

def test_failed_request_can_be_recovered(tmp_path):
    first = make(tmp_path, failure_rate=1.0, max_attempts=2)
    first.submit(1, {"features": [1]})
    first.stop()
    assert first.results[1]["status"] == "error"

    second = make(tmp_path)
    assert second.recover() == 1
    second.stop()
    assert second.results[1]["status"] == "ok"
    assert second.wal.pending() == {}

def test_worker_survives_unexpected_error(tmp_path):
    service = make(tmp_path, workers=1)
    real = service._process

    def broken_once(features):
        service._process = real
        raise RuntimeError("bug")

    service._process = broken_once
    service.submit(1, {"features": [1]})
    service.submit(2, {"features": [1]})
    service.stop()
    assert service.results[2]["status"] == "ok"