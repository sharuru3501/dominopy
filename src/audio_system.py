"""
Audio system for MIDI playback using FluidSynth
"""
import os
import sys
import threading
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

try:
    import fluidsynth
    FLUIDSYNTH_AVAILABLE = True
except ImportError:
    FLUIDSYNTH_AVAILABLE = False
    print("Warning: FluidSynth not available. Audio playback will be disabled.")

import rtmidi
from PySide6.QtCore import QObject, Signal, QTimer, QThread
from src.midi_data_model import MidiNote
from src.logger import print_debug

# Import macOS-specific audio if available
if sys.platform == "darwin":
    try:
        from src.macos_audio import MacOSAudioEngine, MacOSSystemAudio, MACOS_AUDIO_AVAILABLE
    except ImportError:
        MACOS_AUDIO_AVAILABLE = False
else:
    MACOS_AUDIO_AVAILABLE = False

@dataclass
class AudioSettings:
    """Audio system settings"""
    sample_rate: int = 44100
    buffer_size: int = 1024
    gain: float = 0.5
    soundfont_path: Optional[str] = None
    midi_device_id: Optional[int] = None

class FluidSynthAudio(QObject):
    """FluidSynth-based audio engine"""
    
    # Signals
    audio_error = Signal(str)
    audio_ready = Signal()
    
    def __init__(self, settings: AudioSettings):
        super().__init__()
        self.settings = settings
        self.fs: Optional[Any] = None
        self.sfid: Optional[int] = None
        self.is_initialized = False
        
        # Default soundfont paths to try
        self.default_soundfont_paths = [
            "/usr/share/sounds/sf2/FluidR3_GM.sf2",  # Linux
            "/usr/share/soundfonts/FluidR3_GM.sf2",  # Linux alternative
            "/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls",  # macOS
            "C:\\Windows\\system32\\drivers\\gm.dls",  # Windows
        ]
    
    def initialize(self) -> bool:
        """Initialize FluidSynth audio engine"""
        if not FLUIDSYNTH_AVAILABLE:
            self.audio_error.emit("FluidSynth not available")
            return False
        
        try:
            # Create FluidSynth instance with zero gain initially to prevent startup pops
            self.fs = fluidsynth.Synth(
                samplerate=self.settings.sample_rate,
                gain=0.0  # Start with zero gain to completely prevent startup pops
            )
            
            # Load soundfont before starting driver to avoid audio artifacts
            soundfont_path = self._find_soundfont()
            if soundfont_path:
                self.sfid = self.fs.sfload(soundfont_path)
                if self.sfid != -1:
                    # Select bank 0 and program 0 (General MIDI) while muted
                    self.fs.program_select(0, self.sfid, 0, 0)
                    print_debug(f"FluidSynth: Loaded soundfont and selected program 0 (Piano)")
                else:
                    print_debug(f"FluidSynth: Failed to load soundfont: {soundfont_path}")
                    return False
            else:
                print_debug("FluidSynth: No soundfont found")
                return False
            
            # Start audio driver with explicit CoreAudio driver for macOS
            if sys.platform == "darwin":
                self.fs.start(driver='coreaudio')
            else:
                self.fs.start()
            
            # Extended delay to let audio system fully stabilize
            time.sleep(0.2)
            
            # Gradually increase gain to prevent pop noise
            try:
                # Slowly ramp up gain from 0 to target level
                target_gain = self.settings.gain
                steps = 10
                for i in range(steps + 1):
                    current_gain = (target_gain * i) / steps
                    self.fs.setting('synth.gain', current_gain)
                    time.sleep(0.01)  # 10ms delay between steps
                print_debug(f"FluidSynth: Gain smoothly increased to {target_gain}")
            except Exception as e:
                print(f"Warning: Could not set FluidSynth gain: {e}")
            
            self.is_initialized = True
            self.audio_ready.emit()
            print_debug(f"Audio initialized with soundfont: {soundfont_path}")
            return True
                
        except Exception as e:
            self.audio_error.emit(f"Audio initialization error: {str(e)}")
            return False
    
    def _find_soundfont(self) -> Optional[str]:
        """Find an available soundfont file"""
        # Try user-specified soundfont first
        if self.settings.soundfont_path and os.path.exists(self.settings.soundfont_path):
            return self.settings.soundfont_path
        
        # Use the new SoundFont manager
        try:
            from src.soundfont_manager import get_soundfont_manager
            soundfont_manager = get_soundfont_manager()
            
            # Try to get the default soundfont
            default_path = soundfont_manager.get_default_soundfont()
            if default_path:
                return default_path
        except ImportError:
            print_debug("SoundFont manager not available, using fallback")
        
        # Fallback to original logic
        search_paths = [
            "soundfonts/",
            "./soundfonts/",
            "/usr/share/sounds/sf2/",
            "/usr/share/soundfonts/",
            os.path.expanduser("~/Library/Application Support/DominoPy/soundfonts/"),
            os.path.expanduser("~/soundfonts/"),
            ".",
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for file in os.listdir(search_path):
                    if file.endswith('.sf2'):
                        sf2_path = os.path.join(search_path, file)
                        # Skip very small files (likely placeholders)
                        if os.path.getsize(sf2_path) > 10000:  # At least 10KB
                            return sf2_path
        
        # Fallback to default locations (may not be compatible)
        for path in self.default_soundfont_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def play_note(self, channel: int, pitch: int, velocity: int) -> bool:
        """Play a MIDI note"""
        if not self.is_initialized:
            return False
        
        try:
            self.fs.noteon(channel, pitch, velocity)
            return True
        except Exception as e:
            self.audio_error.emit(f"Error playing note: {str(e)}")
            return False
    
    def stop_note(self, channel: int, pitch: int) -> bool:
        """Stop a MIDI note"""
        if not self.is_initialized:
            return False
        
        try:
            self.fs.noteoff(channel, pitch)
            return True
        except Exception as e:
            self.audio_error.emit(f"Error stopping note: {str(e)}")
            return False
    
    def set_program(self, channel: int, program: int) -> bool:
        """Set MIDI program (instrument)"""
        if not self.is_initialized:
            return False
        
        try:
            self.fs.program_change(channel, program)
            return True
        except Exception as e:
            self.audio_error.emit(f"Error setting program: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.fs:
            try:
                self.fs.delete()
                self.fs = None
                self.is_initialized = False
                print_debug("Audio system cleaned up")
            except Exception as e:
                print_debug(f"Error cleaning up audio: {str(e)}")

class MidiOutputDevice(QObject):
    """MIDI output device using python-rtmidi"""
    
    # Signals
    midi_error = Signal(str)
    midi_ready = Signal()
    
    def __init__(self, device_id: Optional[int] = None):
        super().__init__()
        self.device_id = device_id
        self.midi_out: Optional[rtmidi.MidiOut] = None
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """Initialize MIDI output device"""
        try:
            self.midi_out = rtmidi.MidiOut()
            
            # List available ports
            ports = self.midi_out.get_ports()
            print_debug(f"Available MIDI ports: {ports}")
            
            if self.device_id is not None and self.device_id < len(ports):
                # Use specified device
                self.midi_out.open_port(self.device_id)
                self.is_initialized = True
                self.midi_ready.emit()
                print_debug(f"MIDI output connected to: {ports[self.device_id]}")
                return True
            elif ports:
                # Use first available port
                self.midi_out.open_port(0)
                self.is_initialized = True
                self.midi_ready.emit()
                print_debug(f"MIDI output connected to: {ports[0]}")
                return True
            else:
                # Create virtual port
                self.midi_out.open_virtual_port("DominoPy Output")
                self.is_initialized = True
                self.midi_ready.emit()
                print_debug("MIDI virtual port created: DominoPy Output")
                return True
                
        except Exception as e:
            self.midi_error.emit(f"MIDI initialization error: {str(e)}")
            return False
    
    def send_note_on(self, channel: int, pitch: int, velocity: int) -> bool:
        """Send MIDI note on message"""
        if not self.is_initialized:
            return False
        
        try:
            message = [0x90 | channel, pitch, velocity]
            self.midi_out.send_message(message)
            return True
        except Exception as e:
            self.midi_error.emit(f"Error sending note on: {str(e)}")
            return False
    
    def send_note_off(self, channel: int, pitch: int) -> bool:
        """Send MIDI note off message"""
        if not self.is_initialized:
            return False
        
        try:
            message = [0x80 | channel, pitch, 0]
            self.midi_out.send_message(message)
            return True
        except Exception as e:
            self.midi_error.emit(f"Error sending note off: {str(e)}")
            return False
    
    def send_program_change(self, channel: int, program: int) -> bool:
        """Send MIDI program change message"""
        if not self.is_initialized:
            return False
        
        try:
            message = [0xC0 | channel, program]
            self.midi_out.send_message(message)
            return True
        except Exception as e:
            self.midi_error.emit(f"Error sending program change: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up MIDI resources"""
        if self.midi_out:
            try:
                self.midi_out.close_port()
                self.midi_out = None
                self.is_initialized = False
                print_debug("MIDI output cleaned up")
            except Exception as e:
                print_debug(f"Error cleaning up MIDI: {str(e)}")

class AudioManager(QObject):
    """Main audio manager that handles both FluidSynth and MIDI output"""
    
    # Signals
    audio_ready = Signal()
    audio_error = Signal(str)
    
    def __init__(self, settings: AudioSettings):
        super().__init__()
        self.settings = settings
        self.fluidsynth_audio: Optional[FluidSynthAudio] = None
        self.midi_device: Optional[MidiOutputDevice] = None
        self.use_fluidsynth = True
        self.current_channel = 0
        self.current_program = 0
        self.active_notes: Dict[int, float] = {}  # pitch -> start_time
        
        # Note duration for preview playback (in seconds)
        self.preview_note_duration = 0.5
        
        # Timer for stopping preview notes
        self.note_stop_timer = QTimer()
        self.note_stop_timer.timeout.connect(self._stop_preview_notes)
        self.note_stop_timer.setSingleShot(False)
        # Don't start timer immediately - start it only when needed
    
    def initialize(self) -> bool:
        """Initialize audio system"""
        success = False
        
        # Try FluidSynth first (best audio quality)
        if FLUIDSYNTH_AVAILABLE:
            self.fluidsynth_audio = FluidSynthAudio(self.settings)
            self.fluidsynth_audio.audio_ready.connect(self._on_audio_ready)
            self.fluidsynth_audio.audio_error.connect(self._on_audio_error)
            
            fs_init_success = self.fluidsynth_audio.initialize()
            print_debug(f"FluidSynthAudio.initialize() returned: {fs_init_success}")
            if fs_init_success:
                self.use_fluidsynth = True
                success = True
                print_debug("Using FluidSynth for audio playback")
        
        # Try macOS native audio as fallback
        if not success and sys.platform == "darwin" and MACOS_AUDIO_AVAILABLE:
            try:
                # Prioritize MacOSAudioEngine for proper MIDI playback
                self.macos_audio = MacOSAudioEngine()
                self.macos_audio.audio_ready.connect(self._on_audio_ready)
                self.macos_audio.audio_error.connect(self._on_audio_error)
                
                macos_engine_init_success = self.macos_audio.initialize()
                print_debug(f"MacOSAudioEngine.initialize() returned: {macos_engine_init_success}")
                if macos_engine_init_success:
                    self.use_fluidsynth = False
                    success = True
                    print_debug("Using macOS AVAudioEngine for playback")
            except Exception as e:
                print_debug(f"macOS AVAudioEngine failed: {e}")
                # Fallback to MacOSSystemAudio if AVAudioEngine fails
                try:
                    macos_system_init_success = self.macos_audio.initialize()
                    print_debug(f"MacOSSystemAudio.initialize() returned: {macos_system_init_success}")
                    if macos_system_init_success:
                        self.use_fluidsynth = False
                        success = True
                        print_debug("Using macOS system audio for playback (fallback)")
                except Exception as e:
                    print_debug(f"macOS system audio failed: {e}")
        
        # Final fallback to MIDI output (silent but functional)
        if not success:
            self.midi_device = MidiOutputDevice(self.settings.midi_device_id)
            self.midi_device.midi_ready.connect(self._on_audio_ready)
            self.midi_device.midi_error.connect(self._on_audio_error)
            
            if self.midi_device.initialize():
                self.use_fluidsynth = False
                success = True
                print_debug("Using MIDI output for audio playback (may be silent)")
        
        if success:
            self.audio_ready.emit()
            # Start timer only after successful initialization
            self.note_stop_timer.start(50)  # Check every 50ms
            print_debug("AudioManager: Audio system initialized successfully.")
        else:
            print_debug("AudioManager: No audio output available")
        
        return success
        
    def play_note_preview(self, pitch: int, velocity: int = 100) -> bool:
        """Play a note for preview purposes (e.g., piano roll click)"""
        success = False
        
        # Try macOS audio first
        if MACOS_AUDIO_AVAILABLE and hasattr(self, 'macos_audio') and self.macos_audio:
            success = self.macos_audio.play_note(self.current_channel, pitch, velocity)
            if success: print_debug(f"AudioManager: Preview via macOS Audio (pitch={pitch})")
        # Try FluidSynth
        elif self.use_fluidsynth and self.fluidsynth_audio:
            success = self.fluidsynth_audio.play_note(self.current_channel, pitch, velocity)
            if success: print_debug(f"AudioManager: Preview via FluidSynth (pitch={pitch})")
        # Fallback to MIDI output
        elif self.midi_device:
            success = self.midi_device.send_note_on(self.current_channel, pitch, velocity)
            if success: print_debug(f"AudioManager: Preview via MIDI Output (pitch={pitch})")
        
        if success:
            self.active_notes[pitch] = time.time()  # Store start time for auto-stop
        return success
    
    def play_note_immediate(self, pitch: int, velocity: int = 100, channel: int = None) -> bool:
        """Play a note immediately (for playback engine)"""
        success = False
        
        # Use provided channel or fall back to current_channel
        use_channel = channel if channel is not None else self.current_channel
        
        # Try macOS audio first
        if MACOS_AUDIO_AVAILABLE and hasattr(self, 'macos_audio') and self.macos_audio:
            success = self.macos_audio.play_note(use_channel, pitch, velocity)
            if success: print_debug(f"AudioManager: Immediate play via macOS Audio (ch={use_channel}, pitch={pitch})")
        # Try FluidSynth
        elif self.use_fluidsynth and self.fluidsynth_audio:
            success = self.fluidsynth_audio.play_note(use_channel, pitch, velocity)
            if success: print_debug(f"AudioManager: Immediate play via FluidSynth (ch={use_channel}, pitch={pitch})")
        # Fallback to MIDI output
        elif self.midi_device:
            success = self.midi_device.send_note_on(use_channel, pitch, velocity)
            if success: print_debug(f"AudioManager: Immediate play via MIDI Output (pitch={pitch})")
        
        # Don't add to active_notes for auto-stop (playback engine handles timing)
        return success
    
    def stop_note_immediate(self, pitch: int, channel: int = None) -> bool:
        """Stop a note immediately (for playback engine)"""
        success = False
        
        # Use provided channel or fall back to current_channel
        use_channel = channel if channel is not None else self.current_channel
        
        # Try macOS audio first
        if MACOS_AUDIO_AVAILABLE and hasattr(self, 'macos_audio') and self.macos_audio:
            success = self.macos_audio.stop_note(use_channel, pitch)
            if success: print_debug(f"AudioManager: Immediate stop via macOS Audio (ch={use_channel}, pitch={pitch})")
        # Try FluidSynth
        elif self.use_fluidsynth and self.fluidsynth_audio:
            success = self.fluidsynth_audio.stop_note(use_channel, pitch)
            if success: print_debug(f"AudioManager: Immediate stop via FluidSynth (ch={use_channel}, pitch={pitch})")
        # Fallback to MIDI output
        elif self.midi_device:
            success = self.midi_device.send_note_off(use_channel, pitch)
            if success: print_debug(f"AudioManager: Immediate stop via MIDI Output (ch={use_channel}, pitch={pitch})")
        
        # Don't modify active_notes (playback engine handles timing)
        return success
    
    def stop_note_preview(self, pitch: int) -> bool:
        """Stop a note preview"""
        success = False
        
        # Try macOS audio first
        if MACOS_AUDIO_AVAILABLE and hasattr(self, 'macos_audio') and self.macos_audio:
            success = self.macos_audio.stop_note(self.current_channel, pitch)
            if success: print_debug(f"AudioManager: Preview stop via macOS Audio (pitch={pitch})")
        # Try FluidSynth
        elif self.use_fluidsynth and self.fluidsynth_audio:
            success = self.fluidsynth_audio.stop_note(self.current_channel, pitch)
            if success: print_debug(f"AudioManager: Preview stop via FluidSynth (pitch={pitch})")
        # Fallback to MIDI output
        elif self.midi_device:
            success = self.midi_device.send_note_off(self.current_channel, pitch)
            if success: print_debug(f"AudioManager: Preview stop via MIDI Output (pitch={pitch})")
        
        if success and pitch in self.active_notes:
            del self.active_notes[pitch]
        return success
    
    def _stop_preview_notes(self):
        """Stop preview notes that have been playing too long"""
        current_time = time.time()
        notes_to_stop = []
        
        for pitch, start_time in self.active_notes.items():
            if current_time - start_time > self.preview_note_duration:
                notes_to_stop.append(pitch)
        
        for pitch in notes_to_stop:
            self.stop_note_preview(pitch)
    
    def set_program(self, program: int) -> bool:
        """Set MIDI program (instrument)"""
        if program is None:
            print_debug("AudioManager: Cannot set program to None - track has no instrument")
            return False
            
        self.current_program = program
        
        if self.use_fluidsynth and self.fluidsynth_audio:
            return self.fluidsynth_audio.set_program(self.current_channel, program)
        elif self.midi_device:
            return self.midi_device.send_program_change(self.current_channel, program)
        
        return False
    
    def set_channel(self, channel: int):
        """Set MIDI channel"""
        self.current_channel = channel
    
    def _on_audio_ready(self):
        """Handle audio ready signal"""
        print_debug("Audio system ready")
    
    def _on_audio_error(self, error: str):
        """Handle audio error signal"""
        print_debug(f"Audio error: {error}")
        self.audio_error.emit(error)
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.note_stop_timer:
            self.note_stop_timer.stop()
        
        if hasattr(self, 'macos_audio') and self.macos_audio:
            self.macos_audio.cleanup()
        
        if self.fluidsynth_audio:
            self.fluidsynth_audio.cleanup()
        
        if self.midi_device:
            self.midi_device.cleanup()
        
        print_debug("Audio manager cleaned up")

# Global audio manager instance
audio_manager: Optional[AudioManager] = None

def get_audio_manager() -> Optional[AudioManager]:
    """Get the global audio manager instance"""
    return audio_manager

def initialize_audio_manager(settings: AudioSettings) -> bool:
    """Initialize the global audio manager"""
    global audio_manager
    
    if audio_manager is not None:
        audio_manager.cleanup()
    
    audio_manager = AudioManager(settings)
    init_success = audio_manager.initialize()
    print_debug(f"initialize_audio_manager() returning: {init_success}")
    return init_success

def cleanup_audio_manager():
    """Clean up the global audio manager"""
    global audio_manager
    
    if audio_manager:
        audio_manager.cleanup()
        audio_manager = None