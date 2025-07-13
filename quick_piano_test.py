#!/usr/bin/env python3
"""
Quick piano click audio test - minimal GUI test
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_piano_audio():
    """Test piano widget audio functionality"""
    from src.ui.piano_roll_widget import PianoRollWidget
    from src.audio_system import initialize_audio_manager, AudioSettings
    from src.midi_routing import initialize_midi_routing, get_midi_routing_manager
    
    print("Initializing audio systems...")
    
    # Initialize audio
    soundfont_path = os.path.join('soundfonts', 'MuseScore_General.sf2')
    audio_settings = AudioSettings(
        sample_rate=44100,
        buffer_size=1024,
        gain=0.5,
        soundfont_path=soundfont_path if os.path.exists(soundfont_path) else None
    )
    audio_init = initialize_audio_manager(audio_settings)
    print(f"Audio init: {audio_init}")
    
    # Initialize MIDI routing
    midi_init = initialize_midi_routing()
    if midi_init:
        midi_router = get_midi_routing_manager()
        if midi_router:
            midi_router.set_primary_output("internal_fluidsynth")
    
    # Create and test piano roll
    piano_roll = PianoRollWidget()
    
    # Test preview note directly
    print("Testing preview note...")
    result = piano_roll._play_track_preview(60, 100)  # C4
    print(f"Preview note result: {result}")
    
    print("Audio test completed")
    return result

def main():
    print("Quick Piano Audio Test")
    print("=" * 25)
    
    app = QApplication(sys.argv)
    
    try:
        result = test_piano_audio()
        if result:
            print("✓ Audio preview is working!")
        else:
            print("✗ Audio preview failed")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()