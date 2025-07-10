#!/usr/bin/env python3
"""
Debug crash issues with PyDomino
"""
import sys
import os
import traceback
import signal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def crash_handler(signum, frame):
    """Handle crash signals"""
    print(f"\nCRASH DETECTED: Signal {signum}")
    print("Stack trace:")
    traceback.print_stack(frame)
    print("\nTrying to cleanup...")
    
    # Try to cleanup audio and playback systems
    try:
        from src.audio_system import cleanup_audio_manager
        from src.playback_engine import cleanup_playback_engine
        cleanup_playback_engine()
        cleanup_audio_manager()
        print("Cleanup completed")
    except Exception as e:
        print(f"Cleanup failed: {e}")
    
    sys.exit(1)

def main():
    """Main debug application"""
    print("=== PyDomino Debug Mode ===")
    
    # Install signal handlers
    signal.signal(signal.SIGINT, crash_handler)
    signal.signal(signal.SIGTERM, crash_handler)
    
    try:
        # Import and run the application with extra error handling
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from src.ui.main_window import PyDominoMainWindow
        
        # Create QApplication with debug flags
        app = QApplication(sys.argv)
        app.setAttribute(Qt.AA_DontUseNativeDialogs)
        
        # Create and show main window
        window = PyDominoMainWindow()
        window.show()
        
        print("Application started successfully")
        print("Instructions:")
        print("1. Try to reproduce the crash")
        print("2. Watch the console for error messages")
        print("3. If it crashes, check the output above")
        
        # Run with exception handling
        try:
            exit_code = app.exec()
            print(f"Application exited normally with code: {exit_code}")
        except Exception as e:
            print(f"Application crashed with exception: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"Failed to start application: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()