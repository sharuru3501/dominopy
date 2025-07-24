"""
SoundFont Management System
Handles discovery, loading, and management of SoundFont files
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

@dataclass
class SoundFontInfo:
    """Information about a SoundFont file"""
    name: str
    path: str
    size: int
    is_builtin: bool
    is_user_added: bool
    description: str = ""
    
    @property
    def size_mb(self) -> float:
        """Size in MB"""
        return self.size / (1024 * 1024)

class SoundFontManager(QObject):
    """Manages SoundFont files for PyDomino"""
    
    # Signals
    soundfonts_changed = Signal()
    soundfont_loaded = Signal(str)  # path
    soundfont_error = Signal(str)   # error message
    
    def __init__(self):
        super().__init__()
        self.user_soundfont_dir = self._get_user_soundfont_dir()
        self.builtin_soundfont_dir = self._get_builtin_soundfont_dir()
        self._ensure_user_directory()
        
    def _get_user_soundfont_dir(self) -> str:
        """Get user soundfont directory (macOS Application Support)"""
        return os.path.expanduser("~/Library/Application Support/PyDomino/soundfonts")
    
    def _get_builtin_soundfont_dir(self) -> str:
        """Get builtin soundfont directory"""
        import sys
        
        if getattr(sys, 'frozen', False):
            # PyInstaller bundle
            app_dir = os.path.dirname(sys.executable)
            return os.path.join(app_dir, '..', 'Resources', 'soundfonts')
        else:
            # Development environment
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            return os.path.join(project_root, "soundfonts")
    
    def _ensure_user_directory(self):
        """Ensure user soundfont directory exists"""
        os.makedirs(self.user_soundfont_dir, exist_ok=True)
        
        # Create a README file for user guidance
        readme_path = os.path.join(self.user_soundfont_dir, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, 'w') as f:
                f.write("""PyDomino SoundFont Directory

This directory is where you can place additional SoundFont (.sf2) files
for use with PyDomino.

To add a new SoundFont:
1. Download a .sf2 file
2. Copy it to this directory
3. Restart PyDomino
4. Select the new SoundFont in Audio Sources

Recommended SoundFonts:
- FluidR3_GM.sf2 (high quality, ~141MB)
- MuseScore_General.sf2 (excellent quality, ~200MB)

Note: Please ensure you have the right to use any SoundFont files
you place in this directory.
""")
    
    def scan_soundfonts(self) -> List[SoundFontInfo]:
        """Scan for all available SoundFont files"""
        soundfonts = []
        
        # Scan builtin soundfonts
        if os.path.exists(self.builtin_soundfont_dir):
            for sf_path in glob.glob(os.path.join(self.builtin_soundfont_dir, "*.sf2")):
                if os.path.isfile(sf_path) and os.path.getsize(sf_path) > 1000:  # Skip tiny files
                    name = os.path.basename(sf_path)
                    soundfonts.append(SoundFontInfo(
                        name=name,
                        path=sf_path,
                        size=os.path.getsize(sf_path),
                        is_builtin=True,
                        is_user_added=False,
                        description=self._get_soundfont_description(name)
                    ))
        
        # Scan user soundfonts
        if os.path.exists(self.user_soundfont_dir):
            for sf_path in glob.glob(os.path.join(self.user_soundfont_dir, "*.sf2")):
                if os.path.isfile(sf_path) and os.path.getsize(sf_path) > 1000:  # Skip tiny files
                    name = os.path.basename(sf_path)
                    soundfonts.append(SoundFontInfo(
                        name=name,
                        path=sf_path,
                        size=os.path.getsize(sf_path),
                        is_builtin=False,
                        is_user_added=True,
                        description=self._get_soundfont_description(name)
                    ))
        
        # Sort by name
        soundfonts.sort(key=lambda x: x.name.lower())
        return soundfonts
    
    def _get_soundfont_description(self, name: str) -> str:
        """Get description for known SoundFont files"""
        descriptions = {
            "FluidR3_GM.sf2": "High-quality General MIDI SoundFont (141MB) - Default",
            "MuseScore_General.sf2": "Excellent quality General MIDI SoundFont (200MB)",
            "TimGM6mb.sf2": "Compact General MIDI SoundFont (6MB)",
            "Hiyameshi-DMG-STD.sf2": "Chiptune-style SoundFont",
        }
        return descriptions.get(name, "SoundFont file")
    
    def get_default_soundfont(self) -> Optional[str]:
        """Get path to default SoundFont"""
        # Try FluidR3_GM.sf2 first (our current default)
        fluidr3_path = os.path.join(self.builtin_soundfont_dir, "FluidR3_GM.sf2")
        if os.path.exists(fluidr3_path):
            return fluidr3_path
        
        # Try any builtin soundfont
        soundfonts = self.scan_soundfonts()
        builtin_soundfonts = [sf for sf in soundfonts if sf.is_builtin]
        if builtin_soundfonts:
            # Sort by size (larger soundfonts are typically better quality)
            builtin_soundfonts.sort(key=lambda x: x.size, reverse=True)
            return builtin_soundfonts[0].path
        
        return None
    
    def get_soundfont_info(self, path: str) -> Optional[SoundFontInfo]:
        """Get information about a specific SoundFont file"""
        if not os.path.exists(path):
            return None
        
        name = os.path.basename(path)
        size = os.path.getsize(path)
        is_builtin = path.startswith(self.builtin_soundfont_dir)
        
        return SoundFontInfo(
            name=name,
            path=path,
            size=size,
            is_builtin=is_builtin,
            is_user_added=not is_builtin,
            description=self._get_soundfont_description(name)
        )
    
    def install_soundfont(self, source_path: str) -> bool:
        """Install a SoundFont file to user directory"""
        if not os.path.exists(source_path):
            self.soundfont_error.emit(f"Source file not found: {source_path}")
            return False
        
        if not source_path.lower().endswith('.sf2'):
            self.soundfont_error.emit("File must be a SoundFont (.sf2) file")
            return False
        
        filename = os.path.basename(source_path)
        dest_path = os.path.join(self.user_soundfont_dir, filename)
        
        try:
            # Copy file
            with open(source_path, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            
            self.soundfont_loaded.emit(dest_path)
            self.soundfonts_changed.emit()
            return True
            
        except Exception as e:
            self.soundfont_error.emit(f"Failed to install SoundFont: {str(e)}")
            return False
    
    def remove_soundfont(self, path: str) -> bool:
        """Remove a user-added SoundFont file"""
        if not path.startswith(self.user_soundfont_dir):
            self.soundfont_error.emit("Can only remove user-added SoundFonts")
            return False
        
        try:
            os.remove(path)
            self.soundfonts_changed.emit()
            return True
        except Exception as e:
            self.soundfont_error.emit(f"Failed to remove SoundFont: {str(e)}")
            return False
    
    def open_user_soundfont_directory(self):
        """Open user soundfont directory in Finder (macOS)"""
        import subprocess
        subprocess.run(["open", self.user_soundfont_dir])

# Global instance
_soundfont_manager = None

def get_soundfont_manager() -> SoundFontManager:
    """Get the global SoundFont manager instance"""
    global _soundfont_manager
    if _soundfont_manager is None:
        _soundfont_manager = SoundFontManager()
    return _soundfont_manager