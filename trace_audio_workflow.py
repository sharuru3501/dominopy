#!/usr/bin/env python3
"""
Trace the complete audio workflow in PyDomino step by step
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeyEvent

def trace_audio_workflow():
    """Trace complete audio workflow in PyDomino"""
    print("🔍 Tracing Complete PyDomino Audio Workflow...")
    
    app = QApplication(sys.argv)
    
    def run_trace():
        try:
            from src.ui.main_window import PyDominoMainWindow
            from src.playback_engine import get_playback_engine
            from src.audio_system import get_audio_manager
            from src.midi_routing import get_midi_routing_manager
            
            window = PyDominoMainWindow()
            window.show()
            
            def setup_trace():
                print("✓ Setting up trace environment...")
                window._create_test_song()
                
                audio_manager = get_audio_manager()
                midi_router = get_midi_routing_manager()
                engine = get_playback_engine()
                
                def step_by_step_trace():
                    print("\n🔍 Step-by-Step Audio Workflow Trace:")
                    
                    print("\n1. Manual Preview Test (Known Working):")
                    print("   Calling audio_manager.play_note_preview(60, 100)...")
                    if audio_manager:
                        result = audio_manager.play_note_preview(60, 100)
                        print(f"   → Result: {result}")
                        print("   → Expected: Audio should play NOW")
                        
                        def stop_preview():
                            audio_manager.stop_note_preview(60)
                            print("   → Preview stopped")
                        
                        QTimer.singleShot(2000, stop_preview)
                    
                    def test_midi_routing_manual():
                        print("\n2. MIDI Routing Manual Test:")
                        print("   Calling midi_router.play_note(0, 62, 100)...")
                        if midi_router:
                            midi_router.play_note(0, 62, 100)
                            print("   → MIDI routing call made")
                            print("   → Expected: Audio should play NOW")
                            
                            def stop_midi():
                                midi_router.stop_note(0, 62)
                                print("   → MIDI routing stopped")
                            
                            QTimer.singleShot(2000, stop_midi)
                        
                        def test_engine_manual():
                            print("\n3. Engine Manual Event Test:")
                            if engine:
                                from src.playback_engine import PlaybackEvent
                                from src.midi_data_model import MidiNote
                                
                                test_note = MidiNote(pitch=64, start_tick=0, end_tick=480, velocity=100)
                                test_event = PlaybackEvent(
                                    timestamp=0.0,
                                    tick=0,
                                    note=test_note,
                                    event_type="note_on"
                                )
                                
                                print("   Calling engine._schedule_event manually...")
                                engine._schedule_event(test_event)
                                print("   → Engine event scheduled")
                                print("   → Expected: Audio should play NOW")
                                
                                def stop_engine_test():
                                    test_event_off = PlaybackEvent(
                                        timestamp=1.0,
                                        tick=480,
                                        note=test_note,
                                        event_type="note_off"
                                    )
                                    engine._schedule_event(test_event_off)
                                    print("   → Engine note off scheduled")
                                
                                QTimer.singleShot(2000, stop_engine_test)
                            
                            def test_full_playback():
                                print("\n4. Full Playback Test (The Problem Case):")
                                print("   Starting full playback sequence...")
                                
                                # Monitor for the first few events
                                original_schedule = engine._schedule_event
                                event_count = [0]
                                
                                def monitored_schedule(event):
                                    event_count[0] += 1
                                    print(f"   📡 Event #{event_count[0]}: {event.event_type} note {event.note.pitch} at tick {event.tick}")
                                    print(f"      → Calling original _schedule_event...")
                                    result = original_schedule(event)
                                    print(f"      → Expected: Audio should play NOW for note {event.note.pitch}")
                                    return result
                                
                                # Temporarily replace the method for monitoring
                                engine._schedule_event = monitored_schedule
                                
                                # Start playback
                                space_key = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier)
                                window.piano_roll.keyPressEvent(space_key)
                                print("   ▶️ Playback started...")
                                print("   → Watch for audio events above...")
                                
                                def stop_and_analyze():
                                    # Restore original method
                                    engine._schedule_event = original_schedule
                                    
                                    # Stop playback
                                    space_key2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier)
                                    window.piano_roll.keyPressEvent(space_key2)
                                    
                                    print("\n📊 Audio Workflow Analysis Complete:")
                                    print("You should have heard audio at these points:")
                                    print("1. Manual preview test ✓/✗")
                                    print("2. MIDI routing manual test ✓/✗")
                                    print("3. Engine manual event test ✓/✗")
                                    print("4. Full playback events ✓/✗")
                                    print("\nIf you heard audio for 1-3 but not 4:")
                                    print("→ The issue is in the playback timing/scheduling")
                                    print("If you heard no audio at all:")
                                    print("→ The issue is in the base audio system")
                                    print("If you heard all audio:")
                                    print("→ The system is working correctly!")
                                    
                                    app.quit()
                                
                                QTimer.singleShot(4000, stop_and_analyze)
                            
                            QTimer.singleShot(3000, test_full_playback)
                        
                        QTimer.singleShot(3000, test_engine_manual)
                    
                    QTimer.singleShot(3000, test_midi_routing_manual)
                
                QTimer.singleShot(3000, step_by_step_trace)
            
            QTimer.singleShot(3000, setup_trace)
            
        except Exception as e:
            print(f"✗ Trace error: {e}")
            import traceback
            traceback.print_exc()
            app.quit()
    
    QTimer.singleShot(1000, run_trace)
    
    result = app.exec()
    print(f"Audio workflow trace completed. Exit code: {result}")
    return result == 0

if __name__ == "__main__":
    success = trace_audio_workflow()
    print(f"Audio workflow trace {'COMPLETED' if success else 'FAILED'}")
    
    print("\n🎯 Key Questions for Diagnosis:")
    print("1. Did you hear audio during the manual preview test?")
    print("2. Did you hear audio during the MIDI routing manual test?")
    print("3. Did you hear audio during the engine manual event test?")
    print("4. Did you hear audio during the full playback sequence?")
    print("\nPlease let me know which of these produced audible sound!")