import threading
import queue
import uuid
from typing import Any, Callable, Dict, Tuple

_q: queue.Queue[Tuple[str, Callable[..., Any], tuple, dict]] | None = None
_jobs: Dict[str, Dict[str, Any]] = {}
_workers: list[threading.Thread] = []
_alive = False


def init_job_queue(max_workers: int) -> None:
    global _q, _workers, _alive
    if _alive:
        return
    _q = queue.Queue()
    _alive = True
    _workers = []
    for _ in range(max_workers):
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        _workers.append(t)


def submit(func: Callable[..., Any], *args, **kwargs) -> str:
    if not _alive or _q is None:
        raise RuntimeError("Job queue not initialized")
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued", "result": None, "error": None}
    _q.put((job_id, func, args, kwargs))
    return job_id


def get_status(job_id: str) -> Dict[str, Any]:
    return _jobs.get(job_id, {"status": "not_found"})


def shutdown() -> None:
    global _alive
    _alive = False


def _worker() -> None:
    while _alive and _q is not None:
        try:
            job_id, func, args, kwargs = _q.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            _jobs[job_id]["status"] = "running"
            res = func(*args, **kwargs)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = res
        except Exception as e:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)
        finally:
            _q.task_done()
