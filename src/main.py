import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import DominoPyMainWindow

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties (for macOS menu bar)
    app.setApplicationName("DominoPy")
    app.setApplicationDisplayName("DominoPy")
    app.setOrganizationName("DominoPy")
    app.setOrganizationDomain("dominopy.app")
    
    # Initialize MIDI routing early
    from src.midi_routing import initialize_midi_routing
    initialize_midi_routing()
    
    window = DominoPyMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()