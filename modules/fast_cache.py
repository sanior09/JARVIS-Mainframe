"""
fast_cache.py — In-Memory hot-path counter cache for JARVIS.

- ใช้ Redis ถ้ามี server รันอยู่ (และติดตั้งไลบรารี `redis`)
- ถ้าไม่มี จะ fallback เป็น RAM (dict + lock) อัตโนมัติ
- ทั้งสองโหมดเขียนลง SQLite แบบ write-behind (เบื้องหลังทุก few วินาที + ตอนปิดโปรแกรม)
  ทำให้ hot path (นับโควต้า) ไม่ต้องรอ disk I/O
"""
import atexit
import logging
import threading
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger("jarvis.fast_cache")


class FastCounterCache:
    def __init__(self, loader: Callable[[str], Optional[tuple]],
                 saver: Callable[[str, int, str], None],
                 flush_interval: float = 5.0,
                 redis_url: str = "redis://127.0.0.1:6379/0"):
        """
        loader(key) -> (count:int, date:'YYYY-MM-DD') | None   (อ่านจาก SQLite)
        saver(key, count, date) -> None                         (เขียนลง SQLite)
        """
        self._loader = loader
        self._saver = saver
        self._lock = threading.Lock()
        self._mem: dict = {}      # key -> [count, date]
        self._dirty: set = set()
        self._redis = None
        self._stop = threading.Event()
        self.backend = "memory"

        try:
            import redis  # type: ignore
            client = redis.Redis.from_url(redis_url, socket_connect_timeout=0.3,
                                          socket_timeout=0.5, decode_responses=True)
            client.ping()
            self._redis = client
            self.backend = "redis"
        except Exception:
            self._redis = None

        self._thread = threading.Thread(target=self._flush_loop, args=(flush_interval,),
                                        daemon=True, name="FastCacheFlusher")
        self._thread.start()
        atexit.register(self.flush)
        logger.info(f"FastCounterCache backend = {self.backend}")

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # ---------- internal ----------
    def _load_mem(self, key: str) -> list:
        entry = self._mem.get(key)
        if entry is None:
            row = None
            try:
                row = self._loader(key)
            except Exception as e:
                logger.error(f"cache load failed: {e}")
            entry = [int(row[0]), row[1]] if row else [0, self._today()]
            self._mem[key] = entry
        return entry

    def _rkey(self, key: str) -> str:
        return f"jarvis:{key}:{self._today()}"

    # ---------- public ----------
    def incr(self, key: str) -> int:
        today = self._today()
        if self._redis is not None:
            try:
                rk = self._rkey(key)
                if not self._redis.exists(rk):
                    # seed จาก SQLite เฉพาะถ้าเป็นของวันนี้ (กัน restart แล้วเลขรีเซ็ต)
                    row = self._loader(key)
                    if row and row[1] == today:
                        self._redis.set(rk, int(row[0]), ex=172800, nx=True)
                val = int(self._redis.incr(rk))
                self._redis.expire(rk, 172800)
                with self._lock:
                    self._mem[key] = [val, today]
                    self._dirty.add(key)
                return val
            except Exception as e:
                logger.warning(f"Redis error, falling back to memory: {e}")
                self._redis = None
                self.backend = "memory"
        with self._lock:
            entry = self._load_mem(key)
            if entry[1] != today:
                entry[0], entry[1] = 0, today
            entry[0] += 1
            self._dirty.add(key)
            return entry[0]

    def get(self, key: str) -> int:
        today = self._today()
        if self._redis is not None:
            try:
                v = self._redis.get(self._rkey(key))
                if v is not None:
                    return int(v)
            except Exception:
                self._redis = None
                self.backend = "memory"
        with self._lock:
            entry = self._load_mem(key)
            return entry[0] if entry[1] == today else 0

    def flush(self) -> None:
        with self._lock:
            keys = list(self._dirty)
            self._dirty.clear()
            snapshot = {k: tuple(self._mem[k]) for k in keys if k in self._mem}
        for k, (count, date) in snapshot.items():
            try:
                self._saver(k, count, date)
            except Exception as e:
                logger.error(f"cache flush failed for {k}: {e}")
                with self._lock:
                    self._dirty.add(k)

    def _flush_loop(self, interval: float) -> None:
        while not self._stop.wait(interval):
            self.flush()

    def close(self) -> None:
        self._stop.set()
        self.flush()
