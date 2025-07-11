#!/usr/bin/env python3
"""
Investigate the difference between working and non-working audio paths
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeyEvent

def investigate_audio_paths():
    """Compare working vs non-working audio paths"""
    print("🔍 Investigating Audio Path Differences...")
    
    app = QApplication(sys.argv)
    
    def run_investigation():
        try:
            from src.ui.main_window import PyDominoMainWindow
            from src.playback_engine import get_playback_engine
            from src.audio_system import get_audio_manager
            from src.midi_routing import get_midi_routing_manager
            
            window = PyDominoMainWindow()
            window.show()
            
            def setup_test():
                print("✓ Creating test song...")
                window._create_test_song()
                
                def detailed_investigation():
                    audio_manager = get_audio_manager()
                    midi_router = get_midi_routing_manager()
                    engine = get_playback_engine()
                    
                    print("\n📊 Detailed System Analysis:")
                    
                    # 1. Audio Manager Analysis
                    if audio_manager:
                        print(f"\n🎵 Audio Manager:")
                        print(f"   - Initialized: {getattr(audio_manager, 'is_initialized', 'Unknown')}")
                        print(f"   - Use FluidSynth: {getattr(audio_manager, 'use_fluidsynth', 'Unknown')}")
                        print(f"   - FluidSynth Audio: {getattr(audio_manager, 'fluidsynth_audio', 'Unknown')}")
                        print(f"   - Current Channel: {getattr(audio_manager, 'current_channel', 'Unknown')}")
                        
                        # Check FluidSynth audio object
                        if hasattr(audio_manager, 'fluidsynth_audio') and audio_manager.fluidsynth_audio:
                            fs_audio = audio_manager.fluidsynth_audio
                            print(f"   - FS Initialized: {getattr(fs_audio, 'is_initialized', 'Unknown')}")
                            print(f"   - FS Sample Rate: {getattr(fs_audio, 'sample_rate', 'Unknown')}")
                            print(f"   - FS Buffer Size: {getattr(fs_audio, 'buffer_size', 'Unknown')}")
                    
                    # 2. MIDI Router Analysis
                    if midi_router:
                        print(f"\n🎛️ MIDI Router:")
                        routing_info = midi_router.get_routing_info()
                        print(f"   - Primary: {routing_info['primary_output']}")
                        print(f"   - Connections: {routing_info['active_connections']}")
                        print(f"   - Internal Audio: {routing_info['internal_audio_enabled']}")
                    
                    def test_working_path():
                        print("\n✅ Testing WORKING Path (Right-click equivalent):")
                        
                        # Test the working audio path
                        if audio_manager:
                            print("   Calling play_note_preview...")
                            result = audio_manager.play_note_preview(60, 100)
                            print(f"   Result: {'SUCCESS' if result else 'FAILED'}")
                            
                            def stop_preview():
                                audio_manager.stop_note_preview(60)
                                print("   Preview stopped")
                            
                            QTimer.singleShot(1000, stop_preview)
                        
                        def test_immediate_path():
                            print("\n🔧 Testing IMMEDIATE Path (Used by MIDI routing):")
                            
                            if audio_manager:
                                print("   Calling play_note_immediate...")
                                result = audio_manager.play_note_immediate(62, 100)
                                print(f"   Result: {'SUCCESS' if result else 'FAILED'}")
                                
                                def stop_immediate():
                                    audio_manager.stop_note_immediate(62)
                                    print("   Immediate stopped")
                                
                                QTimer.singleShot(1000, stop_immediate)
                            
                            def test_midi_routing_path():
                                print("\n🔀 Testing MIDI Routing Path:")
                                
                                if midi_router:
                                    print("   Calling midi_router.play_note...")
                                    try:
                                        midi_router.play_note(0, 64, 100)
                                        print("   MIDI routing call succeeded")
                                        
                                        def stop_midi():
                                            midi_router.stop_note(0, 64)
                                            print("   MIDI routing stopped")
                                        
                                        QTimer.singleShot(1000, stop_midi)
                                    except Exception as e:
                                        print(f"   MIDI routing error: {e}")
                                
                                def test_engine_playback():
                                    print("\n⚙️ Testing ENGINE Playback Path:")
                                    
                                    # Start engine playback and monitor
                                    space_key = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier)
                                    window.piano_roll.keyPressEvent(space_key)
                                    print("   Engine playback started...")
                                    
                                    def monitor_engine():
                                        if engine:
                                            print(f"   Engine state: {engine.get_state()}")
                                            print(f"   Current tick: {engine.current_tick}")
                                            print(f"   Active notes: {engine.active_notes}")
                                        
                                        # Check what's happening in the timer
                                        def stop_and_analyze():
                                            space_key2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier)
                                            window.piano_roll.keyPressEvent(space_key2)
                                            
                                            print("\n📋 Investigation Summary:")
                                            print("Compare which audio paths work vs don't work")
                                            print("- Preview path: Should work ✓")
                                            print("- Immediate path: Check if working ✓/✗")
                                            print("- MIDI routing path: Check if working ✓/✗")
                                            print("- Engine playback: Check if working ✓/✗")
                                            
                                            app.quit()
                                        
                                        QTimer.singleShot(2000, stop_and_analyze)
                                    
                                    QTimer.singleShot(1000, monitor_engine)
                                
                                QTimer.singleShot(2000, test_engine_playback)
                            
                            QTimer.singleShot(2000, test_midi_routing_path)
                        
                        QTimer.singleShot(2000, test_immediate_path)
                    
                    QTimer.singleShot(1000, test_working_path)
                
                QTimer.singleShot(1000, detailed_investigation)
            
            QTimer.singleShot(3000, setup_test)
            
        except Exception as e:
            print(f"✗ Investigation error: {e}")
            import traceback
            traceback.print_exc()
            app.quit()
    
    QTimer.singleShot(1000, run_investigation)
    
    result = app.exec()
    print(f"Audio path investigation completed. Exit code: {result}")
    return result == 0

if __name__ == "__main__":
    success = investigate_audio_paths()
    print(f"Investigation {'COMPLETED' if success else 'FAILED'}")