from __future__ import annotations

import ctypes
from enum import Enum
import sys
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from src.capture.mss_capture import MSSScreenCapture
from src.capture.region_selector import RegionSelector
from src.config.settings import AppSettings
from src.config.settings_manager import SettingsManager
from src.exceptions import OperationCancelled, ScreenTranslatorError
from src.ocr.paddle_ocr import PaddleOCREngine
from src.overlay.overlay_manager import OverlayManager
from src.services.translation_pipeline import (
    FullScreenTranslationResult,
    TranslationPipeline,
    TranslationResult,
)
from src.translation.argos_translator import ArgosTranslator
from src.translation.azure_translator import AzureTranslator
from src.translation.deepl_translator import DeepLTranslator
from src.translation.libretranslate_translator import LibreTranslateTranslator
from src.translation.translation_service import TranslationService
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logging

from .hotkey_manager import HotkeyError, HotkeyManager
from .tray_manager import TrayManager


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class AppState(Enum):
    IDLE = "idle"
    SELECTING = "selecting"
    PROCESSING = "processing"
    SHOWING_OVERLAY = "showing_overlay"


class _WorkerSignals(QObject):
    finished = Signal(int, object)
    error = Signal(int, str)
    status = Signal(int, str)


class _PipelineWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        pipeline: TranslationPipeline,
        region,
        settings: AppSettings,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.pipeline = pipeline
        self.region = region
        self.settings = settings
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.pipeline.translate_region(
                region=self.region,
                source_language=self.settings.source_language,
                target_language=self.settings.target_language,
                provider_name=self.settings.translation_provider,
                status_callback=lambda text: self.signals.status.emit(
                    self.job_id, text
                ),
            )
        except OperationCancelled:
            return
        except ScreenTranslatorError as exc:
            self.signals.error.emit(self.job_id, str(exc))
            return
        except Exception as exc:
            self.signals.error.emit(
                self.job_id, f"Unexpected error while translating: {exc}"
            )
            return

        self.signals.finished.emit(self.job_id, result)


class _FullScreenWorker(QRunnable):
    def __init__(
        self,
        job_id: int,
        pipeline: TranslationPipeline,
        settings: AppSettings,
    ) -> None:
        super().__init__()
        self.job_id = job_id
        self.pipeline = pipeline
        self.settings = settings
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.pipeline.translate_full_screen(
                source_language=self.settings.source_language,
                target_language=self.settings.target_language,
                provider_name=self.settings.translation_provider,
                status_callback=lambda text: self.signals.status.emit(
                    self.job_id, text
                ),
            )
        except OperationCancelled:
            return
        except ScreenTranslatorError as exc:
            self.signals.error.emit(self.job_id, str(exc))
            return
        except Exception as exc:
            self.signals.error.emit(
                self.job_id, f"Unexpected full-screen translation error: {exc}"
            )
            return

        self.signals.finished.emit(self.job_id, result)


class ScreenTranslatorApplication(QObject):
    def __init__(self, debug: bool = False) -> None:
        enable_windows_dpi_awareness()

        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setApplicationName("Screen Translator")
        self.qt_app.setOrganizationName("ScreenTranslator")
        self.qt_app.setQuitOnLastWindowClosed(False)
        super().__init__()

        self.logger = setup_logging(debug=debug)
        self.logger.info("Starting Screen Translator.")

        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.load()

        self.translation_service = TranslationService()
        self.argos = ArgosTranslator()
        self.ocr = PaddleOCREngine(
            language=self.settings.source_language,
            min_confidence=self.settings.ocr_min_confidence,
        )
        self.pipeline = TranslationPipeline(
            screen_capture=MSSScreenCapture(),
            ocr_engine=self.ocr,
            translation_service=self.translation_service,
        )
        self._configure_translation_providers()

        self.overlay_manager = OverlayManager()
        self.thread_pool = QThreadPool.globalInstance()
        self.state = AppState.IDLE
        self._job_id = 0
        self._selector: RegionSelector | None = None
        self._quitting = False

        self.window = MainWindow(self.settings)
        self.window.translate_requested.connect(self.start_selection)
        self.window.full_screen_translate_requested.connect(
            self.start_full_screen_translation
        )
        self.window.settings_saved.connect(self.apply_settings)
        self.window.install_argos_requested.connect(self.install_argos_model)

        self.tray = TrayManager(self.window)
        self.tray.translate_requested.connect(self.start_selection)
        self.tray.open_requested.connect(self.show_main_window)
        self.tray.settings_requested.connect(self.show_main_window)
        self.tray.exit_requested.connect(self.quit)

        self.hotkey = HotkeyManager(self.qt_app)
        self.hotkey.hotkey_pressed.connect(self.start_selection)
        self._register_hotkey(self.settings.global_hotkey)

        self.tray.show()

        if self.settings.start_minimized:
            self.window.hide()
        else:
            self.window.show()

    def _configure_translation_providers(self) -> None:
        self.translation_service.register(self.argos)
        self.translation_service.register(
            AzureTranslator(
                api_key=self.settings.azure_api_key,
                region=self.settings.azure_region,
                endpoint=self.settings.azure_endpoint,
            )
        )
        self.translation_service.register(
            DeepLTranslator(
                api_key=self.settings.deepl_api_key,
                api_url=self.settings.deepl_api_url,
            )
        )
        self.translation_service.register(
            LibreTranslateTranslator(
                base_url=self.settings.libretranslate_url,
                api_key=self.settings.libretranslate_api_key,
            )
        )

    def _register_hotkey(self, hotkey: str) -> None:
        try:
            self.hotkey.register(hotkey)
        except HotkeyError as exc:
            self.logger.error("Hotkey registration failed: %s", exc)
            self.window.set_status(str(exc))
            self.tray.notify("Screen Translator", str(exc))
        else:
            self.logger.info("Registered global hotkey %s.", hotkey)

    @Slot()
    def show_main_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _sync_current_ui_settings(self) -> bool:
        try:
            current = self.window.settings_page.values()
        except ValueError as exc:
            self._handle_error(str(exc))
            return False

        if current == self.settings:
            return True

        old_hotkey = self.settings.global_hotkey
        try:
            current = self.settings_manager.save(current)
        except ValueError as exc:
            self._handle_error(str(exc))
            return False

        self.settings = current
        self._configure_translation_providers()
        self.ocr.set_language(current.source_language)

        if current.global_hotkey != old_hotkey:
            self._register_hotkey(current.global_hotkey)

        self.logger.info(
            "Applied current GUI settings provider=%s source=%s target=%s",
            current.translation_provider,
            current.source_language,
            current.target_language,
        )
        return True

    def _cancel_current_activity(self) -> None:
        self._job_id += 1
        self.pipeline.cancel()
        self.overlay_manager.close()
        self._dispose_selector()

    @Slot()
    def start_selection(self) -> None:
        if not self._sync_current_ui_settings():
            return

        self._cancel_current_activity()
        self.state = AppState.SELECTING
        self.window.set_processing(False)
        self.window.set_status("Select a screen region")

        try:
            selector = RegionSelector()
        except Exception as exc:
            self.state = AppState.IDLE
            self._handle_error(f"Unable to start region selection: {exc}")
            return

        self._selector = selector
        selector.region_selected.connect(self._on_region_selected)
        selector.cancelled.connect(self._on_selection_cancelled)
        selector.begin()

    @Slot()
    def start_full_screen_translation(self) -> None:
        if not self._sync_current_ui_settings():
            return

        self._cancel_current_activity()
        self.pipeline.reset_cancelled()
        self.state = AppState.PROCESSING
        self.window.set_processing(True)
        self.window.set_status("Preparing full-screen scan...")

        # Hide our own GUI before the screenshot so PaddleOCR does not detect
        # and translate Screen Translator itself.
        self.window.hide()

        self._job_id += 1
        job_id = self._job_id
        QTimer.singleShot(220, lambda: self._launch_full_screen_worker(job_id))

    def _launch_full_screen_worker(self, job_id: int) -> None:
        if job_id != self._job_id or self._quitting:
            return

        worker = _FullScreenWorker(
            job_id=job_id,
            pipeline=self.pipeline,
            settings=self.settings,
        )
        worker.signals.status.connect(self._on_worker_status)
        worker.signals.finished.connect(self._on_full_screen_finished)
        worker.signals.error.connect(self._on_worker_error)
        self.thread_pool.start(worker)

    @Slot()
    def _on_selection_cancelled(self) -> None:
        self.state = AppState.IDLE
        self.window.set_status("Ready")
        self._dispose_selector()

    def _dispose_selector(self) -> None:
        selector = self._selector
        self._selector = None
        if selector is not None:
            selector.close()
            selector.deleteLater()

    @Slot(object)
    def _on_region_selected(self, region: Any) -> None:
        self._dispose_selector()
        self.pipeline.reset_cancelled()
        self.state = AppState.PROCESSING
        self.window.set_processing(True)

        self._job_id += 1
        job_id = self._job_id
        worker = _PipelineWorker(
            job_id=job_id,
            pipeline=self.pipeline,
            region=region,
            settings=self.settings,
        )
        worker.signals.status.connect(self._on_worker_status)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.error.connect(self._on_worker_error)
        self.thread_pool.start(worker)

    @Slot(int, str)
    def _on_worker_status(self, job_id: int, text: str) -> None:
        if job_id == self._job_id:
            self.window.set_status(text)

    @Slot(int, object)
    def _on_worker_finished(self, job_id: int, result: TranslationResult) -> None:
        if job_id != self._job_id:
            return

        self.logger.info(
            "Translation completed provider=%s capture=%.3fs ocr=%.3fs translation=%.3fs",
            result.provider,
            result.capture_seconds,
            result.ocr_seconds,
            result.translation_seconds,
        )
        self.window.set_processing(False)
        self.window.set_status("Translation ready")
        self.overlay_manager.show_translation(
            result.translated_text,
            result.region,
            self.settings.overlay_opacity,
        )
        self.state = AppState.SHOWING_OVERLAY

    @Slot(int, object)
    def _on_full_screen_finished(
        self,
        job_id: int,
        result: FullScreenTranslationResult,
    ) -> None:
        if job_id != self._job_id:
            return

        self.window.set_processing(False)
        self.window.set_status(
            f"Translated {len(result.items)} screen regions"
        )

        translations = [
            (item.translated_text, item.region)
            for item in result.items
        ]
        self.overlay_manager.show_translations(
            translations,
            self.settings.overlay_opacity,
        )
        self.state = AppState.SHOWING_OVERLAY

    @Slot(int, str)
    def _on_worker_error(self, job_id: int, message: str) -> None:
        if job_id != self._job_id:
            return
        self.state = AppState.IDLE
        self.window.set_processing(False)
        self._handle_error(message)

    def _handle_error(self, message: str) -> None:
        self.logger.error("%s", message)
        self.window.set_status(message)
        if self.window.isVisible():
            self.window.show_error(message)
        else:
            self.tray.notify("Screen Translator", message)

    @Slot(object)
    def apply_settings(self, settings: AppSettings) -> None:
        old_hotkey = self.settings.global_hotkey
        try:
            settings = self.settings_manager.save(settings)
        except ValueError as exc:
            self.window.show_error(str(exc))
            return

        self.settings = settings
        self._configure_translation_providers()
        self.ocr.set_language(settings.source_language)

        if settings.global_hotkey != old_hotkey:
            self._register_hotkey(settings.global_hotkey)

        self.window.settings_page.load(settings)
        self.window.set_status("Settings saved")
        self.tray.notify("Screen Translator", "Settings saved.")

    @Slot(str, str)
    def install_argos_model(self, source_language: str, target_language: str) -> None:
        self.window.set_status(
            f"Installing Argos model {source_language} -> {target_language}..."
        )
        self.window.set_processing(True)

        class _InstallSignals(QObject):
            success = Signal(str)
            error = Signal(str)

        class _InstallWorker(QRunnable):
            def __init__(self, translator, source, target) -> None:
                super().__init__()
                self.translator = translator
                self.source = source
                self.target = target
                self.signals = _InstallSignals()

            @Slot()
            def run(self) -> None:
                try:
                    self.translator.install_language_model(
                        self.source, self.target
                    )
                except ScreenTranslatorError as exc:
                    self.signals.error.emit(str(exc))
                    return
                except Exception as exc:
                    self.signals.error.emit(
                        f"Unable to install the Argos model: {exc}"
                    )
                    return
                self.signals.success.emit(
                    f"Argos model {self.source} -> {self.target} installed."
                )

        worker = _InstallWorker(self.argos, source_language, target_language)
        worker.signals.success.connect(self._on_argos_installed)
        worker.signals.error.connect(self._on_argos_install_error)
        self.thread_pool.start(worker)

    @Slot(str)
    def _on_argos_installed(self, message: str) -> None:
        self.window.set_processing(False)
        self.window.set_status(message)
        self.window.show_information(message)

    @Slot(str)
    def _on_argos_install_error(self, message: str) -> None:
        self.window.set_processing(False)
        self._handle_error(message)

    @Slot()
    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        self.logger.info("Shutting down Screen Translator.")
        self._job_id += 1
        self.pipeline.cancel()
        self.overlay_manager.close()
        self._dispose_selector()
        self.hotkey.close()
        self.tray.hide()
        self.thread_pool.waitForDone(1500)
        self.window.allow_close()
        self.window.close()
        self.qt_app.quit()

    def run(self) -> int:
        return self.qt_app.exec()
