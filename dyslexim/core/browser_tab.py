from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, pyqtSlot

class BrowserView(QWebEngineView):
    """A custom QWebEngineView with the leaveEvent fix."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # --- FIX: Clear highlight when mouse leaves the web view area ---
    def leaveEvent(self, event):
        """Fires when the mouse leaves the web view area."""
        js = "(function(){ if(window.__dyslexim_clearHighlight) window.__dyslexim_clearHighlight(); })();"
        self.page().runJavaScript(js)
        super().leaveEvent(event)

class BrowserTab(QWidget):
    """A single tab widget, containing a web view and its state."""
    
    def __init__(self, start_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- State is stored here, on the tab ---
        self.gaze_enabled = True
        self.focus_mode_enabled = False
        
        self.view = BrowserView()
        
        # Use an off-the-record profile for privacy, like Incognito
        # Use QWebEngineProfile.defaultProfile() for persistence
        self.profile = QWebEngineProfile(f"profile_{id(self)}", self)
        self.page = QWebEnginePage(self.profile, self)
        self.view.setPage(self.page)
        
        layout.addWidget(self.view)
        self.setLayout(layout)
        
        self.view.setUrl(QUrl(start_url))
    
    def __del__(self):
        """Cleanup when tab is deleted."""
        try:
            if hasattr(self, 'page') and self.page:
                self.page.deleteLater()
            if hasattr(self, 'profile') and self.profile:
                self.profile.deleteLater()
        except:
            pass