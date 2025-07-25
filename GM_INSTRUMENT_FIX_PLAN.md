# GM Instrument音色変更問題 修正計画

## 🔍 問題の詳細

**症状**: Select GM Instrumentで音色を変更しても、常にGrand Piano（program=0）から音色が変わらない

**根本原因**: `src/audio_source_manager.py`の`assign_source_to_track()`メソッド（136-145行目）で、GM Instrumentダイアログで設定したプログラム番号が`get_track_program_for_soundfont()`によって**強制的にデフォルト値（0=ピアノ）に上書き**されている。

## 📊 デバッグ結果

```
5. GM Instrument変更をシミュレート: Flute (program=73)
Applied track 0 program 0 to soundfont GM: Flute  ← program=0に上書きされている！
📌 Assigned internal_fluidsynth_ch0 to track 0 (program: 0)
```

### 問題のコードフロー

1. **GM Instrumentダイアログ**: `program=73` (Flute) でAudioSourceを作成
2. **audio_source_manager.assign_source_to_track()**: `get_track_program_for_soundfont()`を呼び出し
3. **get_track_program_for_soundfont()**: トラック0に対してDEFAULT_TRACK_PROGRAMS[0]=0を返す
4. **結果**: `source.program = 0` に上書きされ、ピアノ音色になる

## 🎯 修正方法（採用: 方法A - GM専用ソースの保護）

### 修正箇所
- `src/audio_source_manager.py` の `assign_source_to_track()` メソッド

### 修正内容
GM Instrumentダイアログで作成される`internal_fluidsynth_ch*`ソースについては、プログラム番号の上書きをスキップし、既存のサウンドフォントファイルソースは従来通りデフォルトプログラムを適用。

### 修正前のコード
```python
# For soundfont sources, apply track-specific program
source = self.available_sources[source_id]
if source.source_type == AudioSourceType.SOUNDFONT:
    try:
        from src.track_manager import get_track_manager_for_soundfont
        source.program = get_track_program_for_soundfont(track_index, source.name)
        source.channel = track_index % 16
        print(f"Applied track {track_index} program {source.program} to soundfont {source.name}")
    except ImportError:
        pass
```

### 修正後のコード
```python
# For soundfont sources, apply track-specific program
source = self.available_sources[source_id]
if source.source_type == AudioSourceType.SOUNDFONT:
    # GM Instrumentダイアログで作成されたソースはプログラム保持
    if not source_id.startswith("internal_fluidsynth_ch"):
        try:
            from src.track_manager import get_track_program_for_soundfont
            source.program = get_track_program_for_soundfont(track_index, source.name)
            source.channel = track_index % 16
            print(f"Applied track {track_index} program {source.program} to soundfont {source.name}")
        except ImportError:
            pass
    else:
        # GM専用ソースはプログラム番号を保持
        source.channel = track_index % 16  # チャンネルのみ更新
        print(f"Preserved GM instrument program {source.program} for track {track_index}")
```

## 🧪 検証方法

### 1. 修正前の確認
- GM InstrumentダイアログでFlute（program=73）を選択
- 音色が変わらず、ピアノのまま

### 2. 修正後の期待動作
- GM InstrumentダイアログでFlute（program=73）を選択
- 実際にフルート音色で音が鳴る
- デバッグログで`Preserved GM instrument program 73 for track 0`が表示される

### 3. 回帰テスト
- 通常のサウンドフォントファイル（TimGM6mb）の音色はデフォルトプログラムのまま
- 他のトラックでのGM Instrument変更も正常動作

## 📝 実装手順

1. **コードを修正**: `src/audio_source_manager.py`
2. **デバッグスクリプト実行**: 修正効果を確認
3. **実際のアプリでテスト**: GM Instrumentダイアログの動作確認
4. **開発履歴更新**: 修正内容をドキュメント化
5. **コミット**: 修正をリポジトリに反映

## 🔄 その他の検討事項

### 副作用チェック
- 既存のサウンドフォントファイルの動作に影響がないか
- マルチトラックでのGM Instrument変更が正常か
- 音色変更後の保存・読み込みが正常か

### 将来的な改善
- GM Instrument選択がより直感的になるUIの検討
- プリセット楽器編成（ロック、ジャズ、オーケストラ等）の実装