from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout


class StatusWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("Status: Ready")
        layout.addWidget(self._label)

    def set_status(self, text: str) -> None:
        self._label.setText(f"Status: {text}")
