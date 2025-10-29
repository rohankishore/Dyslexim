from functools import partial
import json

from PyQt6.QtCore import Qt, QTimer, QUrl, QObject, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QIcon, QCursor
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QLineEdit, QTabWidget, QWidget,
    QPushButton, QSizePolicy, QStyle, QStatusBar
)
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel

from .browser_tab import BrowserTab, BrowserView
from .config import (
    HOME_URL, INJECT_DELAY_MS, GAZE_UPDATE_INTERVAL_MS, 
    load_config, save_config, config, POST_ONBOARDING_URL, 
    SETTINGS_URL, SEARCH_ENGINES
)
from .js_handler import get_js_gaze_handler, get_focus_mode_js


class WebChannelHandler(QObject):
    """Handles JS-to-Python communication for settings."""
    
    @pyqtSlot(str, str, str, bool, float, str)
    def saveSettings(self, color, font, alignment, readingMask, ttsHoverTime, searchEngine):
        """Called by JS from the onboarding/settings page."""
        # ... (same as before)
        config['onboarding_complete'] = True
        save_config(config)
        
        if self.parent():
            self.parent().reload_all_tabs_after_settings_change()

    @pyqtSlot(result=str)
    def loadSettings(self):
        """Called by JS on the settings page to get current config."""
        # ... (same as before)
        return json.dumps(config)
        
    # --- NEW: Slot for the custom home page search ---
    @pyqtSlot(str)
    def performSearch(self, term):
        """Called by home.js to perform a search."""
        print(f"Search received from JS: {term}")
        if self.parent() and term:
            self.parent().navigate_to_search(term)


class DysleximMainWindow(QMainWindow):
    """The main application window, managing tabs and the toolbar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyslexim")
        self.resize(1366, 768)
        
        # Load custom SVG icons
        self.load_icons()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True) # Allow re-ordering tabs
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tabs)
        
        # --- NEW: Add "+" button to tab bar corner ---
        self.new_tab_btn = QPushButton(self.plus_icon, "")
        self.new_tab_btn.setToolTip("New Tab")
        self.new_tab_btn.setObjectName("newtab_corner_btn")
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab(POST_ONBOARDING_URL, "New Tab"))
        self.tabs.setCornerWidget(self.new_tab_btn, Qt.Corner.TopRightCorner)

        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20)) # Crisper icons
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.add_toolbar_items()

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Welcome to Dyslexim.")

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

    def load_icons(self):
        """Loads and stores custom SVG icons from QRC."""
        self.back_icon = QIcon("qrc:///icons/arrow-left.svg")
        self.fwd_icon = QIcon("qrc:///icons/arrow-right.svg")
        self.reload_icon = QIcon("qrc:///icons/rotate-cw.svg")
        self.home_icon = QIcon("qrc:///icons/home.svg")
        self.settings_icon = QIcon("qrc:///icons/settings.svg")
        self.gaze_on_icon = QIcon("qrc:///icons/eye.svg")
        self.gaze_off_icon = QIcon("qrc:///icons/eye-off.svg")
        self.focus_icon = QIcon("qrc:///icons/target.svg")
        self.plus_icon = QIcon("qrc:///icons/plus.svg")


    def set_stylesheet(self):
        """Sets the new modern stylesheet."""
        self.setStyleSheet("""
            /* --- Base Window --- */
            QMainWindow { 
                background: #1c1c1e; /* Softer, iOS-like dark */
            }
            QStatusBar {
                color: #8a8a8e;
            }

            /* --- Toolbar --- */
            QToolBar { 
                background: #1c1c1e;
                border-bottom: 1px solid #3a3a3c;
                spacing: 10px; 
                padding: 10px 15px;
            }
            
            /* --- URL Bar --- */
            QLineEdit { 
                background: #2c2c2e; 
                color: #f2f2f7; 
                border: 1px solid #3a3a3c; 
                padding: 10px 15px; 
                border-radius: 10px; /* More rounded */
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #0a84ff; /* Apple blue */
            }
            
            /* --- Tab Bar --- */
            QTabWidget::pane { 
                /* The content area */
                border-top: 1px solid #3a3a3c; 
            }
            QTabBar {
                /* The bar itself */
                background: #1c1c1e;
                border-bottom: 1px solid #3a3a3c;
            }
            QTabBar::tab { 
                background: #1c1c1e; 
                color: #8a8a8e; /* Muted text */
                padding: 12px 18px; 
                border: 1px solid transparent;
                border-bottom: none; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px;
            }
            QTabBar::tab:hover {
                background: #2c2c2e;
            }
            QTabBar::tab:selected { 
                background: #1c1c1e; /* Blends with window */
                color: #f2f2f7;
                border: 1px solid #3a3a3c;
                border-bottom: 1px solid #1c1c1e; /* Hides bottom border */
            }
            
            /* --- New Tab Button in Corner --- */
            QTabBar::corner-widget {
                padding-right: 10px;
                padding-top: 8px;
            }
            QPushButton#newtab_corner_btn {
                background: transparent;
                border: none;
                padding: 5px;
                border-radius: 6px;
            }
            QPushButton#newtab_corner_btn:hover {
                background: #2c2c2e;
            }
            
            /* --- Toolbar Buttons (Icons) --- */
            QToolBar > QPushButton {
                background: transparent;
                border: none;
                padding: 6px;
                border-radius: 6px;
            }
            QToolBar > QPushButton:hover {
                background: #2c2c2e;
            }
            QToolBar > QPushButton:pressed {
                background: #3a3a3c;
            }
            QToolBar > QPushButton:checked {
                /* For 'Focus' button */
                background: #0a84ff;
                color: white;
            }
        """)

    def add_toolbar_items(self):
        """Creates and adds all items to the main toolbar."""
        # Back
        self.act_back = QPushButton(self.back_icon, "")
        self.act_back.setToolTip("Back")
        self.act_back.clicked.connect(lambda: self.current_view().back())
        self.toolbar.addWidget(self.act_back)

        # Forward
        self.act_fwd = QPushButton(self.fwd_icon, "")
        self.act_fwd.setToolTip("Forward")
        self.act_fwd.clicked.connect(lambda: self.current_view().forward())
        self.toolbar.addWidget(self.act_fwd)

        # Reload
        self.act_reload = QPushButton(self.reload_icon, "")
        self.act_reload.setToolTip("Reload")
        self.act_reload.clicked.connect(lambda: self.current_view().reload())
        self.toolbar.addWidget(self.act_reload)

        # Home
        self.act_home = QPushButton(self.home_icon, "")
        self.act_home.setToolTip("Home")
        home_url = HOME_URL if not config.get('onboarding_complete') else POST_ONBOARDING_URL
        self.act_home.clicked.connect(lambda: self.navigate_to(home_url))
        self.toolbar.addWidget(self.act_home)

        # Address bar
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter URL or search term...")
        self.url_edit.returnPressed.connect(self.on_url_entered)
        self.url_edit.focusInEvent = self.on_url_focus
        self.toolbar.addWidget(self.url_edit)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Gaze toggle (eye icon)
        self.gaze_btn = QPushButton(self.gaze_on_icon, "")
        self.gaze_btn.setToolTip("Toggle gaze highlighting (per tab)")
        self.gaze_btn.clicked.connect(self.toggle_gaze_for_current_tab)
        self.toolbar.addWidget(self.gaze_btn)

        # Focus Mode
        self.focus_btn = QPushButton(self.focus_icon, "")
        self.focus_btn.setToolTip("Toggle Focus Mode (removes styles)")
        self.focus_btn.setCheckable(True)
        self.focus_btn.clicked.connect(self.toggle_focus_mode)
        self.toolbar.addWidget(self.focus_btn)

        # Settings
        self.settings_btn = QPushButton(self.settings_icon, "")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        self.toolbar.addWidget(self.settings_btn)

    def add_new_tab(self, url, label):
        # ... (same as before)
        tab = BrowserTab(start_url=url)
        tab.view.page().setWebChannel(self.channel)
        
        index = self.tabs.addTab(tab, label)
        self.tabs.setCurrentIndex(index)

        tab.view.titleChanged.connect(partial(self.on_title_changed, tab))
        tab.view.urlChanged.connect(partial(self.on_url_changed, tab))
        tab.view.loadFinished.connect(partial(self.on_load_finished_inject, tab))

        if self.tabs.currentIndex() == index:
             self.url_edit.setText(url)
        return tab

    def close_tab(self, idx):
        if self.tabs.count() == 1:
            return 
        
        tab_to_remove = self.tabs.widget(idx)
        self.tabs.removeTab(idx)
        tab_to_remove.deleteLater() 

    def current_tab(self) -> BrowserTab | None:
        # ... (same as before)
        return self.tabs.currentWidget()

    def current_view(self) -> BrowserView | None:
        t = self.current_tab()
        return t.view if t else None

    def navigate_to(self, url_text):
        if not url_text:
            return
        
        view = self.current_view()
        if not view:
            return

        if "://" in url_text or url_text.startswith("qrc:///"):
            q = QUrl(url_text)
        else:
            q = QUrl.fromUserInput(url_text)
            
        view.setUrl(q)

    # --- NEW: Helper for home page search ---
    def navigate_to_search(self, term):
        """Navigates the current tab to a search query."""
        view = self.current_view()
        if not view or not term:
            return
            
        search_engine_name = config.get('searchEngine', 'Google')
        search_url = SEARCH_ENGINES.get(search_engine_name, "https://www.google.com/search?q={}")
        query_url = search_url.format(term.replace(' ', '+'))
        view.setUrl(QUrl.fromUserInput(query_url))
        
    def on_url_entered(self):
        """Handles the user entering a URL or search term in the address bar."""
        text = self.url_edit.text().strip()
        if not text:
            return
        
        # Simple check: if it has a dot or '://' or 'qrc:', treat as URL.
        # Otherwise, treat as search.
        if "." in text or "://" in text or text.startswith("qrc:"):
            self.navigate_to(text)
        else:
            self.navigate_to_search(text)

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
                # 1. Inject Gaze Handler
                highlight_color = config.get('highlightColor', 'rgba(255, 200, 0, 0.35)')
                font = config.get('font', 'Poppins')
                alignment = config.get('highlightAlignment', 'center')
                reading_mask = config.get('readingMask', True)
                tts_hover_time = config.get('ttsHoverTime', 1.0)
                js = get_js_gaze_handler(highlight_color, font, alignment, reading_mask, tts_hover_time)
                tab.view.page().runJavaScript(js)

                # --- FIX: Re-apply focus mode if it's on for this tab ---
                if tab.focus_mode_enabled:
                    focus_js = get_focus_mode_js(True)
                    tab.view.page().runJavaScript(focus_js)

            except Exception as e:
                print(f"Error injecting JS: {e}")

        # Delay injection slightly to ensure page JS is loaded
        QTimer.singleShot(INJECT_DELAY_MS, do_inject)

    def dispatch_gaze_to_active_tab(self):
        """Dispatches the current gaze position to the active tab's web view."""
        tab = self.current_tab()
        if not tab or not tab.gaze_enabled:
            return

        global_pos = QCursor.pos()
        local_pt = tab.view.mapFromGlobal(global_pos)
        vw = tab.view.width() or 1
        vh = tab.view.height() or 1
        
        # Only dispatch if cursor is inside the view
        if 0 <= local_pt.x() <= vw and 0 <= local_pt.y() <= vh:
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
        
        # --- FIX: Store state on the tab ---
        tab.gaze_enabled = not tab.gaze_enabled
        
        self.status.showMessage(f"Gaze highlighting {'enabled' if tab.gaze_enabled else 'disabled'} for this tab.", 3000)
        
        # --- FIX: Update icon based on state ---
        self.gaze_btn.setIcon(self.gaze_on_icon if tab.gaze_enabled else self.gaze_off_icon)

    def toggle_focus_mode(self):
        """Toggles the focus mode for the current tab."""
        tab = self.current_tab()
        if not tab:
            return

        # --- FIX: Store state on the tab ---
        tab.focus_mode_enabled = self.focus_btn.isChecked()

        js = get_focus_mode_js(tab.focus_mode_enabled)
        tab.view.page().runJavaScript(js)

    def open_settings(self):
        """Opens the settings page in a new tab."""
        self.add_new_tab(SETTINGS_URL, "Settings")

    # --- NEW: Slot for syncing UI when tab changes ---
    def on_tab_changed(self, index):
        """Updates toolbar buttons to reflect the new tab's state."""
        tab = self.current_tab()
        if not tab:
            return

        # Update Gaze Button
        self.gaze_btn.setIcon(self.gaze_on_icon if tab.gaze_enabled else self.gaze_off_icon)

        # Update Focus Button
        self.focus_btn.setChecked(tab.focus_mode_enabled)

        # Update URL bar
        self.url_edit.setText(tab.view.url().toString())

    # --- NEW: Slot for auto-selecting URL text ---
    def on_url_focus(self, event):
        """Select all text in the URL bar on focus."""
        self.url_edit.selectAll()
        # Propagate the event
        QLineEdit.focusInEvent(self.url_edit, event)

    # --- NEW: Helper for WebChannel ---
    def reload_all_tabs_after_settings_change(self):
        """Called by WebChannelHandler after settings are saved."""
        home_url = POST_ONBOARDING_URL # Onboarding is now complete
        
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            current_url = tab.view.url().toString()
            
            # Re-point home tabs to new home page
            if current_url == HOME_URL or current_url == SETTINGS_URL:
                tab.view.setUrl(QUrl(home_url))
            else:
                # Reload other tabs to apply new JS settings
                tab.view.reload()