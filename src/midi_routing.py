"""
MIDI Routing System for DominoPy
Manages external MIDI connections and virtual MIDI routing
"""
import threading
import time
from typing import List, Optional, Dict, Callable, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal

try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False
    print("Warning: python-rtmidi not available. MIDI routing will be disabled.")

class MIDIOutputType(Enum):
    """Types of MIDI output destinations"""
    INTERNAL_FLUIDSYNTH = "internal_fluidsynth"
    EXTERNAL_DEVICE = "external_device"
    VIRTUAL_PORT = "virtual_port"

@dataclass
class MIDIOutputDevice:
    """Represents a MIDI output device/port"""
    id: str
    name: str
    port_index: int
    output_type: MIDIOutputType
    is_available: bool = True
    description: str = ""

@dataclass
class MIDIRoutingSettings:
    """MIDI routing configuration"""
    primary_output: Optional[str] = None  # Device ID
    secondary_outputs: List[str] = None  # List of additional device IDs
    enable_internal_audio: bool = True
    enable_external_routing: bool = False
    midi_channel: int = 0  # Default MIDI channel
    
    def __post_init__(self):
        if self.secondary_outputs is None:
            self.secondary_outputs = []

class MIDIRoutingManager(QObject):
    """Manages MIDI routing and device connections"""
    
    # Signals
    devices_updated = Signal(list)  # List of available devices updated
    routing_changed = Signal()      # Routing configuration changed
    connection_error = Signal(str)  # MIDI connection error
    connection_status = Signal(str, bool)  # Device ID, connected status
    
    def __init__(self):
        super().__init__()
        
        self.available_devices: Dict[str, MIDIOutputDevice] = {}
        self.active_connections: Dict[str, Any] = {}  # Device ID -> MIDI output instance
        self.settings = MIDIRoutingSettings()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Always include internal FluidSynth as an option
        self._add_internal_device()
        
        if RTMIDI_AVAILABLE:
            self._scan_midi_devices()
        else:
            print("MIDI routing disabled - rtmidi not available")
    
    def _add_internal_device(self):
        """Add internal FluidSynth as a MIDI output option"""
        internal_device = MIDIOutputDevice(
            id="internal_fluidsynth",
            name="Internal FluidSynth (Built-in)",
            port_index=-1,
            output_type=MIDIOutputType.INTERNAL_FLUIDSYNTH,
            description="DominoPy built-in FluidSynth audio engine"
        )
        self.available_devices[internal_device.id] = internal_device
    
    def _scan_midi_devices(self):
        """Scan for available MIDI output devices"""
        if not RTMIDI_AVAILABLE:
            return
        
        try:
            midiout = rtmidi.MidiOut()
            ports = midiout.get_ports()
            
            with self._lock:
                # Clear existing external devices
                self.available_devices = {k: v for k, v in self.available_devices.items() 
                                        if v.output_type == MIDIOutputType.INTERNAL_FLUIDSYNTH}
                
                # Add detected MIDI ports
                for i, port_name in enumerate(ports):
                    # Clean up port name (handle encoding issues)
                    clean_name = self._clean_port_name(port_name)
                    
                    device_id = f"midi_out_{i}"
                    device = MIDIOutputDevice(
                        id=device_id,
                        name=clean_name,
                        port_index=i,
                        output_type=MIDIOutputType.EXTERNAL_DEVICE,
                        description=f"External MIDI device (Port {i})"
                    )
                    
                    self.available_devices[device_id] = device
            
            midiout.close_port()
            self.devices_updated.emit(list(self.available_devices.values()))
            print(f"MIDI scan complete: {len(ports)} external devices found")
            
        except Exception as e:
            self.connection_error.emit(f"Error scanning MIDI devices: {str(e)}")
    
    def _clean_port_name(self, port_name: str) -> str:
        """Clean up MIDI port names with encoding issues"""
        try:
            # Try to decode if it's bytes
            if isinstance(port_name, bytes):
                return port_name.decode('utf-8', errors='replace')
            
            # Handle common encoding issues on macOS
            if "„É" in port_name:  # Common macOS encoding issue
                # Try to extract meaningful parts
                if "IAC" in port_name:
                    # Extract IAC driver info
                    parts = port_name.split()
                    for part in parts:
                        if part.startswith('IAC') or part.isdigit():
                            continue
                        if 'Dualshock' in part or 'MIDI' in part:
                            return f"IAC Driver - {part}"
                    return "IAC Driver (Virtual MIDI)"
                else:
                    return "MIDI Device (Unknown)"
            
            return port_name
            
        except Exception:
            return "MIDI Device (Name unavailable)"
    
    def get_available_devices(self) -> List[MIDIOutputDevice]:
        """Get list of all available MIDI output devices"""
        with self._lock:
            return list(self.available_devices.values())
    
    def set_primary_output(self, device_id: str) -> bool:
        """Set the primary MIDI output device"""
        if device_id not in self.available_devices:
            self.connection_error.emit(f"Device not found: {device_id}")
            return False
        
        # Disconnect previous primary if different
        if self.settings.primary_output and self.settings.primary_output != device_id:
            self.disconnect_device(self.settings.primary_output)
        
        self.settings.primary_output = device_id
        
        # Connect to new primary device
        if self._connect_device(device_id):
            self.routing_changed.emit()
            return True
        
        return False
    
    def add_secondary_output(self, device_id: str) -> bool:
        """Add a secondary MIDI output device"""
        if device_id not in self.available_devices:
            self.connection_error.emit(f"Device not found: {device_id}")
            return False
        
        if device_id not in self.settings.secondary_outputs:
            if self._connect_device(device_id):
                self.settings.secondary_outputs.append(device_id)
                self.routing_changed.emit()
                return True
        
        return False
    
    def remove_secondary_output(self, device_id: str) -> bool:
        """Remove a secondary MIDI output device"""
        if device_id in self.settings.secondary_outputs:
            self.disconnect_device(device_id)
            self.settings.secondary_outputs.remove(device_id)
            self.routing_changed.emit()
            return True
        
        return False
    
    def _connect_device(self, device_id: str) -> bool:
        """Connect to a MIDI device"""
        if device_id in self.active_connections:
            return True  # Already connected
        
        device = self.available_devices.get(device_id)
        if not device:
            return False
        
        try:
            if device.output_type == MIDIOutputType.INTERNAL_FLUIDSYNTH:
                # Internal FluidSynth doesn't need a connection object
                self.active_connections[device_id] = "internal"
                self.connection_status.emit(device_id, True)
                return True
            
            elif device.output_type == MIDIOutputType.EXTERNAL_DEVICE:
                if not RTMIDI_AVAILABLE:
                    return False
                
                midiout = rtmidi.MidiOut()
                midiout.open_port(device.port_index, f"DominoPy -> {device.name}")
                self.active_connections[device_id] = midiout
                self.connection_status.emit(device_id, True)
                print(f"Connected to MIDI device: {device.name}")
                return True
        
        except Exception as e:
            self.connection_error.emit(f"Failed to connect to {device.name}: {str(e)}")
            return False
        
        return False
    
    def disconnect_device(self, device_id: str):
        """Disconnect from a MIDI device"""
        if device_id in self.active_connections:
            connection = self.active_connections[device_id]
            
            if connection != "internal" and hasattr(connection, 'close_port'):
                try:
                    connection.close_port()
                except Exception as e:
                    print(f"Error closing MIDI connection: {e}")
            
            del self.active_connections[device_id]
            self.connection_status.emit(device_id, False)
    
    def send_midi_message(self, message: List[int], device_id: Optional[str] = None):
        """Send a MIDI message to specified device or all active devices"""
        if device_id:
            # Send to specific device
            self._send_to_device(device_id, message)
        else:
            # Send to primary device
            if self.settings.primary_output:
                self._send_to_device(self.settings.primary_output, message)
            
            # Send to secondary devices
            for secondary_id in self.settings.secondary_outputs:
                self._send_to_device(secondary_id, message)
    
    def _send_to_device(self, device_id: str, message: List[int]):
        """Send MIDI message to a specific device"""
        device = self.available_devices.get(device_id)
        if not device:
            return
        
        connection = self.active_connections.get(device_id)
        if not connection:
            return
        
        try:
            if device.output_type == MIDIOutputType.INTERNAL_FLUIDSYNTH:
                # Only route to internal FluidSynth if internal audio is enabled
                if self.settings.enable_internal_audio:
                    self._route_to_internal_audio(message)
            
            elif device.output_type == MIDIOutputType.EXTERNAL_DEVICE and connection != "internal":
                # Only send to external MIDI device if external routing is enabled
                if self.settings.enable_external_routing:
                    connection.send_message(message)
        
        except Exception as e:
            self.connection_error.emit(f"Error sending MIDI to {device.name}: {str(e)}")
    
    def _route_to_internal_audio(self, message: List[int]):
        """Route MIDI message to internal FluidSynth audio system"""
        from src.audio_system import get_audio_manager
        
        audio_manager = get_audio_manager()
        if not audio_manager:
            return
        
        # Parse MIDI message
        if len(message) >= 3:
            status = message[0]
            channel = status & 0x0F
            command = status & 0xF0
            
            if command == 0x90 and message[2] > 0:  # Note On
                channel = status & 0x0F  # Extract channel from status byte
                pitch = message[1]
                velocity = message[2]
                audio_manager.play_note_immediate(pitch, velocity, channel)
            
            elif command == 0x80 or (command == 0x90 and message[2] == 0):  # Note Off
                channel = status & 0x0F  # Extract channel from status byte
                pitch = message[1]
                audio_manager.stop_note_immediate(pitch, channel)
    
    def play_note(self, channel: int, pitch: int, velocity: int):
        """Play a note through the routing system"""
        # Create MIDI Note On message
        note_on = [0x90 | (channel & 0x0F), pitch & 0x7F, velocity & 0x7F]
        self.send_midi_message(note_on)
    
    def stop_note(self, channel: int, pitch: int):
        """Stop a note through the routing system"""
        # Create MIDI Note Off message
        note_off = [0x80 | (channel & 0x0F), pitch & 0x7F, 0x40]
        self.send_midi_message(note_off)
    
    def refresh_devices(self):
        """Refresh the list of available MIDI devices"""
        self._scan_midi_devices()
    
    def disconnect_all(self):
        """Disconnect from all MIDI devices"""
        for device_id in list(self.active_connections.keys()):
            self.disconnect_device(device_id)
    
    def get_routing_info(self) -> Dict[str, Any]:
        """Get current routing configuration info"""
        return {
            'primary_output': self.settings.primary_output,
            'secondary_outputs': self.settings.secondary_outputs.copy(),
            'active_connections': list(self.active_connections.keys()),
            'available_devices': len(self.available_devices),
            'internal_audio_enabled': self.settings.enable_internal_audio,
            'external_routing_enabled': self.settings.enable_external_routing
        }

# Global instance
_midi_routing_manager = None

def get_midi_routing_manager() -> Optional[MIDIRoutingManager]:
    """Get the global MIDI routing manager instance"""
    return _midi_routing_manager

def initialize_midi_routing() -> bool:
    """Initialize the global MIDI routing manager"""
    global _midi_routing_manager
    
    try:
        _midi_routing_manager = MIDIRoutingManager()
        print("MIDI routing system initialized")
        return True
    except Exception as e:
        print(f"Failed to initialize MIDI routing: {e}")
        return False

def cleanup_midi_routing():
    """Clean up the MIDI routing system"""
    global _midi_routing_manager
    
    if _midi_routing_manager:
        _midi_routing_manager.disconnect_all()
        _midi_routing_manager = None
        print("MIDI routing system cleaned up")