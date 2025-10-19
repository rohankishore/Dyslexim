# dyslexim_browser_modern.py
import sys
from functools import partial

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QIcon, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStyle, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# ---------- Configuration ----------
HOME_URL = "https://www.example.com"
INJECT_DELAY_MS = 220  # small delay before injecting handler after loadFinished
GAZE_UPDATE_INTERVAL_MS = 50  # 20Hz

# ---------- JavaScript to inject into pages ----------
# This is robust (idempotent) and defines window.__dyslexim_handleGaze(...)
# It does minimal DOM thrash and stores previous inline styles to revert later.
JS_GAZE_HANDLER = """
(function(){
  if (window.__dyslexim_handler_installed) return;
  window.__dyslexim_handler_installed = true;
  window.__dyslexim_prevEl = null;

  window.__dyslexim_handleGaze = function(normX, normY) {
    try {
      const w = document.documentElement.clientWidth || window.innerWidth;
      const h = document.documentElement.clientHeight || window.innerHeight;
      const x = Math.round(Math.max(0, Math.min(1, normX)) * w);
      const y = Math.round(Math.max(0, Math.min(1, normY)) * h);

      let el = document.elementFromPoint(x, y);
      if (!el) {
        // fallback small offsets
        const els = document.elementsFromPoint(x+6, y) || [];
        el = els[0] || null;
      }
      if (!el) return;

      // avoid reapplying to same element
      if (window.__dyslexim_prevEl === el) return;

      // cleanup previous
      if (window.__dyslexim_prevEl) {
        window.__dyslexim_prevEl.classList.remove('__dyslexim_highlight');
        if (window.__dyslexim_prevEl.__dyslexim_prevStyles) {
          const prev = window.__dyslexim_prevEl.__dyslexim_prevStyles;
          for (const k in prev) {
            window.__dyslexim_prevEl.style[k] = prev[k];
          }
          window.__dyslexim_prevEl.__dyslexim_prevStyles = null;
        }
      }

      // add highlight and adjust spacing for text-like elements
      el.classList.add('__dyslexim_highlight');
      const tag = el.tagName ? el.tagName.toLowerCase() : '';
      const textLike = tag === 'p' || tag === 'span' || tag === 'div' || el.closest('article') || el.closest('p');
      if (textLike) {
        el.__dyslexim_prevStyles = {
          lineHeight: el.style.lineHeight || '',
          letterSpacing: el.style.letterSpacing || '',
          backgroundColor: el.style.backgroundColor || ''
        };
        el.style.transition = 'all 0.12s ease';
        el.style.lineHeight = '1.8';
        el.style.letterSpacing = '0.04em';
        el.style.backgroundColor = 'rgba(255,255,0,0.03)';
      }

      // auto-scroll into view if off-screen
      const rect = el.getBoundingClientRect();
      if (rect.top < 24 || rect.bottom > h - 24) {
        el.scrollIntoView({behavior:'smooth', block:'center'});
      }

      window.__dyslexim_prevEl = el;
    } catch (e) {
      // Don't spam console on edge cases
      // console.error('Dyslexim gaze handler error', e);
    }
  };

  // minimal CSS for highlight (scoped so it won't clash badly)
  (function() {
    const style = document.createElement('style');
    style.setAttribute('data-dyslexim', '1');
    style.textContent = `
      .__dyslexim_highlight {
        outline: 3px solid rgba(255, 200, 0, 0.35) !important;
        outline-offset: 3px !important;
        background-color: rgba(255,255,0,0.04) !important;
        transition: outline 0.12s ease !important;
      }
    `;
    document.head && document.head.appendChild(style);
  })();

  // marker for dev
  // console.log('Dyslexim handler installed');
})();
"""

# ---------- Helper: a single web tab container ----------
class BrowserTab(QWidget):
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

# ---------- Main window ----------
class DysleximMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyslexim")
        self.resize(1200, 780)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        # top toolbar (modern style)
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView).availableSizes()[0] if self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView).availableSizes() else Qt.QSize(16,16))
        self.addToolBar(self.toolbar)
        self.add_toolbar_items()

        # status bar for messages
        self.status = self.statusBar()
        self.status.showMessage("Ready — gaze simulation: mouse. Toggle with the eye icon.")

        # create initial tab
        self.add_new_tab(HOME_URL, "Home")

        # gaze update timer (sends normalized cursor pos to the active tab)
        self.gaze_timer = QTimer(self)
        self.gaze_timer.timeout.connect(self.dispatch_gaze_to_active_tab)
        self.gaze_timer.start(GAZE_UPDATE_INTERVAL_MS)

        # minimal modern stylesheet
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

    # ---------- Toolbar UI ----------
    def add_toolbar_items(self):
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
        self.act_home.triggered.connect(lambda: self.navigate_to(HOME_URL))
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
        eye_icon = QIcon.fromTheme("view-preview")  # fallback to system icon if present
        self.gaze_btn = QPushButton()
        self.gaze_btn.setToolTip("Toggle gaze highlighting (per tab)")
        self.gaze_btn.setText("👁️")
        self.gaze_btn.clicked.connect(self.toggle_gaze_for_current_tab)
        self.toolbar.addWidget(self.gaze_btn)

        # New Tab
        newtab_btn = QPushButton("+ New Tab")
        newtab_btn.setObjectName("newtab")
        newtab_btn.clicked.connect(lambda: self.add_new_tab(HOME_URL, "New Tab"))
        self.toolbar.addWidget(newtab_btn)

    # ---------- Tab management ----------
    def add_new_tab(self, url, label):
        tab = BrowserTab(self, start_url=url)
        index = self.tabs.addTab(tab, label)
        self.tabs.setCurrentIndex(index)
        # UI updates on page title/url changes
        tab.view.titleChanged.connect(partial(self.on_title_changed, tab))
        tab.view.urlChanged.connect(partial(self.on_url_changed, tab))
        # On load finished, inject the handler after a short delay
        tab.view.loadFinished.connect(partial(self.on_load_finished_inject, tab))
        # update address bar initially
        self.url_edit.setText(url)
        return tab

    def close_tab(self, idx):
        if self.tabs.count() == 1:
            return
        self.tabs.removeTab(idx)

    def current_tab(self):
        return self.tabs.currentWidget()

    def current_view(self):
        t = self.current_tab()
        return t.view if t else None

    # ---------- Navigation ----------
    def navigate_to(self, url_text):
        if not url_text:
            return
        if "://" not in url_text:
            # treat as search
            q = QUrl.fromUserInput(url_text)
        else:
            q = QUrl(url_text)
        view = self.current_view()
        if view:
            view.setUrl(q)

    def on_url_entered(self):
        text = self.url_edit.text().strip()
        # allow user to type "example.com" or search
        if text == "":
            return
        if " " in text and "://" not in text:
            # search
            query = QUrl.fromUserInput(f"https://www.google.com/search?q={text.replace(' ', '+')}")
            self.current_view().setUrl(query)
        else:
            self.current_view().setUrl(QUrl.fromUserInput(text))

    def on_title_changed(self, tab, title):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            self.tabs.setTabText(idx, title[:30])

    def on_url_changed(self, tab, url):
        if tab is self.current_tab():
            self.url_edit.setText(url.toString())

    # ---------- Injection & Gaze dispatch ----------
    def on_load_finished_inject(self, tab, ok):
        # Called on each page load. We'll inject handler after a slight delay to avoid races.
        if not ok:
            return
        def do_inject():
            try:
                tab.view.page().runJavaScript(JS_GAZE_HANDLER)
                # double-check: set a flag in Python if JS ready
                def check_ready(result):
                    # result is typeof window.__dyslexim_handleGaze
                    if result == "function":
                        # we could store per-tab readiness if needed; for now rely on guarded calls
                        # print("Injected dyslexim handler into page.")
                        pass
                tab.view.page().runJavaScript("typeof window.__dyslexim_handleGaze;", check_ready)
            except Exception:
                pass
        QTimer.singleShot(INJECT_DELAY_MS, do_inject)

    def dispatch_gaze_to_active_tab(self):
        # mouse as gaze simulator: map global cursor into current QWebEngineView
        tab = self.current_tab()
        if not tab:
            return
        if not getattr(tab, "gaze_enabled", True):
            return

        # Map global cursor to local coordinates of the view
        global_pos = QCursor.pos()
        local_pt = tab.view.mapFromGlobal(global_pos)
        vw = tab.view.width() or 1
        vh = tab.view.height() or 1
        norm_x = max(0.0, min(1.0, local_pt.x() / vw))
        norm_y = max(0.0, min(1.0, local_pt.y() / vh))

        # Guarded JS call (no exceptions even if handler missing)
        js = f"""
        (function(){{
          if (window.__dyslexim_handleGaze && typeof window.__dyslexim_handleGaze === 'function') {{
            try {{ window.__dyslexim_handleGaze({norm_x:.4f}, {norm_y:.4f}); }} catch(e){{ }}
          }}
        }})();
        """
        tab.view.page().runJavaScript(js)

    # ---------- Per-tab gaze toggle ----------
    def toggle_gaze_for_current_tab(self):
        tab = self.current_tab()
        if not tab:
            return
        tab.gaze_enabled = not getattr(tab, "gaze_enabled", True)
        self.status.showMessage(f"Gaze highlighting {'enabled' if tab.gaze_enabled else 'disabled'} for this tab.", 3000)
        # quick visual feedback on button
        self.gaze_btn.setText("👁️" if tab.gaze_enabled else "🚫")

# ---------- Entry ----------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dyslexim")
    window = DysleximMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
