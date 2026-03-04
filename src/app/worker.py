"""
QThread-based worker — launches a subprocess for computation.

The C++ strategy engine (strategy_metrics_cpp) is not safe to call from
a non-main thread on Windows — it causes a fatal segfault that kills the
whole Qt process.  Running it in a separate Process isolates the crash and
lets us report the error cleanly.

The subprocess entry point lives in _subprocess_worker.py (Qt-free module)
to avoid the 0xC0000005 crash caused by importing PyQt6 in a spawned process.
"""

from __future__ import annotations

import tempfile
import traceback
from multiprocessing import Process
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QThread, pyqtSignal

# Qt-free subprocess entry point
import app._subprocess_worker as _sw


TEMP_DIR = Path(tempfile.gettempdir()) / "option_strategy_results"
TEMP_DIR.mkdir(exist_ok=True)


def _result_path(sid: str) -> Path:
    return TEMP_DIR / f"result_{sid}.pkl"

def _error_path(sid: str) -> Path:
    return TEMP_DIR / f"error_{sid}.txt"

def _cleanup(sid: str) -> None:
    for p in (_result_path(sid), _error_path(sid)):
        if p.exists():
            p.unlink(missing_ok=True)


class ProcessingWorker(QThread):
    result_ready     = pyqtSignal(object)
    error_occurred   = pyqtSignal(str)
    progress_message = pyqtSignal(str)

    POLL_MS = 300

    def __init__(self, session_id: str, params: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._sid = session_id
        self._params = params
        self._process: Optional[Process] = None
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2)

    def run(self) -> None:
        _cleanup(self._sid)
        try:
            self._process = Process(
                target=_sw.run,
                args=(self._sid, self._params),
                daemon=True,
            )
            self._process.start()

            while self._process.is_alive():
                if self._stop:
                    self._process.terminate()
                    self._process.join(timeout=2)
                    self.error_occurred.emit("terminated")
                    return
                self.msleep(self.POLL_MS)

            exitcode = self._process.exitcode

            # ── error file written by subprocess exception handler ──
            if _error_path(self._sid).exists():
                self.error_occurred.emit(_error_path(self._sid).read_text())
                return

            # ── subprocess crashed (C++ segfault, OOM, etc.) ──
            if exitcode and exitcode != 0:
                self.error_occurred.emit(
                    f"Subprocess crashed with exit code {exitcode} "
                    f"(0x{exitcode & 0xFFFFFFFF:08X}).\n"
                    "Check that strategy_metrics_cpp is installed and "
                    "that all required parameters are set."
                )
                return

            # ── success ──
            if _result_path(self._sid).exists():
                import pickle
                with open(_result_path(self._sid), "rb") as f:
                    result = pickle.load(f)
                self.result_ready.emit(result)
            else:
                self.error_occurred.emit("Subprocess exited cleanly but wrote no result.")

        except Exception as exc:
            self.error_occurred.emit(f"{exc}\n\n{traceback.format_exc()}")
