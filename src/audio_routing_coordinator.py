"""
Audio Routing Coordinator - Central authority for all multi-track audio routing

This module provides a unified interface for routing audio from tracks to output,
resolving conflicts between multiple audio systems and ensuring proper multi-track operation.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from src.midi_data_model import MidiNote
from src.audio_source_manager import AudioSource, AudioSourceType


class AudioRoutingState(Enum):
    """Audio routing system state"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"


@dataclass
class AudioRoute:
    """Represents an active audio route for a track"""
    track_index: int
    audio_source: AudioSource
    channel: int
    program: int
    is_active: bool = True
    last_used: float = 0.0


@dataclass
class AudioChannelState:
    """Represents the state of a MIDI channel"""
    channel: int
    assigned_track: Optional[int] = None
    current_program: int = 0  # 0-based GM program numbers
    active_notes: Set[int] = None
    
    def __post_init__(self):
        if self.active_notes is None:
            self.active_notes = set()


class AudioRoutingCoordinator:
    """
    Central coordinator for all audio routing in the multi-track MIDI sequencer.
    
    Responsibilities:
    - Unified track-to-audio-source mapping
    - MIDI channel allocation and conflict resolution
    - Consistent audio routing across all playback scenarios
    - Fallback handling when audio sources fail
    """
    
    def __init__(self):
        self.state = AudioRoutingState.UNINITIALIZED
        self.track_routes: Dict[int, AudioRoute] = {}
        self.channel_states: Dict[int, AudioChannelState] = {}
        self.reserved_channels: Set[int] = set()
        
        # Manager references (will be set during initialization)
        self.audio_manager = None
        self.audio_source_manager = None
        self.midi_routing_manager = None
        self.per_track_router = None
        
        # Initialize MIDI channel states (0-15)
        for channel in range(16):
            self.channel_states[channel] = AudioChannelState(channel=channel)
        
        print("AudioRoutingCoordinator: Created")
    
    def initialize(self) -> bool:
        """Initialize the coordinator with manager references"""
        self.state = AudioRoutingState.INITIALIZING
        
        try:
            # Import and get manager references
            from src.audio_system import get_audio_manager
            from src.audio_source_manager import get_audio_source_manager
            from src.midi_routing import get_midi_routing_manager
            from src.per_track_audio_router import get_per_track_audio_router
            
            self.audio_manager = get_audio_manager()
            self.audio_source_manager = get_audio_source_manager()
            self.midi_routing_manager = get_midi_routing_manager()
            self.per_track_router = get_per_track_audio_router()
            
            # Validate critical managers are available
            if not self.audio_source_manager:
                print("AudioRoutingCoordinator: Audio source manager not available")
                self.state = AudioRoutingState.ERROR
                return False
            
            print(f"AudioRoutingCoordinator: Managers - AM: {self.audio_manager is not None}, "
                  f"ASM: {self.audio_source_manager is not None}, "
                  f"MRM: {self.midi_routing_manager is not None}, "
                  f"PTR: {self.per_track_router is not None}")
            
            self.state = AudioRoutingState.READY
            print("AudioRoutingCoordinator: Initialized successfully")
            return True
            
        except Exception as e:
            print(f"AudioRoutingCoordinator: Initialization failed: {e}")
            self.state = AudioRoutingState.ERROR
            return False
    
    def setup_track_route(self, track_index: int) -> bool:
        """Set up audio routing for a specific track"""
        if self.state != AudioRoutingState.READY:
            print(f"AudioRoutingCoordinator: Not ready for track setup (state: {self.state})")
            return False
        
        print(f"AudioRoutingCoordinator: Setting up route for track {track_index}")
        
        # Get audio source for track
        audio_source = self.audio_source_manager.get_track_source(track_index)
        if not audio_source:
            print(f"AudioRoutingCoordinator: No audio source for track {track_index}")
            return False
        
        print(f"AudioRoutingCoordinator: Found audio source for track {track_index}: {audio_source.name} (type: {audio_source.source_type})")
        
        # Audio source found - proceed with routing setup
        
        # Check if audio source has a valid program (instrument)
        if audio_source.program is None:
            print(f"AudioRoutingCoordinator: Track {track_index} has no instrument assigned (program=None) - skipping route setup")
            return False
        
        print(f"AudioRoutingCoordinator: Track {track_index} program: {audio_source.program}, channel: {audio_source.channel}")
        
        # Allocate channel for track
        channel = self._allocate_channel(track_index, audio_source)
        if channel is None:
            print(f"AudioRoutingCoordinator: Could not allocate channel for track {track_index}")
            return False
        
        # Create route
        route = AudioRoute(
            track_index=track_index,
            audio_source=audio_source,
            channel=channel,
            program=audio_source.program,
            last_used=time.time()
        )
        print(f"🎵 Created route: track={track_index}, program={audio_source.program}, source={audio_source.name}")
        
        # Set up audio backend for this route
        success = self._setup_audio_backend(route)
        if not success:
            print(f"AudioRoutingCoordinator: Failed to setup audio backend for track {track_index}")
            self._release_channel(channel)
            return False
        
        # Store the route
        self.track_routes[track_index] = route
        
        # Update channel state
        self.channel_states[channel].assigned_track = track_index
        self.channel_states[channel].current_program = audio_source.program
        
        print(f"AudioRoutingCoordinator: Track {track_index} routed to {audio_source.name} on channel {channel}")
        return True
    
    def play_note(self, track_index: int, note: MidiNote) -> bool:
        """Play a note using the track's audio route"""
        # Get route for track
        route = self.track_routes.get(track_index)
        if not route:
            print(f"AudioRoutingCoordinator: No route for track {track_index}, attempting setup...")
            if not self.setup_track_route(track_index):
                print(f"AudioRoutingCoordinator: Failed to setup route for track {track_index}")
                return False
            route = self.track_routes.get(track_index)
            if not route:
                print(f"AudioRoutingCoordinator: Route setup failed - no route created for track {track_index}")
                return False
        
        # Verify route is still active
        if not route.is_active:
            print(f"AudioRoutingCoordinator: Route for track {track_index} is inactive, refreshing...")
            if not self.refresh_track_route(track_index):
                return False
            route = self.track_routes.get(track_index)
            if not route or not route.is_active:
                return False
        
        # Update last used time
        route.last_used = time.time()
        
        # Route audio based on source type
        success = self._route_note_on(route, note)
        
        if success:
            # Track active note
            self.channel_states[route.channel].active_notes.add(note.pitch)
            print(f"AudioRoutingCoordinator: Note {note.pitch} playing on track {track_index}, channel {route.channel}")
        else:
            print(f"AudioRoutingCoordinator: Failed to play note {note.pitch} on track {track_index}")
        
        return success
    
    def stop_note(self, track_index: int, note: MidiNote) -> bool:
        """Stop a note using the track's audio route"""
        route = self.track_routes.get(track_index)
        if not route:
            return False
        
        success = self._route_note_off(route, note)
        
        if success:
            # Stop tracking active note
            self.channel_states[route.channel].active_notes.discard(note.pitch)
            print(f"AudioRoutingCoordinator: Note {note.pitch} stopped on track {track_index}, channel {route.channel}")
        
        return success
    
    def _allocate_channel(self, track_index: int, audio_source: AudioSource) -> Optional[int]:
        """Allocate a MIDI channel for a track"""
        # For soundfont sources, use track index as preferred channel
        if audio_source.source_type == AudioSourceType.SOUNDFONT:
            preferred_channel = track_index % 16
            
            # Check if preferred channel is available
            if self.channel_states[preferred_channel].assigned_track is None:
                return preferred_channel
            
            # If preferred channel is occupied by same track, reuse it
            if self.channel_states[preferred_channel].assigned_track == track_index:
                return preferred_channel
            
            # Find next available channel
            for offset in range(1, 16):
                candidate = (preferred_channel + offset) % 16
                if self.channel_states[candidate].assigned_track is None:
                    return candidate
        
        # For external MIDI, use configured channel
        elif audio_source.source_type == AudioSourceType.EXTERNAL_MIDI:
            return audio_source.channel
        
        # For soundfonts, allocate next available channel
        else:
            for channel in range(16):
                if self.channel_states[channel].assigned_track is None:
                    return channel
        
        print(f"AudioRoutingCoordinator: No available MIDI channels")
        return None
    
    def _release_channel(self, channel: int):
        """Release a MIDI channel allocation"""
        if 0 <= channel < 16:
            self.channel_states[channel].assigned_track = None
            self.channel_states[channel].active_notes.clear()
    
    def _setup_audio_backend(self, route: AudioRoute) -> bool:
        """Set up the audio backend for a route"""
        if route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Set program for channel on internal FluidSynth
            if self.audio_manager and hasattr(self.audio_manager, 'fluidsynth_audio'):
                fluidsynth = self.audio_manager.fluidsynth_audio
                if fluidsynth and hasattr(fluidsynth, 'fs'):
                    try:
                        fluidsynth.fs.program_select(route.channel, fluidsynth.sfid, 0, route.program)
                        print(f"✅ AudioRoutingCoordinator: Set program {route.program} ({route.audio_source.name}) for channel {route.channel}")
                        return True
                    except Exception as e:
                        print(f"AudioRoutingCoordinator: Failed to set program: {e}")
                        return False
            return True
        
        elif route.audio_source.source_type == AudioSourceType.EXTERNAL_MIDI:
            # External MIDI setup would go here
            return True
        
        elif route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Soundfont setup would go here  
            return True
        
        return False
    
    def _route_note_on(self, route: AudioRoute, note: MidiNote) -> bool:
        """Route a note-on event through the appropriate audio backend"""
        if route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Ensure correct program is set before playing note
            channel_state = self.channel_states.get(route.channel)
            if channel_state and channel_state.current_program != route.program:
                # Program change needed
                if self.audio_manager and hasattr(self.audio_manager, 'fluidsynth_audio'):
                    fluidsynth = self.audio_manager.fluidsynth_audio
                    if fluidsynth and hasattr(fluidsynth, 'fs'):
                        try:
                            fluidsynth.fs.program_select(route.channel, fluidsynth.sfid, 0, route.program)
                            channel_state.current_program = route.program
                            print(f"🎵 Program changed to {route.program} ({route.audio_source.name}) on channel {route.channel}")
                        except Exception as e:
                            print(f"❌ Failed to change program: {e}")
            
            # Route through MIDI routing manager if available
            if self.midi_routing_manager:
                self.midi_routing_manager.play_note(route.channel, note.pitch, note.velocity)
                return True
            # Fallback to direct audio manager
            elif self.audio_manager:
                return self.audio_manager.play_note_immediate(note.pitch, note.velocity, route.channel)
        
        elif route.audio_source.source_type == AudioSourceType.EXTERNAL_MIDI:
            # Route through per-track router for external MIDI
            if self.per_track_router:
                instance = self.per_track_router.track_instances.get(route.track_index)
                if instance and hasattr(self.per_track_router, '_play_external_note'):
                    return self.per_track_router._play_external_note(instance, note)
                else:
                    # Generic per-track routing
                    return self.per_track_router.play_note(route.track_index, note)
        
        elif route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Route through per-track router for soundfonts
            if self.per_track_router:
                instance = self.per_track_router.track_instances.get(route.track_index)
                if instance and hasattr(self.per_track_router, '_play_soundfont_note'):
                    return self.per_track_router._play_soundfont_note(instance, note)
                else:
                    # Generic per-track routing
                    return self.per_track_router.play_note(route.track_index, note)
        
        return False
    
    def invalidate_track_route(self, track_index: int):
        """Invalidate and remove the route for a specific track"""
        if track_index in self.track_routes:
            route = self.track_routes[track_index]
            self._release_channel(route.channel)
            del self.track_routes[track_index]
            print(f"AudioRoutingCoordinator: Invalidated route for track {track_index}")
    
    def refresh_track_route(self, track_index: int) -> bool:
        """Refresh the route for a track (invalidate old and setup new)"""
        self.invalidate_track_route(track_index)
        return self.setup_track_route(track_index)
    
    def _route_note_off(self, route: AudioRoute, note: MidiNote) -> bool:
        """Route a note-off event through the appropriate audio backend"""
        if route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Route through MIDI routing manager if available
            if self.midi_routing_manager:
                self.midi_routing_manager.stop_note(route.channel, note.pitch)
                return True
            # Fallback to direct audio manager
            elif self.audio_manager:
                return self.audio_manager.stop_note_immediate(note.pitch, route.channel)
        
        elif route.audio_source.source_type == AudioSourceType.EXTERNAL_MIDI:
            # Route through per-track router for external MIDI
            if self.per_track_router:
                instance = self.per_track_router.track_instances.get(route.track_index)
                if instance and hasattr(self.per_track_router, '_stop_external_note'):
                    return self.per_track_router._stop_external_note(instance, note)
                else:
                    # Generic per-track routing
                    return self.per_track_router.stop_note(route.track_index, note)
        
        elif route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Route through per-track router for soundfonts  
            if self.per_track_router:
                instance = self.per_track_router.track_instances.get(route.track_index)
                if instance and hasattr(self.per_track_router, '_stop_soundfont_note'):
                    return self.per_track_router._stop_soundfont_note(instance, note)
                else:
                    # Generic per-track routing
                    return self.per_track_router.stop_note(route.track_index, note)
        
        return False
    
    def send_control_change(self, track_index: int, controller: int, value: int) -> bool:
        """Send a MIDI Control Change message for a specific track"""
        route = self.track_routes.get(track_index)
        if not route:
            # If no route exists for the track, try to setup one
            self.setup_track_route(track_index)
            route = self.track_routes.get(track_index)
            if not route:
                return False
        
        # Route the control change through appropriate backend
        if route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Route through MIDI routing manager if available
            if self.midi_routing_manager:
                try:
                    # Use MIDI routing manager's control change method
                    if hasattr(self.midi_routing_manager, 'send_control_change'):
                        self.midi_routing_manager.send_control_change(route.channel, controller, value)
                        return True
                    # Fallback to manual MIDI message construction
                    elif hasattr(self.midi_routing_manager, 'send_midi_message'):
                        midi_bytes = [0xB0 + route.channel, controller, value]  # Control Change
                        self.midi_routing_manager.send_midi_message(midi_bytes)
                        return True
                except Exception as e:
                    print(f"Error sending control change via MIDI routing: {e}")
            
            # Fallback to direct audio manager
            elif self.audio_manager and hasattr(self.audio_manager, 'send_control_change'):
                try:
                    self.audio_manager.send_control_change(route.channel, controller, value)
                    return True
                except Exception as e:
                    print(f"Error sending control change via audio manager: {e}")
        
        elif route.audio_source.source_type == AudioSourceType.EXTERNAL_MIDI:
            # Route through per-track router for external MIDI
            if self.per_track_router and hasattr(self.per_track_router, 'send_control_change'):
                try:  
                    return self.per_track_router.send_control_change(route.track_index, controller, value)
                except Exception as e:
                    print(f"Error sending control change via per-track router: {e}")
        
        elif route.audio_source.source_type == AudioSourceType.SOUNDFONT:
            # Route through per-track router for soundfonts
            if self.per_track_router and hasattr(self.per_track_router, 'send_control_change'):
                try:
                    return self.per_track_router.send_control_change(route.track_index, controller, value)
                except Exception as e:
                    print(f"Error sending control change via per-track router: {e}")
        
        return False
    
    def get_track_info(self, track_index: int) -> Optional[Dict]:
        """Get routing information for a track"""
        route = self.track_routes.get(track_index)
        if not route:
            return None
        
        return {
            "track_index": route.track_index,
            "audio_source": route.audio_source.name,
            "channel": route.channel,
            "program": route.program,
            "is_active": route.is_active,
            "last_used": route.last_used,
            "active_notes": list(self.channel_states[route.channel].active_notes)
        }
    
    def get_system_status(self) -> Dict:
        """Get overall system status"""
        return {
            "state": self.state.value,
            "total_routes": len(self.track_routes),
            "active_channels": len([c for c in self.channel_states.values() if c.assigned_track is not None]),
            "total_active_notes": sum(len(c.active_notes) for c in self.channel_states.values()),
            "managers_available": {
                "audio_manager": self.audio_manager is not None,
                "audio_source_manager": self.audio_source_manager is not None,
                "midi_routing_manager": self.midi_routing_manager is not None,
                "per_track_router": self.per_track_router is not None
            }
        }


# Global instance
_audio_routing_coordinator: Optional[AudioRoutingCoordinator] = None


def initialize_audio_routing_coordinator() -> AudioRoutingCoordinator:
    """Initialize and return the global audio routing coordinator"""
    global _audio_routing_coordinator
    
    if _audio_routing_coordinator is None:
        _audio_routing_coordinator = AudioRoutingCoordinator()
    
    if _audio_routing_coordinator.state == AudioRoutingState.UNINITIALIZED:
        _audio_routing_coordinator.initialize()
    
    return _audio_routing_coordinator


def get_audio_routing_coordinator() -> Optional[AudioRoutingCoordinator]:
    """Get the global audio routing coordinator instance"""
    return _audio_routing_coordinator


def cleanup_audio_routing_coordinator():
    """Clean up the global audio routing coordinator"""
    global _audio_routing_coordinator
    if _audio_routing_coordinator:
        print("AudioRoutingCoordinator: Cleaning up")
        _audio_routing_coordinator = None