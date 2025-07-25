# DominoPy - 技術仕様書

## 1. システム概要

### 1.1 アーキテクチャ概要
DominoPyは、Model-View-Controller（MVC）パターンを基盤とした、モジュラー設計のMIDIシーケンサーです。

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Main Window │ Piano Roll │ Piano Keyboard │ Track Panel    │
├─────────────────────────────────────────────────────────────┤
│                      Business Logic Layer                    │
├─────────────────────────────────────────────────────────────┤
│  Project Manager │ Audio Engine │ MIDI Engine │ Plugin Mgr  │
├─────────────────────────────────────────────────────────────┤
│                      Data Access Layer                       │
├─────────────────────────────────────────────────────────────┤
│  MIDI Parser │ File Manager │ Config Manager │ Data Models  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技術スタック

#### 1.2.1 コア技術
- **Python**: 3.8+ (型ヒント、dataclasses活用)
- **GUI Framework**: PySide6 (Qt6)
- **MIDI Processing**: mido 1.3.3
- **MIDI I/O**: python-rtmidi 1.5.8

#### 1.2.2 開発・テスト
- **Packaging**: packaging 25.0
- **Testing**: pytest
- **Code Quality**: black, flake8, mypy
- **Documentation**: Sphinx

## 2. データモデル

### 2.1 現在のデータモデル

#### 2.1.1 MidiNote クラス
```python
class MidiNote:
    def __init__(self, pitch: int, start_tick: int, end_tick: int, velocity: int, channel: int = 0):
        self.pitch = pitch        # MIDI note number (0-127)
        self.start_tick = start_tick # Start time in MIDI ticks
        self.end_tick = end_tick     # End time in MIDI ticks
        self.velocity = velocity     # Velocity (0-127)
        self.channel = channel       # MIDI channel (0-15)
    
    @property
    def duration(self) -> int:
        return self.end_tick - self.start_tick
```

#### 2.1.2 MidiTrack クラス
```python
class MidiTrack:
    def __init__(self, name: str = "New Track", channel: int = 0, program: int = 0):
        self.name = name
        self.channel = channel
        self.program = program        # MIDI program number (instrument)
        self.notes: List[MidiNote] = []
        # Add other MIDI events later (e.g., CC, Pitch Bend)
```

#### 2.1.3 MidiProject クラス
```python
class MidiProject:
    def __init__(self):
        self.tracks: List[MidiTrack] = []
        self.tempo_map: List[Dict[str, int]] = []      # [{'tick': 0, 'tempo': 500000}]
        self.time_signature_map: List[Dict[str, int]] = [] # [{'tick': 0, 'numerator': 4, 'denominator': 4}]
        self.ticks_per_beat: int = 480
```

### 2.2 拡張予定のデータモデル

#### 2.2.1 MidiEvent クラス（追加予定）
```python
@dataclass
class MidiEvent:
    tick: int
    event_type: str
    data: Dict[str, Any]
    
class ControlChangeEvent(MidiEvent):
    def __init__(self, tick: int, channel: int, control: int, value: int):
        super().__init__(tick, "control_change", {
            "channel": channel,
            "control": control,
            "value": value
        })
```

#### 2.2.2 ProjectSettings クラス（追加予定）
```python
@dataclass
class ProjectSettings:
    quantize_value: int = 480 // 4  # 16th note
    swing_percentage: int = 0
    default_velocity: int = 100
    default_note_length: int = 480
    scale_key: str = "C"
    scale_mode: str = "major"
```

## 3. ユーザーインターフェース仕様

### 3.1 現在のUI構成

#### 3.1.1 メインウィンドウ (main_window.py)
```python
class DominoPyMainWindow(QMainWindow):
    def __init__(self):
        # Layout: HBoxLayout
        # Components: PianoKeyboardWidget + PianoRollWidget
        # Menu: File menu with Open action
```

#### 3.1.2 ピアノロールウィジェット (piano_roll_widget.py)
```python
class PianoRollWidget(QWidget):
    # Current features:
    # - Note display and editing
    # - Mouse-based note creation/deletion/moving/resizing
    # - Grid display (pitch lines, beat lines)
    # - Quantization support
    # - Selection system
    
    # Key methods:
    # - paintEvent(): Renders the piano roll
    # - mousePressEvent(): Handles note creation/selection
    # - mouseMoveEvent(): Handles note dragging/resizing
    # - _tick_to_x(), _pitch_to_y(): Coordinate conversion
```

#### 3.1.3 ピアノキーボードウィジェット (piano_keyboard_widget.py)
```python
class PianoKeyboardWidget(QWidget):
    # Current features:
    # - Visual piano keyboard (white/black keys)
    # - Octave labels (C0, C1, C2, ...)
    # - Fixed width design
    
    # Key methods:
    # - paintEvent(): Renders the keyboard
```

### 3.2 UI 拡張計画

#### 3.2.1 トラックパネル（追加予定）
```python
class TrackPanel(QWidget):
    def __init__(self):
        # Track list with:
        # - Track name editing
        # - Mute/Solo buttons
        # - Volume/Pan controls
        # - Instrument selection
        # - Add/Remove track buttons
```

#### 3.2.2 トランスポートコントロール（追加予定）
```python
class TransportControls(QWidget):
    def __init__(self):
        # Transport controls:
        # - Play/Pause/Stop buttons
        # - Record button
        # - Position display
        # - Tempo control
        # - Time signature display
```

#### 3.2.3 メニューバー・ツールバー拡張
```python
# Additional menus:
# - Edit menu (Undo/Redo, Copy/Paste, Select All)
# - View menu (Zoom, Grid settings)
# - Transport menu (Play/Record controls)
# - Tools menu (Quantize, Transpose)
# - Help menu (About, Documentation)
```

## 4. MIDI処理仕様

### 4.1 現在のMIDI処理 (midi_parser.py)

#### 4.1.1 MIDIファイル読み込み
```python
def load_midi_file(file_path: str) -> MidiProject:
    # Features:
    # - Standard MIDI file (.mid, .midi) support
    # - Tempo map extraction
    # - Time signature map extraction
    # - Note event parsing (note_on/note_off)
    # - Multi-track support
    
    # Process:
    # 1. Load MIDI file using mido
    # 2. Extract tempo/time signature from track 0
    # 3. Parse note events from all tracks
    # 4. Create MidiProject with parsed data
```

#### 4.1.2 課題と制限
- 現在は note_on/note_off イベントのみ対応
- Control Change, Pitch Bend, Program Change 未対応
- MIDI ファイル保存機能未実装

### 4.2 MIDI処理拡張計画

#### 4.2.1 MIDIファイル保存
```python
def save_midi_file(project: MidiProject, file_path: str):
    # Features:
    # - Standard MIDI file export
    # - Tempo map preservation
    # - Time signature preservation
    # - All MIDI events support
    # - Multi-track export
```

#### 4.2.2 リアルタイムMIDI I/O
```python
class MidiInputManager:
    def __init__(self):
        self.input_port = None
        self.recording = False
        
    def start_recording(self):
        # Real-time MIDI input recording
        pass
        
    def stop_recording(self):
        # Stop recording and quantize notes
        pass

class MidiOutputManager:
    def __init__(self):
        self.output_port = None
        self.playing = False
        
    def play_project(self, project: MidiProject):
        # Real-time MIDI playback
        pass
```

## 5. ファイル形式仕様

### 5.1 対応ファイル形式

#### 5.1.1 現在対応
- **MIDI Files**: .mid, .midi (読み込みのみ)

#### 5.1.2 対応予定
- **MIDI Files**: .mid, .midi (読み込み・保存)
- **Project Files**: .pydmn (独自形式)
- **Configuration**: .json (設定ファイル)

### 5.2 プロジェクトファイル形式 (.pydmn)

#### 5.2.1 JSON構造
```json
{
    "version": "1.0",
    "project_info": {
        "name": "Project Name",
        "created_date": "2025-01-01T00:00:00Z",
        "modified_date": "2025-01-01T00:00:00Z"
    },
    "settings": {
        "ticks_per_beat": 480,
        "quantize_value": 120,
        "swing_percentage": 0,
        "default_velocity": 100
    },
    "tempo_map": [
        {"tick": 0, "tempo": 500000}
    ],
    "time_signature_map": [
        {"tick": 0, "numerator": 4, "denominator": 4}
    ],
    "tracks": [
        {
            "name": "Track 1",
            "channel": 0,
            "program": 0,
            "muted": false,
            "solo": false,
            "volume": 100,
            "pan": 64,
            "notes": [
                {
                    "pitch": 60,
                    "start_tick": 0,
                    "end_tick": 480,
                    "velocity": 100,
                    "channel": 0
                }
            ],
            "events": [
                {
                    "tick": 0,
                    "type": "control_change",
                    "channel": 0,
                    "control": 7,
                    "value": 100
                }
            ]
        }
    ]
}
```

## 6. 性能要件

### 6.1 レスポンス時間
- **UI応答性**: < 16ms (60 FPS)
- **ファイル読み込み**: < 5秒 (一般的なMIDIファイル)
- **再生レイテンシ**: < 10ms
- **音符作成**: < 100ms

### 6.2 メモリ使用量
- **基本動作**: < 100MB
- **大型プロジェクト**: < 500MB (10,000+ 音符)
- **メモリリーク**: 長時間使用でもメモリ増加なし

### 6.3 描画性能
- **大量音符**: 10,000+ 音符で 60 FPS 維持
- **スムーズスクロール**: 遅延なし
- **ズーム操作**: リアルタイム応答

## 7. セキュリティ・品質

### 7.1 エラーハンドリング
```python
# File operations
try:
    project = load_midi_file(file_path)
except FileNotFoundError:
    show_error_dialog("File not found")
except MidiFileError:
    show_error_dialog("Invalid MIDI file")
except Exception as e:
    log_error(f"Unexpected error: {e}")
    show_error_dialog("An unexpected error occurred")
```

### 7.2 データ整合性
- **MIDI値の範囲チェック**: 0-127 の範囲内
- **時間値の検証**: 負の値や不正な順序の検出
- **自動修復**: 可能な範囲でのデータ修正

### 7.3 自動保存
```python
class AutoSaveManager:
    def __init__(self, interval: int = 300):  # 5 minutes
        self.interval = interval
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_save)
        
    def auto_save(self):
        # Auto-save current project
        pass
```

## 8. 拡張性

### 8.1 プラグインシステム
```python
class BasePlugin:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        
    def initialize(self):
        pass
        
    def process_notes(self, notes: List[MidiNote]) -> List[MidiNote]:
        pass
        
    def create_ui(self) -> QWidget:
        pass

class PluginManager:
    def __init__(self):
        self.plugins: List[BasePlugin] = []
        
    def load_plugin(self, plugin_path: str):
        # Dynamic plugin loading
        pass
```

### 8.2 カスタムツール
```python
class ToolManager:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        
    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool
        
    def get_tool(self, name: str) -> Tool:
        return self.tools.get(name)
```

## 9. 配布・デプロイ

### 9.1 パッケージング
```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="pydominodev",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.9.1",
        "mido>=1.3.3",
        "python-rtmidi>=1.5.8",
        "packaging>=25.0"
    ],
    entry_points={
        "console_scripts": [
            "pydomino=src.main:main"
        ]
    }
)
```

### 9.2 配布形式
- **PyPI**: ソースディストリビューション
- **Binary**: PyInstaller による実行可能ファイル
- **Platform Specific**: Windows MSI, macOS DMG, Linux AppImage

## 10. テスト戦略

### 10.1 ユニットテスト
```python
# tests/test_midi_data_model.py
import pytest
from src.midi_data_model import MidiNote, MidiTrack, MidiProject

class TestMidiNote:
    def test_note_creation(self):
        note = MidiNote(60, 0, 480, 100)
        assert note.pitch == 60
        assert note.duration == 480
        
    def test_note_validation(self):
        with pytest.raises(ValueError):
            MidiNote(128, 0, 480, 100)  # Invalid pitch
```

### 10.2 統合テスト
```python
# tests/test_midi_integration.py
class TestMidiIntegration:
    def test_file_roundtrip(self):
        # Load -> Save -> Load -> Compare
        pass
        
    def test_ui_interaction(self):
        # UI操作のテスト
        pass
```

### 10.3 パフォーマンステスト
```python
# tests/test_performance.py
import time

class TestPerformance:
    def test_large_project_load(self):
        start = time.time()
        # Load project with 10,000+ notes
        end = time.time()
        assert (end - start) < 5.0  # Under 5 seconds
```

## 11. 今後の技術課題

### 11.1 短期的課題
1. **MIDIファイル保存機能**: 現在読み込みのみ
2. **複数選択機能**: 矩形選択、Ctrl+クリック
3. **Undo/Redo システム**: コマンドパターン実装
4. **キーボードショートカット**: 効率的な操作

### 11.2 中期的課題
1. **リアルタイム再生**: 音声出力との同期
2. **MIDI録音**: 外部機器からの入力
3. **オートメーション**: CC、ピッチベンド編集
4. **プラグインシステム**: 拡張可能な設計

### 11.3 長期的課題
1. **VST プラグイン対応**: 外部音源・エフェクト
2. **オーディオ録音**: MIDI + Audio のハイブリッド
3. **ネットワーク機能**: 協調編集、クラウド同期
4. **AI 機能**: 作曲支援、自動和音付け