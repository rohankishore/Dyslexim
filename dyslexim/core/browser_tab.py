
# dyslexim/core/browser_tab.py

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .config import HOME_URL


class BrowserTab(QWidget):
    """A single browser tab, containing a web view."""

    def __init__(self, parent=None, start_url=HOME_URL):
        super().__init__(parent)
        self.view = QWebEngineView()
        self.view.setUrl(QUrl(start_url))

        # Track if we should apply gaze injection on this tab
        self.gaze_enabled = True

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)
