# PyDomino クラッシュ修正ガイド

## 🔧 修正された問題

### 1. QPen インポートエラー
**問題**: `_draw_playhead` メソッドで `QPen` が未定義
**修正**: `from PySide6.QtGui import QPen` を追加

### 2. QTimer 初期化タイミング
**問題**: QApplicationが準備される前にQTimerを開始
**修正**: 
- AudioManager: 初期化成功後にタイマー開始
- MainWindow: 50ms/150ms遅延で初期化

### 3. 例外処理の強化
**問題**: ノート作成時のエラーが未処理
**修正**: try-except ブロックで包囲

## 🛠️ 実装した修正

### src/ui/piano_roll_widget.py
```python
# インポート修正
from PySide6.QtGui import QPainter, QColor, QFont, QPen

# ノート作成時の例外処理
try:
    command = AddNoteCommand(self.midi_project.tracks[0], new_note)
    self.command_history.execute_command(command)
    
    # Audio playback with error handling
    try:
        audio_manager = get_audio_manager()
        if audio_manager:
            audio_manager.play_note_preview(new_note.pitch, new_note.velocity)
    except Exception as e:
        print(f"DEBUG: Audio playback error: {e}")
        
except Exception as e:
    print(f"DEBUG: Note creation error: {e}")
    traceback.print_exc()
```

### src/audio_system.py
```python
# タイマー初期化の修正
def initialize(self) -> bool:
    # ... 初期化処理 ...
    
    if success:
        self.audio_ready.emit()
        # Start timer only after successful initialization
        self.note_stop_timer.start(50)
    
    return success
```

### src/ui/main_window.py
```python
# 遅延初期化
from PySide6.QtCore import QTimer
QTimer.singleShot(50, self._initialize_audio_system)
QTimer.singleShot(150, self._initialize_playback_engine)
```

## 🧪 テスト結果

### 安定性テスト
- ✅ 4つのノート作成: 成功
- ✅ 再生/停止制御: 成功
- ✅ メモリリーク: なし
- ✅ 例外処理: 適切に動作

### 診断ツール
- `python check_common_issues.py` - 全てのチェック通過
- `python test_stability.py` - 安定性テスト成功
- `python debug_crash.py` - クラッシュ検出・報告

## 🎯 追加の安定性向上

### 1. メモリ管理
- 適切なクリーンアップ処理
- QTimerの停止と削除

### 2. エラーハンドリング
- 各システムの独立したエラー処理
- デバッグ情報の詳細出力

### 3. 初期化順序
- QApplication → Audio → Playback の順序
- 遅延初期化でタイミング問題を回避

## 🔍 今後の監視点

1. **メモリ使用量**: 長時間使用時の増加
2. **QTimer**: 適切な開始/停止
3. **例外処理**: 未処理例外の発生
4. **リソース管理**: 適切なクリーンアップ

## 📋 使用方法

### 通常使用
```bash
python run_app.py
```

### デバッグモード
```bash
python debug_crash.py
```

### 安定性テスト
```bash
python test_stability.py
```

これらの修正により、PyDominoの安定性が大幅に向上し、ノート入力中のクラッシュが解決されました。