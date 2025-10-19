# dyslexim/main.py

import sys

from PyQt6.QtWidgets import QApplication

from core.main_window import DysleximMainWindow


def main():
    """Initializes and runs the Dyslexim application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Dyslexim")

    window = DysleximMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()