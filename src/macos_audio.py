"""
macOS-specific audio support using AVAudioEngine
"""
import sys
import time
from typing import Optional, Dict

try:
    if sys.platform == "darwin":
        # Import macOS-specific audio frameworks
        import objc
        from Foundation import NSObject
        from AVFoundation import (
            AVAudioEngine, AVAudioUnitSampler, AVAudioPlayerNode,
            AVAudioFormat, AVAudioSession, AVAudioSessionCategoryPlayback
        )
        MACOS_AUDIO_AVAILABLE = True
    else:
        MACOS_AUDIO_AVAILABLE = False
except ImportError:
    MACOS_AUDIO_AVAILABLE = False

from PySide6.QtCore import QObject, Signal


class MacOSAudioEngine(QObject):
    """macOS-specific audio engine using AVAudioEngine"""
    
    audio_ready = Signal()
    audio_error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.engine: Optional[object] = None
        self.sampler: Optional[object] = None
        self.is_initialized = False
        self.active_notes: Dict[int, float] = {}
        
    def initialize(self) -> bool:
        """Initialize macOS audio engine"""
        if not MACOS_AUDIO_AVAILABLE:
            self.audio_error.emit("macOS audio frameworks not available")
            return False
        
        try:
            # Create audio engine
            self.engine = AVAudioEngine.alloc().init()
            
            # Create sampler unit
            self.sampler = AVAudioUnitSampler.alloc().init()
            
            # Attach sampler to engine
            self.engine.attachNode_(self.sampler)
            
            # Connect sampler to main mixer
            format = self.engine.mainMixerNode().outputFormatForBus_(0)
            self.engine.connect_to_format_(
                self.sampler, 
                self.engine.mainMixerNode(), 
                format
            )
            
            # Load default General MIDI soundbank
            # This uses the built-in macOS General MIDI soundbank
            self.sampler.loadSoundBankInstrumentAtURL_program_bankMSB_bankLSB_error_(
                None,  # Use default soundbank
                0,     # Program 0 (Acoustic Grand Piano)
                0,     # Bank MSB
                0,     # Bank LSB
                None   # Error pointer
            )
            
            # Start the engine
            self.engine.startAndReturnError_(None)
            
            self.is_initialized = True
            self.audio_ready.emit()
            print("macOS audio engine initialized successfully")
            return True
            
        except Exception as e:
            self.audio_error.emit(f"macOS audio initialization error: {str(e)}")
            print(f"macOS audio error: {e}")
            return False
    
    def play_note(self, channel: int, pitch: int, velocity: int) -> bool:
        """Play a MIDI note"""
        if not self.is_initialized or not self.sampler:
            return False
        
        try:
            # Convert velocity to float (0.0 - 1.0)
            velocity_float = velocity / 127.0
            
            # Start note
            self.sampler.startNote_withVelocity_onChannel_(
                pitch,
                velocity_float,
                channel
            )
            
            self.active_notes[pitch] = time.time()
            return True
            
        except Exception as e:
            self.audio_error.emit(f"Error playing note: {str(e)}")
            return False
    
    def stop_note(self, channel: int, pitch: int) -> bool:
        """Stop a MIDI note"""
        if not self.is_initialized or not self.sampler:
            return False
        
        try:
            self.sampler.stopNote_onChannel_(pitch, channel)
            
            if pitch in self.active_notes:
                del self.active_notes[pitch]
            
            return True
            
        except Exception as e:
            self.audio_error.emit(f"Error stopping note: {str(e)}")
            return False
    
    def set_program(self, channel: int, program: int) -> bool:
        """Set MIDI program (instrument)"""
        if not self.is_initialized or not self.sampler:
            return False
        
        try:
            # Load different instrument
            self.sampler.loadSoundBankInstrumentAtURL_program_bankMSB_bankLSB_error_(
                None,     # Use default soundbank
                program,  # Program number
                0,        # Bank MSB
                0,        # Bank LSB
                None      # Error pointer
            )
            return True
            
        except Exception as e:
            self.audio_error.emit(f"Error setting program: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.engine:
            try:
                self.engine.stop()
                self.engine = None
                self.sampler = None
                self.is_initialized = False
                print("macOS audio engine cleaned up")
            except Exception as e:
                print(f"Error cleaning up macOS audio: {str(e)}")


# Alternative simple approach using system sounds
class MacOSSystemAudio(QObject):
    """Simple macOS audio using system beeps"""
    
    audio_ready = Signal()
    audio_error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """Initialize system audio"""
        try:
            import subprocess
            # Test if we can run system commands
            subprocess.run(['echo', 'test'], capture_output=True, check=True)
            self.is_initialized = True
            self.audio_ready.emit()
            print("macOS system audio initialized")
            return True
        except Exception as e:
            self.audio_error.emit(f"System audio error: {str(e)}")
            return False
    
    def play_note(self, channel: int, pitch: int, velocity: int) -> bool:
        """Play a note using system beep"""
        if not self.is_initialized:
            return False
        
        try:
            import subprocess
            # Use afplay to play a system sound
            # This is a simple fallback - just plays a beep
            subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                         capture_output=True, timeout=1)
            return True
        except Exception:
            # If that fails, try the terminal bell
            try:
                print('\a', end='', flush=True)  # Terminal bell
                return True
            except Exception:
                return False
    
    def stop_note(self, channel: int, pitch: int) -> bool:
        """Stop note (no-op for system sounds)"""
        return True
    
    def set_program(self, channel: int, program: int) -> bool:
        """Set program (no-op for system sounds)"""
        return True
    
    def cleanup(self):
        """Cleanup (no-op for system sounds)"""
        self.is_initialized = False
        print("System audio cleaned up")