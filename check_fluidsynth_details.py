#!/usr/bin/env python3
"""
Deep check of FluidSynth audio details
"""
import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def check_fluidsynth_details():
    """Check FluidSynth audio system in detail"""
    print("🔍 Deep FluidSynth Investigation...")
    
    app = QApplication(sys.argv)
    
    def run_check():
        try:
            from src.ui.main_window import PyDominoMainWindow
            from src.audio_system import get_audio_manager
            
            window = PyDominoMainWindow()
            window.show()
            
            def detailed_check():
                print("✓ Getting audio manager...")
                audio_manager = get_audio_manager()
                
                if not audio_manager:
                    print("✗ No audio manager found!")
                    app.quit()
                    return
                
                print(f"\n🎵 Audio Manager Details:")
                print(f"   - Manager type: {type(audio_manager)}")
                print(f"   - Use FluidSynth: {getattr(audio_manager, 'use_fluidsynth', 'Unknown')}")
                
                # Get FluidSynth audio object
                fs_audio = getattr(audio_manager, 'fluidsynth_audio', None)
                if fs_audio:
                    print(f"\n🔧 FluidSynth Audio Details:")
                    print(f"   - FS Audio type: {type(fs_audio)}")
                    print(f"   - Is initialized: {getattr(fs_audio, 'is_initialized', 'Unknown')}")
                    print(f"   - FluidSynth object: {getattr(fs_audio, 'fs', 'Unknown')}")
                    print(f"   - Soundfont ID: {getattr(fs_audio, 'sfid', 'Unknown')}")
                    
                    # Check FluidSynth object details
                    fs_obj = getattr(fs_audio, 'fs', None)
                    if fs_obj:
                        print(f"   - FS object type: {type(fs_obj)}")
                        print(f"   - FS object: {fs_obj}")
                        
                        # Check if audio driver is running
                        try:
                            # Try to get some info from FluidSynth
                            # Note: This depends on the fluidsynth library version
                            print(f"   - Checking FluidSynth status...")
                        except Exception as e:
                            print(f"   - FS status check error: {e}")
                
                def test_direct_fluidsynth():
                    print(f"\n🎯 Direct FluidSynth Test:")
                    
                    if fs_audio and fs_obj:
                        try:
                            print("   - Calling fs.noteon(0, 60, 100) directly...")
                            fs_obj.noteon(0, 60, 100)
                            print("   - Direct noteon call succeeded")
                            
                            def stop_direct():
                                try:
                                    print("   - Calling fs.noteoff(0, 60) directly...")
                                    fs_obj.noteoff(0, 60)
                                    print("   - Direct noteoff call succeeded")
                                except Exception as e:
                                    print(f"   - Direct noteoff error: {e}")
                            
                            QTimer.singleShot(2000, stop_direct)
                            
                        except Exception as e:
                            print(f"   - Direct noteon error: {e}")
                    
                    def test_audio_manager_immediate():
                        print(f"\n🔄 Audio Manager Immediate Test:")
                        
                        try:
                            print("   - Calling audio_manager.play_note_immediate(62, 100)...")
                            result = audio_manager.play_note_immediate(62, 100)
                            print(f"   - Immediate call result: {result}")
                            
                            def stop_immediate():
                                try:
                                    print("   - Calling audio_manager.stop_note_immediate(62)...")
                                    result = audio_manager.stop_note_immediate(62)
                                    print(f"   - Stop immediate result: {result}")
                                except Exception as e:
                                    print(f"   - Stop immediate error: {e}")
                            
                            QTimer.singleShot(2000, stop_immediate)
                            
                        except Exception as e:
                            print(f"   - Immediate call error: {e}")
                        
                        def check_audio_system():
                            print(f"\n🖥️ System Audio Check:")
                            
                            # Check if this is a headless system
                            try:
                                import os
                                if 'DISPLAY' in os.environ:
                                    print(f"   - DISPLAY: {os.environ['DISPLAY']}")
                                else:
                                    print("   - No DISPLAY environment variable")
                                
                                # Check audio devices
                                print("   - Checking audio devices...")
                                # This is system-specific, but let's see what we can find
                                
                            except Exception as e:
                                print(f"   - System check error: {e}")
                            
                            def final_summary():
                                print(f"\n📋 Investigation Summary:")
                                print("Possible reasons for no audio:")
                                print("1. FluidSynth audio driver not starting properly")
                                print("2. System audio output not configured")
                                print("3. Audio device permission issues")
                                print("4. FluidSynth soundfont loading issues")
                                print("5. Wrong audio driver (ALSA/PulseAudio/CoreAudio)")
                                
                                print("\nNext steps:")
                                print("- Check system audio configuration")
                                print("- Verify FluidSynth audio driver")
                                print("- Test with different audio settings")
                                
                                app.quit()
                            
                            QTimer.singleShot(1000, final_summary)
                        
                        QTimer.singleShot(3000, check_audio_system)
                    
                    QTimer.singleShot(4000, test_audio_manager_immediate)
                
                QTimer.singleShot(2000, test_direct_fluidsynth)
            
            QTimer.singleShot(3000, detailed_check)
            
        except Exception as e:
            print(f"✗ Check error: {e}")
            import traceback
            traceback.print_exc()
            app.quit()
    
    QTimer.singleShot(1000, run_check)
    
    result = app.exec()
    print(f"FluidSynth check completed. Exit code: {result}")
    return result == 0

if __name__ == "__main__":
    success = check_fluidsynth_details()
    print(f"FluidSynth check {'COMPLETED' if success else 'FAILED'}")