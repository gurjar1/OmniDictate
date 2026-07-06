from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from huggingface_hub import snapshot_download
from tqdm.auto import tqdm


class ModelDownloadWorker(QObject):
    progress_updated = Signal(int, str)
    download_completed = Signal(str)
    download_failed = Signal(str)

    def __init__(self, model_id: str, model_storage_path: str, parent=None):
        super().__init__(parent)
        self.model_id = model_id
        self.model_storage_path = model_storage_path
        self._cancel_requested = False

    def _create_tqdm_class(self):
        worker = self

        class DownloadProgressBar(tqdm):
            def __init__(self, *args, **kwargs):
                progress_name = kwargs.pop("name", None)
                if progress_name and "desc" not in kwargs:
                    kwargs["desc"] = str(progress_name)
                kwargs.setdefault("file", io.StringIO())
                kwargs.setdefault("leave", False)
                super().__init__(*args, **kwargs)
                worker._emit_progress(getattr(self, "n", 0), getattr(self, "total", None), getattr(self, "desc", None))

            def update(self, n=1):
                if worker._cancel_requested:
                    raise RuntimeError("Download cancelled by user.")
                result = super().update(n)
                worker._emit_progress(self.n, self.total, self.desc)
                return result

            def close(self):
                worker._emit_progress(getattr(self, "n", 0), getattr(self, "total", None), getattr(self, "desc", None))
                return super().close()

        return DownloadProgressBar

    def _emit_progress(self, completed: int | float | None, total: int | float | None, description: str | None):
        if total:
            percent = max(0, min(100, int((completed / total) * 100)))
        else:
            percent = 0
        message = description or f"Downloading {self.model_id}..."
        try:
            self.progress_updated.emit(percent, message)
        except RuntimeError:
            return

    @Slot()
    def run(self):
        try:
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            local_dir = Path(self.model_storage_path) / self.model_id.rsplit("/", 1)[-1]
            local_dir.mkdir(parents=True, exist_ok=True)
            self.progress_updated.emit(0, f"Preparing download for {self.model_id}...")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                downloaded_path = snapshot_download(
                    repo_id=self.model_id,
                    local_dir=local_dir,
                    local_files_only=False,
                    tqdm_class=self._create_tqdm_class(),
                )
            if self._cancel_requested:
                self.download_failed.emit("Download cancelled by user.")
                return
            self.progress_updated.emit(100, f"Download complete: {self.model_id}")
            self.download_completed.emit(str(downloaded_path))
        except Exception as exc:
            self.download_failed.emit(str(exc))

    @Slot()
    def request_cancel(self):
        self._cancel_requested = True
