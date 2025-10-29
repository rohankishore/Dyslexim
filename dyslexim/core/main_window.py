from functools import partial
import json

from PyQt6.QtCore import Qt, QTimer, QUrl, QObject, pyqtSlot
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
        print(f"Settings received from JS: {color}, {font}, {alignment}, {readingMask}, {ttsHoverTime}, {searchEngine}")
        config['highlightColor'] = color
        config['font'] = font
        config['highlightAlignment'] = alignment
        config['readingMask'] = readingMask
        config['ttsHoverTime'] = ttsHoverTime
        config['searchEngine'] = searchEngine
        config['onboarding_complete'] = True
        save_config(config)
        
        # Reload all tabs to apply new settings
        if self.parent():
            self.parent().reload_all_tabs_after_settings_change()

    @pyqtSlot(result=str)
    def loadSettings(self):
        """Called by JS on the settings page to get current config."""
        print("JS requested current settings, sending...")
        return json.dumps(config)


class DysleximMainWindow(QMainWindow):
    """The main application window, managing tabs and the toolbar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyslexim")
        self.resize(1200, 780)
        
        # Load standard icons
        self.load_icons()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        # --- FIX: Connect tab changed signal for UI sync ---
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView).availableSizes()[0])
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.add_toolbar_items()

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — gaze simulation: mouse. Toggle with the eye icon.")

        # Set up the web channel
        self.channel = QWebChannel(self)
        self.handler = WebChannelHandler(self)
        self.channel.registerObject('handler', self.handler)

        if config.get('onboarding_complete', False):
            self.add_new_tab(POST_ONBOARDING_URL, "Home")
        else:
            self.add_new_tab(HOME_URL, "Welcome to Dyslexim")

        self.gaze_timer = QTimer(self)
        self.gaze_timer.timeout.connect(self.dispatch_gaze_to_active_tab)
        self.gaze_timer.start(GAZE_UPDATE_INTERVAL_MS)

        self.set_stylesheet()

    def load_icons(self):
        """Loads and stores standard icons."""
        style = self.style()
        self.back_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        self.fwd_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        self.reload_icon = style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self.home_icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.settings_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogOptions)
        
        # Icons for toggle buttons
        self.gaze_on_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        self.gaze_off_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.focus_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)


    def set_stylesheet(self):
        """Sets the modern stylesheet for the application."""
        self.setStyleSheet("""
            QMainWindow { 
                background: #0d1117; 
            }
            QToolBar { 
                background: #161b22;
                border-bottom: 1px solid #30363d;
                spacing: 8px; 
                padding: 8px 12px;
            }
            QLineEdit { 
                background: #0d1117; 
                color: #c9d1d9; 
                border: 1px solid #30363d; 
                padding: 8px 12px; 
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2f81f7;
                box-shadow: 0 0 5px #2f81f7;
            }
            QTabWidget::pane { 
                border-top: 1px solid #30363d; 
            }
            QTabBar::tab { 
                background: #161b22; 
                color: #8b949e; 
                padding: 10px 14px; 
                border: 1px solid #30363d; 
                border-bottom: none; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px;
                margin-right: 1px;
            }
            QTabBar::tab:selected { 
                background: #0d1117; 
                color: #c9d1d9;
                border-bottom: 1px solid #0d1117; /* Hides pane border */
            }
            QTabBar::tab:!selected:hover {
                background: #21262d;
                color: #c9d1d9;
            }
            QTabBar::close-button {
                image: url(icons/close.svg); /* You'll need a close icon */
            }
            
            /* --- Modern Toolbar Buttons --- */
            QPushButton { 
                color: #c9d1d9; 
                background: #21262d; 
                border: 1px solid #30363d;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover { 
                background: #30363d;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background: #2a3037;
            }
            /* Special "New Tab" button */
            QPushButton#newtab { 
                background: #238636; 
                border-color: #2ea043;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton#newtab:hover {
                background: #2ea043;
            }
            /* Icon-only buttons (Back, Fwd, etc) */
            QToolBar > QPushButton {
                background: transparent;
                border: none;
                padding: 6px;
            }
            QToolBar > QPushButton:hover {
                background: #21262d;
            }
            QToolBar > QPushButton:pressed {
                background: #30363d;
            }
            QToolBar > QPushButton:checked {
                background: #1a3c68; /* Blue tint for "on" state */
            }
            
            QStatusBar {
                color: #8b949e;
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
        # --- UX: Auto-select text on click ---
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

        # New Tab
        newtab_btn = QPushButton("+ New Tab")
        newtab_btn.setObjectName("newtab")
        newtab_btn.clicked.connect(lambda: self.add_new_tab(POST_ONBOARDING_URL, "New Tab"))
        self.toolbar.addWidget(newtab_btn)

    def add_new_tab(self, url, label):
        """Adds a new browser tab to the tab widget."""
        # --- FIX: Use the new BrowserTab class ---
        tab = BrowserTab(start_url=url)
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
            return # Don't close the last tab
        
        tab_to_remove = self.tabs.widget(idx)
        self.tabs.removeTab(idx)
        tab_to_remove.deleteLater() # Ensure proper cleanup

    def current_tab(self) -> BrowserTab | None:
        """Returns the currently active BrowserTab."""
        return self.tabs.currentWidget()

    def current_view(self) -> BrowserView | None:
        """Returns the web view of the currently active tab."""
        t = self.current_tab()
        return t.view if t else None

    def navigate_to(self, url_text):
        """Navigates the current tab to the given URL string."""
        if not url_text:
            return
        
        view = self.current_view()
        if not view:
            return

        if "://" in url_text or url_text.startswith("qrc:///"):
            q = QUrl(url_text)
        else:
            q = QUrl.fromUserInput(url_text) # Handles file paths
            
        view.setUrl(q)

    def on_url_entered(self):
        """Handles the user entering a URL or search term in the address bar."""
        text = self.url_edit.text().strip()
        if not text:
            return
        
        view = self.current_view()
        if not view:
            return

        # Check for search term (no dot and contains space, or not a URL)
        is_search = " " in text and "." not in text and "://" not in text
        
        if is_search:
            search_engine_name = config.get('searchEngine', 'Google')
            search_url = SEARCH_ENGINES.get(search_engine_name, "https://www.google.com/search?q={}")
            query_url = search_url.format(text.replace(' ', '+'))
            view.setUrl(QUrl.fromUserInput(query_url))
        else:
            view.setUrl(QUrl.fromUserInput(text))

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