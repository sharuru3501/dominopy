"""
MIDI Input System for PyDomino
Receives MIDI from external sources (Strudel, DAWs, MIDI files)
"""
import json
import threading
import time
from typing import List, Optional, Dict, Callable, Any
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer

try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False
    print("Warning: python-rtmidi not available. MIDI input will be limited.")

@dataclass
class MIDIInputEvent:
    """MIDI入力イベント"""
    type: str  # 'noteOn', 'noteOff', 'cc', 'pitchBend'
    timestamp: float
    channel: int
    note: Optional[int] = None
    velocity: Optional[int] = None
    controller: Optional[int] = None
    value: Optional[int] = None
    raw_message: Optional[List[int]] = None

@dataclass
class MIDIInputDevice:
    """MIDI入力デバイス"""
    id: str
    name: str
    port_index: int
    is_available: bool = True
    description: str = ""

class MIDIInputSystem(QObject):
    """MIDI入力システム"""
    
    # Signals
    midi_event_received = Signal(object)  # MIDIInputEvent
    device_connected = Signal(str)        # Device ID
    device_disconnected = Signal(str)     # Device ID
    input_error = Signal(str)             # Error message
    
    def __init__(self):
        super().__init__()
        
        self.available_devices: Dict[str, MIDIInputDevice] = {}
        self.active_connections: Dict[str, Any] = {}
        self.event_callbacks: List[Callable[[MIDIInputEvent], None]] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Virtual MIDI input for file/JSON import
        self._add_virtual_devices()
        
        if RTMIDI_AVAILABLE:
            self._scan_input_devices()
        else:
            print("MIDI input limited - rtmidi not available")
    
    def _add_virtual_devices(self):
        """仮想MIDI入力デバイスを追加"""
        virtual_devices = [
            MIDIInputDevice(
                id="json_file_input",
                name="JSON File Input (Strudel/DAW export)",
                port_index=-1,
                description="Import MIDI events from JSON files"
            ),
            MIDIInputDevice(
                id="real_time_json",
                name="Real-time JSON Stream (Strudel bridge)",
                port_index=-2,
                description="Real-time MIDI from Strudel or other sources"
            ),
            MIDIInputDevice(
                id="websocket_input",
                name="WebSocket MIDI Input (Strudel Real-time)",
                port_index=-3,
                description="Real-time MIDI from Strudel via WebSocket"
            )
        ]
        
        for device in virtual_devices:
            self.available_devices[device.id] = device
    
    def _scan_input_devices(self):
        """利用可能なMIDI入力デバイスをスキャン"""
        if not RTMIDI_AVAILABLE:
            return
        
        try:
            midiin = rtmidi.MidiIn()
            ports = midiin.get_ports()
            
            with self._lock:
                # Clear existing hardware devices
                self.available_devices = {k: v for k, v in self.available_devices.items() 
                                        if v.port_index < 0}
                
                # Add detected MIDI input ports
                for i, port_name in enumerate(ports):
                    clean_name = self._clean_port_name(port_name)
                    
                    device_id = f"midi_in_{i}"
                    device = MIDIInputDevice(
                        id=device_id,
                        name=clean_name,
                        port_index=i,
                        description=f"Hardware MIDI input (Port {i})"
                    )
                    
                    self.available_devices[device_id] = device
            
            midiin.close_port()
            print(f"MIDI input scan complete: {len(ports)} hardware devices found")
            
        except Exception as e:
            self.input_error.emit(f"Error scanning MIDI input devices: {str(e)}")
    
    def _clean_port_name(self, port_name: str) -> str:
        """MIDI入力ポート名をクリーンアップ"""
        try:
            if isinstance(port_name, bytes):
                return port_name.decode('utf-8', errors='replace')
            
            # Handle encoding issues
            if "„É" in port_name:
                if "IAC" in port_name:
                    return "IAC Driver (Virtual MIDI Input)"
                return "MIDI Input Device (Unknown)"
            
            return port_name
            
        except Exception:
            return "MIDI Input Device (Name unavailable)"
    
    def get_available_devices(self) -> List[MIDIInputDevice]:
        """利用可能なMIDI入力デバイス一覧を取得"""
        with self._lock:
            return list(self.available_devices.values())
    
    def connect_device(self, device_id: str) -> bool:
        """MIDI入力デバイスに接続"""
        device = self.available_devices.get(device_id)
        if not device:
            self.input_error.emit(f"Device not found: {device_id}")
            return False
        
        if device_id in self.active_connections:
            return True  # Already connected
        
        try:
            if device.port_index >= 0 and RTMIDI_AVAILABLE:
                # Hardware MIDI device
                midiin = rtmidi.MidiIn()
                midiin.open_port(device.port_index, f"PyDomino <- {device.name}")
                midiin.set_callback(lambda msg, data: self._handle_midi_message(msg, device_id))
                
                self.active_connections[device_id] = midiin
                self.device_connected.emit(device_id)
                print(f"Connected to MIDI input: {device.name}")
                return True
            
            elif device.port_index < 0:
                # Virtual device (JSON, file-based, WebSocket)
                if device_id == "websocket_input":
                    # WebSocket MIDI input - connect to WebSocket server
                    success = self._connect_websocket_input()
                    if success:
                        self.active_connections[device_id] = "websocket"
                        self.device_connected.emit(device_id)
                        print(f"Connected to WebSocket MIDI input: {device.name}")
                        return True
                    else:
                        return False
                else:
                    # Other virtual devices
                    self.active_connections[device_id] = "virtual"
                    self.device_connected.emit(device_id)
                    print(f"Activated virtual input: {device.name}")
                    return True
        
        except Exception as e:
            self.input_error.emit(f"Failed to connect to {device.name}: {str(e)}")
            return False
        
        return False
    
    def _connect_websocket_input(self) -> bool:
        """WebSocket MIDI入力に接続（現在は無効化）"""
        self.input_error.emit("WebSocket MIDI input is currently disabled")
        return False
    
    def _handle_websocket_midi(self, websocket_msg):
        """WebSocketからのMIDIメッセージを処理"""
        try:
            # Convert to MIDIInputEvent
            event = MIDIInputEvent(
                type=websocket_msg.command,
                timestamp=websocket_msg.timestamp,
                channel=websocket_msg.channel,
                note=websocket_msg.note,
                velocity=websocket_msg.velocity,
                controller=websocket_msg.controller,
                value=websocket_msg.value,
                raw_message=websocket_msg.to_midi_bytes()
            )
            
            # Emit event
            self.midi_event_received.emit(event)
            
            # Call callbacks
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in WebSocket MIDI callback: {e}")
                    
        except Exception as e:
            self.input_error.emit(f"Error processing WebSocket MIDI: {str(e)}")
    
    def _handle_bridge_midi_event(self, midi_event):
        """リアルタイムブリッジからのMIDIイベントを処理"""
        try:
            # Convert to MIDIInputEvent
            event = MIDIInputEvent(
                type=midi_event.command,
                timestamp=midi_event.timestamp,
                channel=midi_event.channel,
                note=midi_event.note,
                velocity=midi_event.velocity,
                controller=midi_event.controller,
                value=midi_event.value,
                raw_message=midi_event.midi_bytes
            )
            
            # Emit event (avoid duplicate if already handled by WebSocket)
            # This is mainly for logging and UI updates
            # The actual audio processing is handled by the bridge itself
            
        except Exception as e:
            print(f"Error handling bridge MIDI event: {e}")

    def disconnect_device(self, device_id: str):
        """MIDI入力デバイスから切断"""
        if device_id in self.active_connections:
            connection = self.active_connections[device_id]
            
            if connection == "websocket":
                # Disconnect WebSocket input
                self._disconnect_websocket_input()
            elif connection != "virtual" and hasattr(connection, 'close_port'):
                try:
                    connection.close_port()
                except Exception as e:
                    print(f"Error closing MIDI input connection: {e}")
            
            del self.active_connections[device_id]
            self.device_disconnected.emit(device_id)
    
    def _disconnect_websocket_input(self):
        """WebSocket MIDI入力から切断（現在は無効化）"""
        print("WebSocket MIDI input disconnected (disabled)")
    
    def _handle_midi_message(self, message, device_id: str):
        """受信したMIDIメッセージを処理"""
        msg, deltatime = message
        if len(msg) < 3:
            return
        
        try:
            # Parse MIDI message
            status = msg[0]
            channel = status & 0x0F
            command = status & 0xF0
            
            # Create MIDI event
            event = MIDIInputEvent(
                type="unknown",
                timestamp=time.time(),
                channel=channel,
                raw_message=msg
            )
            
            if command == 0x90 and len(msg) >= 3:  # Note On
                event.type = "noteOn" if msg[2] > 0 else "noteOff"
                event.note = msg[1]
                event.velocity = msg[2]
            
            elif command == 0x80 and len(msg) >= 3:  # Note Off
                event.type = "noteOff"
                event.note = msg[1]
                event.velocity = msg[2]
            
            elif command == 0xB0 and len(msg) >= 3:  # Control Change
                event.type = "cc"
                event.controller = msg[1]
                event.value = msg[2]
            
            elif command == 0xE0 and len(msg) >= 3:  # Pitch Bend
                event.type = "pitchBend"
                event.value = (msg[2] << 7) | msg[1]
            
            # Emit event
            self.midi_event_received.emit(event)
            
            # Call registered callbacks
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in MIDI callback: {e}")
        
        except Exception as e:
            self.input_error.emit(f"Error processing MIDI message: {str(e)}")
    
    def import_json_file(self, file_path: str, play_realtime: bool = False) -> bool:
        """JSONファイルからMIDIイベントをインポート"""
        try:
            path = Path(file_path)
            if not path.exists():
                self.input_error.emit(f"File not found: {file_path}")
                return False
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            events = data.get('events', [])
            tempo = data.get('tempo', 120)
            ppq = data.get('ppq', 480)
            
            if play_realtime:
                # Real-time playback
                self._play_events_realtime(events, tempo, ppq)
            else:
                # Immediate import
                self._import_events_immediate(events)
            
            print(f"Imported {len(events)} MIDI events from {file_path}")
            return True
        
        except Exception as e:
            self.input_error.emit(f"Error importing JSON file: {str(e)}")
            return False
    
    def _import_events_immediate(self, events: List[Dict]):
        """MIDIイベントを即座にインポート（タイミング無視）"""
        for event_data in events:
            try:
                event = MIDIInputEvent(
                    type=event_data.get('type', 'unknown'),
                    timestamp=time.time(),
                    channel=event_data.get('channel', 0),
                    note=event_data.get('note'),
                    velocity=event_data.get('velocity'),
                    controller=event_data.get('controller'),
                    value=event_data.get('value')
                )
                
                self.midi_event_received.emit(event)
                
                # Call callbacks
                for callback in self.event_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Error in MIDI callback: {e}")
            
            except Exception as e:
                print(f"Error processing event: {e}")
    
    def _play_events_realtime(self, events: List[Dict], tempo: int, ppq: int):
        """MIDIイベントをリアルタイム再生"""
        def play_thread():
            try:
                sorted_events = sorted(events, key=lambda e: e.get('time', 0))
                start_time = time.time()
                
                for event_data in sorted_events:
                    # Calculate timing
                    event_time_ticks = event_data.get('time', 0)
                    event_time_seconds = (event_time_ticks / ppq) * (60.0 / tempo)
                    
                    # Wait until event time
                    current_time = time.time() - start_time
                    sleep_time = event_time_seconds - current_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
                    # Create and emit event
                    event = MIDIInputEvent(
                        type=event_data.get('type', 'unknown'),
                        timestamp=time.time(),
                        channel=event_data.get('channel', 0),
                        note=event_data.get('note'),
                        velocity=event_data.get('velocity'),
                        controller=event_data.get('controller'),
                        value=event_data.get('value')
                    )
                    
                    self.midi_event_received.emit(event)
                    
                    # Call callbacks
                    for callback in self.event_callbacks:
                        try:
                            callback(event)
                        except Exception as e:
                            print(f"Error in MIDI callback: {e}")
            
            except Exception as e:
                self.input_error.emit(f"Error during realtime playback: {str(e)}")
        
        # Start playback in separate thread
        thread = threading.Thread(target=play_thread, daemon=True)
        thread.start()
    
    def add_event_callback(self, callback: Callable[[MIDIInputEvent], None]):
        """MIDIイベント受信時のコールバックを追加"""
        self.event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[MIDIInputEvent], None]):
        """MIDIイベントコールバックを削除"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
    
    def send_to_audio_system(self, event: MIDIInputEvent):
        """MIDIイベントをPyDominoのオーディオシステムに送信"""
        try:
            from src.audio_system import get_audio_manager
            
            audio_manager = get_audio_manager()
            if not audio_manager:
                return
            
            if event.type == "noteOn" and event.note is not None:
                audio_manager.play_note_immediate(
                    event.note, 
                    event.velocity or 127, 
                    event.channel
                )
            
            elif event.type == "noteOff" and event.note is not None:
                audio_manager.stop_note_immediate(
                    event.note, 
                    event.channel
                )
        
        except Exception as e:
            print(f"Error sending MIDI to audio system: {e}")
    
    def refresh_devices(self):
        """利用可能なデバイスを再スキャン"""
        self._scan_input_devices()
    
    def disconnect_all(self):
        """すべてのデバイスから切断"""
        for device_id in list(self.active_connections.keys()):
            self.disconnect_device(device_id)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """接続状況情報を取得"""
        return {
            'active_connections': list(self.active_connections.keys()),
            'available_devices': len(self.available_devices),
            'callback_count': len(self.event_callbacks),
            'rtmidi_available': RTMIDI_AVAILABLE
        }

# Global instance
_midi_input_system = None

def get_midi_input_system() -> Optional[MIDIInputSystem]:
    """グローバルMIDI入力システムインスタンスを取得"""
    return _midi_input_system

def initialize_midi_input() -> bool:
    """グローバルMIDI入力システムを初期化"""
    global _midi_input_system
    
    try:
        _midi_input_system = MIDIInputSystem()
        
        # Auto-connect to audio system
        _midi_input_system.add_event_callback(_midi_input_system.send_to_audio_system)
        
        print("MIDI input system initialized")
        return True
    except Exception as e:
        print(f"Failed to initialize MIDI input: {e}")
        return False

def cleanup_midi_input():
    """MIDI入力システムをクリーンアップ"""
    global _midi_input_system
    
    if _midi_input_system:
        _midi_input_system.disconnect_all()
        _midi_input_system = None
        print("MIDI input system cleaned up")