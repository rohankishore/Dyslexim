# dyslexim/core/main_window.py

from functools import partial
import json

from PyQt6.QtCore import Qt, QTimer, QUrl, QObject, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QCursor
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QLineEdit, QTabWidget, QWidget,
    QPushButton, QSizePolicy, QStyle
)
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel

from .browser_tab import BrowserTab
from .config import HOME_URL, INJECT_DELAY_MS, GAZE_UPDATE_INTERVAL_MS, load_config, save_config, config, POST_ONBOARDING_URL
from .js_handler import get_js_gaze_handler


class WebChannelHandler(QObject):
    @pyqtSlot(str, str, str)
    def saveSettings(self, color, font, alignment):
        print(f"Settings received from JS: {color}, {font}, {alignment}")
        config['highlightColor'] = color
        config['font'] = font
        config['highlightAlignment'] = alignment
        config['onboarding_complete'] = True
        save_config(config)

class DysleximMainWindow(QMainWindow):
    """The main application window, managing tabs and the toolbar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyslexim")
        self.resize(1200, 780)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView).availableSizes()[0] if self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView).availableSizes() else Qt.QSize(16,16))
        self.addToolBar(self.toolbar)
        self.add_toolbar_items()

        self.status = self.statusBar()
        self.status.showMessage("Ready — gaze simulation: mouse. Toggle with the eye icon.")

        # Set up the web channel
        self.channel = QWebChannel(self)
        self.handler = WebChannelHandler(self)
        self.channel.registerObject('handler', self.handler)

        if config.get('onboarding_complete', False):
            self.add_new_tab(POST_ONBOARDING_URL, "Home")
        else:
            self.add_new_tab(HOME_URL, "Welcome")

        self.gaze_timer = QTimer(self)
        self.gaze_timer.timeout.connect(self.dispatch_gaze_to_active_tab)
        self.gaze_timer.start(GAZE_UPDATE_INTERVAL_MS)

        self.set_stylesheet()

    def set_stylesheet(self):
        """Sets the modern stylesheet for the application."""
        self.setStyleSheet("""
            QMainWindow { background: #0f1720; }
            QToolBar { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0b1220, stop:1 #101820); spacing:8px; padding:6px; }
            QLineEdit { background: #0b1220; color: #e6eef8; border: 1px solid #1f2a37; padding:6px; border-radius:6px; }
            QTabWidget::pane { border-top: 1px solid #1b2630; }
            QTabBar::tab { background: #0b1220; color: #cfe3ff; padding:8px; border:1px solid #14202a; border-bottom: none; border-top-left-radius:8px; border-top-right-radius:8px; margin-right:2px; }
            QTabBar::tab:selected { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #15202b, stop:1 #0f2a36); color: #ffffff; }
            QPushButton { color: #dcecff; background: transparent; border: none; padding:6px; }
            QPushButton#newtab { background: #0f9d58; border-radius:6px; padding:6px 10px; color: #fff; }
        """)

    def add_toolbar_items(self):
        """Creates and adds all items to the main toolbar."""
        # Back
        back_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        self.act_back = QAction(back_icon, "Back", self)
        self.act_back.triggered.connect(lambda: self.current_view().back())
        self.toolbar.addAction(self.act_back)

        # Forward
        fwd_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        self.act_fwd = QAction(fwd_icon, "Forward", self)
        self.act_fwd.triggered.connect(lambda: self.current_view().forward())
        self.toolbar.addAction(self.act_fwd)

        # Reload
        reload_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self.act_reload = QAction(reload_icon, "Reload", self)
        self.act_reload.triggered.connect(lambda: self.current_view().reload())
        self.toolbar.addAction(self.act_reload)

        # Home
        home_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton)
        self.act_home = QAction(home_icon, "Home", self)
        self.act_home.triggered.connect(lambda: self.navigate_to(HOME_URL if not config.get('onboarding_complete') else POST_ONBOARDING_URL))
        self.toolbar.addAction(self.act_home)

        # Address bar
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter URL or search term...")
        self.url_edit.returnPressed.connect(self.on_url_entered)
        self.url_edit.setMinimumWidth(480)
        self.toolbar.addWidget(self.url_edit)

        # Go button
        go_btn = QPushButton("Go")
        go_btn.clicked.connect(self.on_url_entered)
        self.toolbar.addWidget(go_btn)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Gaze toggle (eye icon)
        self.gaze_btn = QPushButton()
        self.gaze_btn.setToolTip("Toggle gaze highlighting (per tab)")
        self.gaze_btn.setText("👁️")
        self.gaze_btn.clicked.connect(self.toggle_gaze_for_current_tab)
        self.toolbar.addWidget(self.gaze_btn)

        # New Tab
        newtab_btn = QPushButton("+ New Tab")
        newtab_btn.setObjectName("newtab")
        newtab_btn.clicked.connect(lambda: self.add_new_tab(POST_ONBOARDING_URL, "New Tab"))
        self.toolbar.addWidget(newtab_btn)

    def add_new_tab(self, url, label):
        """Adds a new browser tab to the tab widget."""
        tab = BrowserTab(self, start_url=url)
        tab.view.page().setWebChannel(self.channel)
        index = self.tabs.addTab(tab, label)
        self.tabs.setCurrentIndex(index)

        tab.view.titleChanged.connect(partial(self.on_title_changed, tab))
        tab.view.urlChanged.connect(partial(self.on_url_changed, tab))
        tab.view.loadFinished.connect(partial(self.on_load_finished_inject, tab))

        self.url_edit.setText(url)
        return tab

    def close_tab(self, idx):
        """Closes a tab, but not the last one."""
        if self.tabs.count() == 1:
            return
        self.tabs.removeTab(idx)

    def current_tab(self) -> BrowserTab | None:
        """Returns the currently active BrowserTab."""
        return self.tabs.currentWidget()

    def current_view(self):
        """Returns the web view of the currently active tab."""
        t = self.current_tab()
        return t.view if t else None

    def navigate_to(self, url_text):
        """Navigates the current tab to the given URL string."""
        if not url_text:
            return
        if "://" not in url_text:
            q = QUrl.fromUserInput(url_text)
        else:
            q = QUrl(url_text)
        view = self.current_view()
        if view:
            view.setUrl(q)

    def on_url_entered(self):
        """Handles the user entering a URL or search term in the address bar."""
        text = self.url_edit.text().strip()
        if not text:
            return
        if " " in text and "://" not in text:
            query = QUrl.fromUserInput(f"https://www.google.com/search?q={text.replace(' ', '+')}")
            self.current_view().setUrl(query)
        else:
            self.current_view().setUrl(QUrl.fromUserInput(text))

    def on_title_changed(self, tab, title):
        """Updates the tab title when the page title changes."""
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            self.tabs.setTabText(idx, title[:30])

    def on_url_changed(self, tab, url):
        """Updates the address bar when the URL changes."""
        if tab is self.current_tab():
            self.url_edit.setText(url.toString())

    def on_load_finished_inject(self, tab, ok):
        """Injects the gaze handler JavaScript after a page has loaded."""
        if not ok:
            return

        def do_inject():
            try:
                highlight_color = config.get('highlightColor', 'rgba(255, 200, 0, 0.35)')
                font = config.get('font', 'Poppins')
                alignment = config.get('highlightAlignment', 'center')
                js = get_js_gaze_handler(highlight_color, font, alignment)
                tab.view.page().runJavaScript(js)
            except Exception:
                pass  # Ignore potential errors on special pages

        QTimer.singleShot(INJECT_DELAY_MS, do_inject)

    def dispatch_gaze_to_active_tab(self):
        """Dispatches the current gaze position to the active tab's web view."""
        tab = self.current_tab()
        if not tab or not getattr(tab, "gaze_enabled", True):
            return

        global_pos = QCursor.pos()
        local_pt = tab.view.mapFromGlobal(global_pos)
        vw = tab.view.width() or 1
        vh = tab.view.height() or 1
        norm_x = max(0.0, min(1.0, local_pt.x() / vw))
        norm_y = max(0.0, min(1.0, local_pt.y() / vh))

        js = f"""
        (function(){{
          if (window.__dyslexim_handleGaze && typeof window.__dyslexim_handleGaze === 'function') {{
            try {{ window.__dyslexim_handleGaze({norm_x:.4f}, {norm_y:.4f}); }} catch(e){{ }}
          }}
        }})();
        """
        tab.view.page().runJavaScript(js)

    def toggle_gaze_for_current_tab(self):
        """Toggles the gaze highlighting feature for the current tab."""
        tab = self.current_tab()
        if not tab:
            return
        tab.gaze_enabled = not getattr(tab, "gaze_enabled", True)
        self.status.showMessage(f"Gaze highlighting {'enabled' if tab.gaze_enabled else 'disabled'} for this tab.", 3000)
        self.gaze_btn.setText("👁️" if tab.gaze_enabled else "🚫")