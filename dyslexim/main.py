import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dyslexim Demo</title>
<style>
body {
  font-family: 'Segoe UI', sans-serif;
  background: #FAF9F6;
  color: #222;
  padding: 40px;
  line-height: 1.6;
}
.__highlight {
  outline: 3px solid rgba(255, 200, 0, 0.4);
  outline-offset: 3px;
  background-color: rgba(255, 255, 0, 0.08);
}
</style>
</head>
<body>
<h1>Welcome to Dyslexim</h1>
<p>This is a prototype demonstrating gaze-based focus.</p>
<p>Move your mouse — the element under the pointer will highlight. Later, this will be driven by real eye tracking.</p>
<p>We can adapt spacing, colors, or scrolling dynamically based on user focus.</p>
</body>
</html>
"""

JS_GAZE_HANDLER = """
window.__dyslexim_handleGaze = function(normX, normY) {
  const w = document.documentElement.clientWidth;
  const h = document.documentElement.clientHeight;
  const x = Math.round(normX * w);
  const y = Math.round(normY * h);
  let el = document.elementFromPoint(x, y);
  if (!el) return;
  if (window.__prevEl && window.__prevEl !== el) {
    window.__prevEl.classList.remove('__highlight');
  }
  el.classList.add('__highlight');
  window.__prevEl = el;
};
"""

class DysleximBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyslexim Prototype")
        self.resize(1000, 700)
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        # Load local HTML content
        self.view.setHtml(HTML_PAGE)

        # Inject our JS after load
        self.view.loadFinished.connect(self.inject_js)

        # Track mouse as fake gaze
        self.setMouseTracking(True)
        self.view.setMouseTracking(True)
        self.mouse_x = 0
        self.mouse_y = 0

        # Periodic gaze update (20 Hz)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gaze)
        self.timer.start(50)

    def inject_js(self):
        self.view.page().runJavaScript(JS_GAZE_HANDLER)

    def mouseMoveEvent(self, event):
        # Convert mouse coords to normalized
        self.mouse_x = event.position().x() / self.width()
        self.mouse_y = event.position().y() / self.height()

    def update_gaze(self):
        js = f"window.__dyslexim_handleGaze({self.mouse_x:.4f}, {self.mouse_y:.4f});"
        self.view.page().runJavaScript(js)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = DysleximBrowser()
    browser.show()
    sys.exit(app.exec())
