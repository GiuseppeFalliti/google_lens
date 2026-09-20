from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from src.exceptions import TranslationConfigurationError, TranslationError

from .base_translator import TranslationProvider
from .argos_worker import RESULT_PREFIX


class ArgosTranslator(TranslationProvider):
    """Argos provider isolated in a child process on Windows.

    Argos depends on Stanza/PyTorch. PaddlePaddle and PyTorch may conflict at
    the native DLL level when loaded into the same Windows process, so Argos
    never imports its ML stack in the GUI/OCR process.
    """

    @property
    def name(self) -> str:
        return "argos"

    @staticmethod
    def _run_worker(
        action: str,
        source_language: str,
        target_language: str,
        *,
        text: str = "",
        timeout: float = 90.0,
    ) -> dict[str, Any]:
        payload = {
            "action": action,
            "source": source_language,
            "target": target_language,
            "text": text,
        }

        env = os.environ.copy()
        env.setdefault("ARGOS_DEVICE_TYPE", "cpu")
        env.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            completed = subprocess.run(
                [sys.executable, "-m", "src.translation.argos_worker"],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
                creationflags=creationflags,
            )
        except FileNotFoundError as exc:
            raise TranslationConfigurationError(
                "Unable to start the Argos translation worker."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise TranslationError("Argos translation worker timed out.") from exc
        except OSError as exc:
            raise TranslationError(
                f"Unable to start the Argos translation worker: {exc}"
            ) from exc

        result: dict[str, Any] | None = None
        for line in reversed(completed.stdout.splitlines()):
            if line.startswith(RESULT_PREFIX):
                try:
                    result = json.loads(line[len(RESULT_PREFIX) :])
                except json.JSONDecodeError:
                    result = None
                break

        if result is None:
            details = completed.stderr.strip() or completed.stdout.strip()
            if len(details) > 700:
                details = details[-700:]
            raise TranslationError(
                "Argos worker returned an invalid response."
                + (f" Details: {details}" if details else "")
            )

        if not result.get("ok"):
            error = str(result.get("error") or "Unknown Argos worker error.")
            if "No module named" in error or "ModuleNotFoundError" in error:
                raise TranslationConfigurationError(
                    "Argos Translate is not installed correctly. "
                    f"Worker error: {error}"
                )
            raise TranslationError(error)

        return result

    def is_model_installed(self, source_language: str, target_language: str) -> bool:
        result = self._run_worker(
            "check",
            source_language,
            target_language,
            timeout=45.0,
        )
        return bool(result.get("installed"))

    def install_language_model(
        self, source_language: str, target_language: str
    ) -> None:
        self._run_worker(
            "install",
            source_language,
            target_language,
            timeout=360.0,
        )

    def translate(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        if not self.is_model_installed(source_language, target_language):
            raise TranslationConfigurationError(
                f"Argos model {source_language} -> {target_language} is not installed."
            )

        result = self._run_worker(
            "translate",
            source_language,
            target_language,
            text=text,
            timeout=90.0,
        )
        translated = str(result.get("text", "")).strip()
        if not translated:
            raise TranslationError("Argos returned an empty translation.")
        return translated
