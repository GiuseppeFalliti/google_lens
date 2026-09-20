from __future__ import annotations

import json
import os
import sys
from typing import Any


RESULT_PREFIX = "__SCREEN_TRANSLATOR_ARGOS_RESULT__="


def emit(payload: dict[str, Any]) -> None:
    print(RESULT_PREFIX + json.dumps(payload, ensure_ascii=False), flush=True)


def load_modules():
    # Keep PyTorch/Stanza entirely inside this subprocess. Loading them in the
    # same Windows process as PaddlePaddle can trigger native DLL conflicts.
    os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")
    os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

    import argostranslate.package as package
    import argostranslate.translate as translate

    return package, translate


def model_installed(source: str, target: str) -> bool:
    _, translate = load_modules()
    languages = {language.code: language for language in translate.get_installed_languages()}
    source_language = languages.get(source)
    target_language = languages.get(target)
    if source_language is None or target_language is None:
        return False

    try:
        source_language.get_translation(target_language)
    except Exception:
        return False
    return True


def install_model(source: str, target: str) -> None:
    package, _ = load_modules()
    package.update_package_index()
    available = package.get_available_packages()
    candidate = next(
        (
            item
            for item in available
            if item.from_code == source and item.to_code == target
        ),
        None,
    )
    if candidate is None:
        raise RuntimeError(f"No Argos model is available for {source} -> {target}.")
    package.install_from_path(candidate.download())


def translate_text(text: str, source: str, target: str) -> str:
    _, translate = load_modules()
    result = translate.translate(text, source, target)
    result = str(result).strip()
    if not result:
        raise RuntimeError("Argos returned an empty translation.")
    return result


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        action = str(payload.get("action", "")).strip().lower()
        source = str(payload.get("source", "")).strip().lower()
        target = str(payload.get("target", "")).strip().lower()

        if action == "check":
            emit({"ok": True, "installed": model_installed(source, target)})
            return 0

        if action == "install":
            install_model(source, target)
            emit({"ok": True})
            return 0

        if action == "translate":
            text = str(payload.get("text", ""))
            emit({"ok": True, "text": translate_text(text, source, target)})
            return 0

        raise RuntimeError(f"Unsupported Argos worker action: {action}")
    except Exception as exc:
        emit(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
