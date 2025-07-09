import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import PyDominoMainWindow

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    window = PyDominoMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()