#!/usr/bin/env python3
"""
PyDomino Application Launcher
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the application
from src.main import main

if __name__ == "__main__":
    print("Starting PyDomino...")
    print("Features available:")
    print("- 🎵 Note Input Mode (Key: 1)")
    print("- 📐 Selection Mode (Key: 2)")
    print("- ⇄ Toggle Mode (Key: Tab)")
    print("- 📋 Copy/Paste (Ctrl+C/V)")
    print("- ↩️ Undo/Redo (Ctrl+Z/Y)")
    print("- 🎹 MIDI File Support")
    print()
    
    # Run the application
    main()