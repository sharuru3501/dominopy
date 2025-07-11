#!/usr/bin/env python3
"""
Simple FluidSynth test without GUI
"""
import sys
import time

def simple_fluidsynth_test():
    """Test FluidSynth directly without PyDomino"""
    print("🎵 Simple FluidSynth Test...")
    
    try:
        print("1. Importing fluidsynth...")
        import fluidsynth
        print("   ✓ FluidSynth import successful")
        
        print("2. Creating FluidSynth instance...")
        fs = fluidsynth.Synth(samplerate=44100, gain=0.5)
        print("   ✓ FluidSynth instance created")
        
        print("3. Starting audio driver...")
        fs.start()
        print("   ✓ Audio driver started")
        
        print("4. Loading soundfont...")
        soundfont_path = "/Users/shinnosuke/dev/pydominodev/soundfonts/MuseScore_General.sf2"
        sfid = fs.sfload(soundfont_path)
        print(f"   Soundfont loaded: {sfid}")
        
        if sfid != -1:
            print("5. Setting program...")
            fs.program_select(0, sfid, 0, 0)
            print("   ✓ Program selected")
            
            print("6. Playing test note...")
            print("   Playing C4 (pitch 60) for 2 seconds...")
            fs.noteon(0, 60, 100)
            print("   ✓ Note on sent")
            
            time.sleep(2.0)
            
            print("7. Stopping note...")
            fs.noteoff(0, 60)
            print("   ✓ Note off sent")
            
            print("8. Playing chord...")
            print("   Playing C major chord...")
            fs.noteon(0, 60, 100)  # C
            fs.noteon(0, 64, 100)  # E
            fs.noteon(0, 67, 100)  # G
            print("   ✓ Chord notes on sent")
            
            time.sleep(1.5)
            
            fs.noteoff(0, 60)
            fs.noteoff(0, 64)
            fs.noteoff(0, 67)
            print("   ✓ Chord notes off sent")
            
            print("9. Test complete!")
            print("   Did you hear the audio? (C4 note + C major chord)")
            
        else:
            print("   ✗ Failed to load soundfont")
            return False
        
        print("10. Cleaning up...")
        fs.delete()
        print("    ✓ FluidSynth cleaned up")
        
        return True
        
    except ImportError:
        print("   ✗ FluidSynth not available")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simple_fluidsynth_test()
    print(f"\nSimple FluidSynth test {'PASSED' if success else 'FAILED'}")
    if success:
        print("If you heard audio, FluidSynth is working correctly.")
        print("If you didn't hear audio, there may be a system audio issue.")
    else:
        print("FluidSynth test failed - check the error messages above.")