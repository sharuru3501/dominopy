# DominoPy 開発履歴

## 概要
DominoPyは、PySide6を使用したクロスプラットフォーム対応のMIDIピアノロールアプリケーションです。
このドキュメントは、開発過程で実装された機能や修正の詳細な履歴を記録します。

## 開発履歴

### 2025-07-24: プロジェクト名変更とリリース準備
**ブランディング戦略**: PyDomino から DominoPy への統一的な名前変更

#### 🎯 変更の背景
- **名前衝突の回避**: 既存のpydomino（ドミノ・ピザAPIラッパー）との差別化
- **ブランディング統一**: Python + Domino の組み合わせを明確化
- **親しみやすさ**: 「ドミノパイ」という響きによる親しみやすさ向上
- **検索性向上**: ユニークな名前による検索時の識別性向上

#### 📋 実施した変更内容

**1. インフラストラクチャ変更**
- **GitHubリポジトリ名**: `pydomino` → `dominopy`
- **PyInstallerファイル**: `PyDomino.spec` → `DominoPy.spec`
- **アプリケーションバンドル**: `PyDomino.app` → `DominoPy.app`
- **Bundle ID**: `app.pydomino.PyDomino` → `app.dominopy.DominoPy`

**2. ユーザーインターフェース更新**
- **ウィンドウタイトル**: 全て「DominoPy」に統一
- **アプリケーション名**: macOSメニューバーでの表示名変更
- **クラス名**: `PyDominoMainWindow` → `DominoPyMainWindow`
- **ステータスバー**: `PyDominoStatusBar` → `DominoPyStatusBar`

**3. システムレベル変更**
- **Application Support パス**: `~/Library/Application Support/PyDomino/` → `~/Library/Application Support/DominoPy/`
- **MIDI仮想ポート名**: "PyDomino Output" → "DominoPy Output"
- **ドメイン設定**: `pydomino.app` → `dominopy.app`

**4. コードベース全体更新**
- **コメント・docstring**: 全てのPython ファイル内の参照を更新
- **テストファイル**: 全てのテストコード内の参照を更新
- **ビルドスクリプト**: 全ての実行スクリプトの参照を更新

**5. ドキュメンテーション更新**
- **README.md**: プロジェクト説明とセットアップ手順を更新
- **LICENSE**: 著作権者名を「DominoPy Contributors」に変更
- **BUILD_INSTRUCTIONS.md**: ビルド手順を新しい名前に更新
- **docs/**: 全てのMarkdownファイルの参照を更新
- **soundfonts/README.md**: セットアップガイドを更新

#### 🚀 リリース成果
- **GitHub Release**: DominoPy v1.0.0-macOS を正式リリース

### 2025-07-25: 包括的なAudio Source管理システムの実装
**UX改善**: サウンドフォント管理の完全刷新とユーザビリティ向上

#### 🎯 実装の背景
- **UX問題の解決**: サウンドフォント追加・管理の複雑さの改善
- **機能発見性**: ユーザーがオーディオ機能を見つけやすくする
- **統一性**: Add/Remove操作の対称性とUI一貫性の確保
- **簡素化**: 不要な「No Audio Source」オプションの削除

#### 📋 実装した機能

**1. トラック右クリックメニュー強化** (`src/ui/track_list_widget.py`)
- **Audio Source...**: トラック別にサウンドフォント選択・管理
- **既存メニュー拡張**: Rename, Color, Duplicate等と統合
- **コンテキスト適応**: トラック固有の設定にアクセス

**2. Audio Source管理ダイアログ改善** (`src/ui/audio_source_dialog.py`)
- **🎵 Add Soundfont...**: ファイルダイアログでサウンドフォント追加
- **🗑️ Remove Soundfont**: ボタンとコンテキストメニューの両方で削除
- **スマート削除ボタン**: サウンドフォント選択時のみ有効化
- **ファイル検証**: サイズチェック、形式検証、確認ダイアログ
- **右クリック削除**: サウンドフォントリストでの直接削除

**3. Audioメニュー拡張** (`src/ui/main_window.py`)
- **🎵 Audio Sources...**: アクティブトラックのソース管理
- **➕ Add Soundfont...**: 直接サウンドフォント追加
- **統合配置**: 既存のMIDI Routing, Virtual Keyboardと統合

**4. Audio Source Manager機能強化** (`src/audio_source_manager.py`)
- **add_soundfont_file()**: ファイルコピー、登録、検証の自動化
- **remove_soundfont_file()**: 安全な削除とトラック割り当て解除
- **シグナル連携**: UI更新の自動化
- **エラーハンドリング**: 堅牢な例外処理

**5. UIデザイン最適化**
- **対称的ボタン配置**: Add/Removeボタンのペア配置
- **3セクション構成**: Refresh | Add/Remove | Cancel/Select
- **状況適応UI**: 選択状態に応じたボタン有効化
- **ツールチップ**: 選択中のサウンドフォント名表示

**6. \"No Audio Source\"完全削除**
- **AudioSourceType.NONE削除**: enumから完全除去
- **UI簡素化**: 不要なラジオボタン削除
- **デフォルト変更**: 「Soundfont Files」がデフォルト選択
- **表示統一**: 音源なし状態は「No Audio」で統一表示

#### 🛠️ 技術的改善

**アーキテクチャ**
- **信号駆動更新**: sources_updated.emit()による自動UI更新
- **分離した責任**: Manager(データ) ↔ Dialog(UI) ↔ Menu(アクセス)
- **エラー耐性**: 不正ファイル、大容量ファイルの適切な処理

**ファイル操作**
- **安全なコピー**: shutil.copy2()による属性保持コピー
- **自動ディレクトリ作成**: os.makedirs(exist_ok=True)
- **重複検出**: 既存ファイルチェックと適切な応答

**UI/UX設計**
- **発見性**: 3つのアクセス方法（トラック右クリック、Audioメニュー×2）
- **学習性**: 初心者はボタン、上級者は右クリック
- **フィードバック**: 操作結果の明確な通知

#### 🎨 ユーザーエクスペリエンス向上

**操作の流れ**
1. **アクセス**: トラック右クリック → "Audio Source..." 
2. **追加**: "🎵 Add Soundfont..." → ファイル選択 → 自動登録
3. **選択**: 追加されたサウンドフォント → GM楽器選択
4. **削除**: サウンドフォント右クリック → "🗑️ サウンドフォントを削除"

**安全機能**
- **確認ダイアログ**: 削除時の詳細影響説明
- **自動トラック処理**: 削除ソース使用中トラックの自動解除
- **サイズ警告**: 大容量ファイル（500MB+）の確認

#### 📊 実装統計
- **新規メソッド**: 8個（追加・削除・更新・検証）
- **修正ファイル**: 4個（manager, dialog, main_window, track_list）
- **削除コード**: AudioSourceType.NONE関連の全コード
- **新機能**: サウンドフォント追加・削除・右クリック管理

#### 🚀 成果
- **シンプル化**: 不要な「無音選択」オプション削除
- **直感性**: Add/Remove対称ボタンによる明確な操作
- **効率性**: 複数アクセス方法による柔軟な操作
- **堅牢性**: エラーハンドリングと安全確認の実装
- **配布ファイル**: `DominoPy-v1.0.0-macos.zip` (207MB)
- **クリーンビルド**: 空のsoundfontsフォルダ付きで配布
- **ユーザーガイド**: 正確なセットアップ手順（トラック名ダブルクリック）を記載

#### 📊 技術的影響
- **互換性**: 既存の設定ファイルとの互換性は一時的に失われる
- **移行**: ユーザーは新しいApplication Supportパスに手動移行が必要
- **識別性**: プロジェクトの一意性が確保され、混同リスクが解消

#### 🔄 次のステップ
- Audio メニューからのサウンドフォント設定機能実装
- トラック右クリックでの Audio Source 設定機能実装
- より直感的な UX 改善のためのバージョンアップ

### 2025-07-25: リアルタイムオーディオ機能と右クリック音修正
**UX改善**: 即座の音響フィードバックとプレビュー機能の完全動作

#### 🎯 修正の背景
- **即座性の欠如**: サウンドフォント追加後にアプリ再起動が必要
- **右クリック音問題**: 和音プレビュー機能が動作しない
- **ユーザビリティ**: 音響フィードバックの即時性改善
- **デバッグ効率**: 根本原因特定のための段階的解析アプローチ

#### 📋 実装した修正内容

**1. アプリケーション起動時のデフォルトオーディオソース自動割り当て** (`src/ui/main_window.py`)
- **_auto_assign_default_audio_sources()**: 全トラックに利用可能な最初のサウンドフォントを自動割り当て
- **_validate_track_audio_assignments()**: TrackManager初期化後の割り当て漏れをチェック・修正
- **段階的タイミング**: QTimerを使用した適切な初期化順序制御
- **楽器多様性**: トラックごとに異なるGMプログラム（楽器）を自動割り当て

**2. リアルタイムオーディオルーティング更新** (`src/ui/audio_source_dialog.py`)
- **_update_audio_routing_realtime()**: オーディオソース変更の即座反映
- **AudioRoutingCoordinator.refresh_track_route()**: 古いルート無効化と新ルート設定
- **シームレスUX**: アプリ再起動不要のライブ音響更新
- **トラック表示更新**: UI要素の自動同期

**3. 右クリック音機能の根本修復** (`src/ui/piano_roll_widget.py`)
- **古いenum参照削除**: `AudioSourceType.NONE`への参照を完全除去
- **AttributeError解決**: 右クリック処理時のエラー回避
- **和音プレビュー復活**: ノート右クリック・空エリア右クリックの両方で音が再生
- **エラーハンドリング**: `if not track_source:`による適切なnull検証

#### 🛠️ 技術的実装詳細

**問題特定プロセス**
1. **段階的デバッグ**: テストスクリプトによる機能分離検証
2. **UIイベント解析**: 実際のmousePressEvent処理の詳細ログ
3. **エラートレース**: AttributeErrorの正確な発生箇所特定
4. **回帰防止**: 全ての関連箇所の一括修正

**修正された処理フロー**
```python
# 修正前（エラーの原因）
if track_source and track_source.source_type == AudioSourceType.NONE:
    return False  # AttributeError発生

# 修正後（正常動作）
if not track_source:
    return False  # 適切なnullチェック
```

**自動割り当てシステム**
```python
def _auto_assign_default_audio_sources(self, audio_source_manager):
    # 利用可能な最初のサウンドフォントを取得
    default_source = audio_source_manager.get_soundfont_sources()[0]
    
    # 全トラック（8個）に割り当て
    for track_index in range(num_tracks):
        audio_source_manager.assign_source_to_track(track_index, default_source.id)
```

#### 🎨 ユーザーエクスペリエンス向上

**即座性の実現**
- **サウンドフォント追加 → 即座に音が出る**: アプリ再起動不要
- **右クリック → 即座に和音プレビュー**: ノート・空エリア両対応
- **トラック切り替え → 即座に楽器変更**: リアルタイム音響フィードバック

**音響フィードバック**
- **ノート入力クリック**: 音によるフィードバック ✅
- **Piano Roll鍵盤クリック**: 視覚と音響の統合 ✅  
- **Virtual Keyboard**: キーボード押下の音響確認 ✅
- **右クリック和音プレビュー**: 和音の音響確認 ✅

#### 📊 検証結果

**修正前の問題**
```
AttributeError: NONE
Error calling Python override of QWidget::mousePressEvent()
```

**修正後の正常動作**
```
🖱️ MousePressEvent Debug: Right-click processing
AudioRoutingCoordinator: Note 60 playing on track 0, channel 0
AudioRoutingCoordinator: Note 64 playing on track 0, channel 0  
AudioRoutingCoordinator: Note 67 playing on track 0, channel 0
PianoRoll: Chord preview with 3 notes playing on track 0
Chord at playhead: C (C, E, G)
```

#### 🚀 成果
- **完全なプレビュー機能**: 全ての音響フィードバックが正常動作
- **即座のUX**: サウンドフォント操作の即時反映
- **エラー解消**: 右クリック時のクラッシュ問題完全修復
- **音楽的UX**: 和音検出・表示による音楽理論的フィードバック
- **開発効率**: 段階的デバッグアプローチによる効率的問題解決

#### 🔄 技術的債務の解消
- **enum整合性**: AudioSourceType.NONEの完全除去による型安全性向上
- **初期化順序**: 適切なタイミング制御による安定性向上
- **エラーハンドリング**: nullチェックの統一による堅牢性向上

### 2025-07-25: GM Instrument音色変更機能の修復
**音楽機能修正**: Select GM Instrumentダイアログでの楽器変更が正常に反映されるよう修正

#### 🎯 問題の背景
- **音色固定問題**: GM Instrumentダイアログで楽器を変更してもGrand Piano音色のまま変わらない
- **根本原因特定**: AudioSourceManagerの`assign_source_to_track()`メソッドでプログラム番号上書き
- **ユーザー体験**: 楽器選択機能が事実上無効化されている状態

#### 🔍 問題の詳細調査

**症状の再現**
```
GM Instrument変更をシミュレート: Flute (program=73)
Applied track 0 program 0 to soundfont GM: Flute  ← program=0に強制上書き
AudioRoutingCoordinator: Track 0 program: 0, channel: 0  ← 常にピアノ
```

**原因箇所**: `src/audio_source_manager.py`の`assign_source_to_track()`メソッド（206-221行目）
- GM Instrumentダイアログで作成される`internal_fluidsynth_ch*`ソースも`get_track_program_for_soundfont()`による上書き対象
- トラック0の場合、常にDEFAULT_TRACK_PROGRAMS[0]=0（ピアノ）が強制設定される

#### 📋 実装した修正内容

**修正方針**: GM専用ソースのプログラム番号保護
- 通常のサウンドフォントファイル: 従来通りデフォルトプログラム適用
- GM専用ソース（`internal_fluidsynth_ch*`）: 選択されたプログラム番号を保持

**修正前のコード**
```python
# For soundfont sources, apply track-specific program
source = self.available_sources[source_id]
if source.source_type == AudioSourceType.SOUNDFONT:
    source.program = get_track_program_for_soundfont(track_index, source.name)
    source.channel = track_index % 16
```

**修正後のコード**
```python
# For soundfont sources, apply track-specific program
source = self.available_sources[source_id]
if source.source_type == AudioSourceType.SOUNDFONT:
    # GM Instrumentダイアログで作成されたソースはプログラム保持
    if not source_id.startswith("internal_fluidsynth_ch"):
        source.program = get_track_program_for_soundfont(track_index, source.name)
        source.channel = track_index % 16
        print(f"Applied track {track_index} program {source.program} to soundfont {source.name}")
    else:
        # GM専用ソースはプログラム番号を保持
        source.channel = track_index % 16  # チャンネルのみ更新
        print(f"Preserved GM instrument program {source.program} for track {track_index}")
```

#### 🎨 修正効果の検証

**修正後の正常動作**
```
Preserved GM instrument program 73 for track 0  ← 正しく保持
📌 Assigned internal_fluidsynth_ch0 to track 0 (program: 73)
AudioRoutingCoordinator: Track 0 program: 73, channel: 0  ← 73で設定
✅ AudioRoutingCoordinator: Set program 73 (GM: Flute) for channel 0
```

**全楽器での動作確認**
- **Acoustic Grand Piano (0)**: ✅ 正常
- **Violin (40)**: ✅ 正常  
- **Flute (73)**: ✅ 正常
- **Reverse Cymbal (120)**: ✅ 正常
- **Steel String Guitar (25)**: ✅ 正常

#### 🚀 成果
- **楽器変更機能の完全復活**: GM Instrumentダイアログでの楽器選択が即座に音色に反映
- **後方互換性**: 既存のサウンドフォントファイルの動作に影響なし
- **マルチトラック対応**: 各トラックで独立した楽器選択が可能
- **リアルタイム反映**: 楽器変更後すぐに新しい音色でプレビュー可能

#### 🔄 技術的改善
- **条件分岐による保護**: GM専用ソース識別による適切な処理分岐
- **デバッグ改善**: プログラム保持の明確なログ出力
- **型安全性**: AudioSourceのプログラム番号整合性確保

---

### 2025-07-23: ピアノロールノート編集機能の大幅改善
**UI/UX革新**: グリッドスナップ制御とダイレクトノート操作の実現

#### 🎯 実装目標
- より直感的で効率的なノート編集体験の提供
- プロフェッショナルDAWレベルの操作性実現
- 16分音符制限の撤廃と任意長さ調整の実現
- 複数ノート選択時の操作性大幅改善

#### 📋 主要改善内容

**1. グリッドスナップ制御システム**
- **Alt/Optionキー**: リアルタイムでグリッドスナップ無効化
- **フリーリサイズ**: 任意の長さでノート調整が可能
- **動的制御**: 全ての編集操作（ドラッグ、リサイズ、ペースト）に適用
- **16分音符制限の撤廃**: ピクセル単位での精密編集

**2. 複数ノート選択時のリサイズ革新**
- **直感的動作**: 複数選択時は全ノートが比例リサイズ
- **シンプル操作**: 修飾キー不要のストレートな操作
- **個別編集**: 単一選択で個別ノート調整
- **選択状態維持**: 編集後も選択状態を保持

**3. 統一されたスナップ制御**
```python
def _apply_grid_snap(self, tick: int, modifiers=None) -> int:
    # Alt/Optionキーでスナップ無効化
    if modifiers and (modifiers & Qt.AltModifier):
        return tick  # フリーモード
    
    if not self.snap_enabled:
        return tick  # グローバル設定
    
    return round(tick / self.quantize_grid_ticks) * self.quantize_grid_ticks
```

#### 🔧 技術的実装

**ファイル変更:**
- `src/ui/piano_roll_widget.py`: メイン編集ロジック全面改修

**新機能:**
- `_apply_grid_snap()`: 統一スナップ制御メソッド
- `toggle_grid_snap()`: 動的スナップ切り替え
- `_handle_proportional_multi_resize()`: 比例リサイズ専用処理

**操作統合:**
- 全ての量子化処理を`_apply_grid_snap()`に統一
- マウス修飾キーのリアルタイム検出
- 複数ノートリサイズの大幅簡素化

#### 🎮 新しい操作体系

**基本操作:**
```
通常ドラッグ/リサイズ: グリッドスナップあり
Alt/Option + ドラッグ: フリー編集（スナップなし）
```

**複数ノート編集:**
```
複数選択 + リサイズ: 全ノートを比例リサイズ
単一選択 + リサイズ: 個別ノート調整
```

**使用例:**
- **精密編集**: Alt押しながらドラッグで1tick単位調整
- **一括調整**: 複数選択してリサイズで統一的な長さ変更
- **個別微調整**: 単一選択で特定ノートのみ調整

#### 📊 改善結果

**操作性向上:**
- **直感性**: 期待通りの動作で学習コストゼロ
- **効率性**: 修飾キー不要のシンプル操作
- **柔軟性**: 必要時のみ精密モードに切り替え
- **一貫性**: 全編集操作で統一されたスナップ制御

**技術的成果:**
- **コード統一**: 重複した量子化処理を一元化
- **保守性向上**: メソッド分離による可読性向上
- **拡張性確保**: 将来機能への対応基盤構築

**ユーザー体験:**
- **学習不要**: DAW経験者なら即座に理解可能
- **作業効率**: 選択解除が不要で連続編集が快適
- **精密制御**: プロ用途でも満足できる調整精度

#### 💡 設計思想

**シンプルファースト:**
- 複雑な修飾キー組み合わせを排除
- 最も頻繁な操作を最もシンプルに

**期待に応える:**
- 複数選択したら全体が変わる（自然な期待）
- 単一選択なら個別調整（明確な意図）

**必要時のみ複雑:**
- 基本操作は簡単
- 精密編集時のみAlt/Option使用

### 2025-07-23: 仮想キーボードUIモダン化とSustainペダル機能実装
**UI/UX大幅改善**: 見やすく美しいモダンデザインへの全面リニューアル + Logic Pro準拠機能追加

#### 🎨 仮想キーボードUIモダン化
**実装目標**: 視認性向上と現代的なデザインへの全面改修

**実装内容:**

**1. 鍵盤キーラベルの改善**
- フォントサイズ拡大: 特殊文字（; :）16px/14px、通常文字14px/12px
- 特殊文字の視認性向上: 深い青色（白鍵）、明るい黄色（黒鍵）
- モダンな色彩設計とコントラスト最適化

**2. Controlsパネルの大幅改善**
- 横並びレイアウト採用: Octave/Velocity/Sustain を効率的配置
- フォントサイズ統一拡大: 12px太字（各ラベル）
- 視覚的キーボードキー描画: 35x25pxの3Dキーボタン表示
- Track情報・Sustain表示の可読性向上

**3. Chord Display & Harmonic Analysis統合**
- 横並び配置でスペース効率化
- フォントサイズ最適化:
  - Chord notes: 10px → 12px
  - Interval analysis: 11px → 13px  
  - Key suggestion: 10px → 12px
- パディング増加と最小高さ設定

**技術的実装:**
```python
def _create_keyboard_key_display(self, keys, functions):
    # 直感的キー・機能ペアリング
    group_layout.setSpacing(3)  # キーと機能記号を密着配置
    func_label.setFont(QFont("Arial", 18, QFont.Bold))  # 機能記号18px
    # レイアウト: [Z]− [X]+ [C]− [V]+ [Tab]Toggle
```

**4. 段階的UI改善プロセス**
- **Phase 1**: 基本フォントサイズ拡大（; : キー16px/14px）
- **Phase 2**: Controls横並びレイアウト + 視覚的キーボードキー描画
- **Phase 3**: Chord Display & Harmonic Analysis横並び配置
- **Phase 4**: スペース有効活用とフォント・色彩統一
- **Phase 5**: 直感的キー・機能ペアリング（最終調整）

#### 📊 UI改善結果
- **視認性**: 全フォントサイズ統一拡大により大幅改善（最大18px）
- **操作性**: 視覚的キーボードキー + 直感的配置で完璧な理解
- **デザイン**: モダンで統一感のある美しいUI（統一色彩・角丸6px）
- **効率性**: 横並びレイアウトでスペース活用最適化
- **直感性**: キーと機能が視覚的に一体化（3px間隔）

**修正ファイル:**
- `src/ui/virtual_keyboard_widget.py`: 全面的UIモダン化実装

### 2025-07-23: 仮想キーボードSustainペダル機能実装
**Logic Pro準拠機能追加**: TabキーによるSustainペダル機能とJISキーボード最適化

#### 🎹 実装目標
- Logic Pro準拠のTabキーSustainペダル機能
- 本格的な音響持続効果の実装
- MacのJISキーボードでの動作保証
- 視覚的フィードバックの提供

#### 📋 実装内容

**1. Sustainペダル基本機能**
- `Qt.Key_Tab`でSustain ON/OFF切り替え
- UI表示: "Sustain: OFF" / "Sustain: ON"（緑色、太字）
- MIDI Control Change 64メッセージ送信（127=ON, 0=OFF）

**2. 音響持続効果**
```python
# 持続音管理
self.sustained_notes: Set[int] = set()

# キーリリース時の処理
if self.sustain_active:
    self.sustained_notes.add(midi_pitch)  # 持続音として保持
else:
    self.note_released.emit(midi_pitch)   # 通常リリース
```

**3. MacのJISキーボード対応**
- `eventFilter`によるTabキー確実キャッチ
- フォーカス管理強化（`setFocus` + `activateWindow`）
- キー圧縮無効化（`Qt.WA_KeyCompression`）
- フォーカスヒント追加: "※ Click here first to ensure keyboard focus"

**4. 視覚的統合**
- 鍵盤表示: 持続音も青色ハイライト表示
- コード分析: `pressed_notes | sustained_notes`による統合解析
- デバッグ出力: 持続/解放の詳細ログ

#### 🔧 技術的実装

**AudioRoutingCoordinator拡張:**
```python
def send_control_change(self, track_index: int, controller: int, value: int) -> bool:
    """Send MIDI Control Change message for specific track"""
    # FluidSynth, 外部MIDI, Soundfont対応
    # 複数音源での確実なCC送信
```

**Sustain動作フロー:**
1. **Tab押下** → `sustain_toggle` → UI更新 + CC64送信
2. **キー演奏** → 通常のnote_on処理
3. **キーリリース** → `sustained_notes`に追加（音継続）
4. **Tab再押下** → 持続音すべて解放 + CC64(0)送信

#### 📊 修正結果
- **Logic Pro互換**: TabキーSustain動作
- **音響効果**: 真のペダル持続機能
- **JISキーボード**: Mac環境での確実動作
- **安全性**: アプリ終了時の自動リリース
- **UI/UX**: 直感的な操作と視覚フィードバック

**修正ファイル:**
- `src/ui/virtual_keyboard_widget.py`: Sustain機能メイン実装
- `src/audio_routing_coordinator.py`: `send_control_change`メソッド追加

#### 💡 技術的ポイント
- **状態分離**: `pressed_notes`（物理）と`sustained_notes`（仮想）
- **統合表示**: 両方を合わせた視覚・音響フィードバック
- **イベント処理**: Tab キーの特殊扱いに対するeventFilter対応
- **MIDI準拠**: 標準CC64による音源互換性

### 2025-07-23: 仮想キーボード表示鍵盤数の修正 & JISキーボード対応
**UI/UX改善**: 表示鍵盤数と実際のキーマッピング範囲の一致、JISキーボード最適化

#### 🎯 修正目標
- 仮想キーボードの表示鍵盤数と実際にタイピングで演奏可能な音の数を一致させる
- JISキーボードでの操作性を向上（':'キーの採用）
- ユーザーの混乱を解消し、より直感的なUI/UX体験を提供

#### 📋 問題分析
**修正前の問題:**
- 仮想キーボード表示: 2オクターブ（14個の白鍵）
- 実際のキーマッピング: 11個の白鍵のみ対応
- ユーザーが鍵盤をクリックしても音が出ない範囲が存在

**キーマッピング詳細:**
- 白鍵: A(C) S(D) D(E) F(F) G(G) H(A) J(B) K(C+12) L(D+12) ;(E+12) :(F+12)
- 黒鍵: W(C#) E(D#) T(F#) Y(G#) U(A#) O(C#+12) P(D#+12)

#### 🔧 実装内容

**1. 表示鍵盤数の調整**
- `VirtualKeyboardWidget.visible_octaves = 2` → `visible_keys = 11`
- `PianoKeyboardDisplay.visible_octaves = 2` → `visible_keys = 11`

**2. 鍵盤描画ロジックの更新**
```python
# 白鍵レイアウト: C D E F G A B C D E F（11鍵）
white_key_offsets = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17]

# 黒鍵レイアウト: C# D# F# G# A# C# D#（7鍵）
black_key_positions = [0.7, 1.7, 3.7, 4.7, 5.7, 7.7, 8.7]
black_note_offsets = [1, 3, 6, 8, 10, 13, 15]
```

**3. JISキーボード対応**
- F+12キーを`Qt.Key_Apostrophe("'")`から`Qt.Key_Colon(":")`に変更
- JISキーボードで打ちやすい位置（;キーの右隣）への最適化

**4. UI表示の改善**
- キーマッピング説明を「A S D F G H J K L ; :」に更新
- 「JIS keyboard optimized」の注記を追加
- 正確な鍵盤配置（C-B-C-D-E-F）の説明

#### 📊 修正結果
- **表示鍵盤**: 11個の白鍵 + 対応する7個の黒鍵
- **演奏可能範囲**: タイピングキーボードと完全一致
- **UI/UX**: 混乱のない直感的な操作体験

**修正ファイル:**
- `src/ui/virtual_keyboard_widget.py`: メイン修正
  - `VirtualKeyboardWidget.__init__()`: visible_keys設定
  - `PianoKeyboardDisplay._draw_white_keys()`: 11鍵描画
  - `PianoKeyboardDisplay._draw_black_keys()`: 対応黒鍵描画
  - UI説明テキストの更新

#### 💡 技術的解決策
- **正確な鍵盤マッピング**: 実際のキー配置に基づく描画計算
- **動的レイアウト**: 鍵盤数に応じた自動サイズ調整
- **視覚的一貫性**: 白鍵・黒鍵の正しい位置関係を維持

### 2025-07-23: Strudelプロトタイプコード整理
**プロジェクト整理**: 不要なプロトタイプファイルの削除とGit管理の整備

#### 🎯 整理目標
- Strudelローカル実行環境確立により、DominoPy内実装が不要となったため整理
- プロダクションコードのクリーンアップとディレクトリ構成の最適化

#### 📋 削除対象
**プロトタイプ・テストファイル:**
- WebSocket統合関連: `websocket_midi_server.py`, `realtime_midi_bridge.py`
- JavaScript統合: `strudel_websocket_client.js`, `strudel_midi_bridge.js`
- Node.js関連: `package.json`, `package-lock.json`, `node_modules/`
- ターミナル機能: `*terminal*.py`ウィジェット群
- テストファイル: `test_strudel_*.py`, `test_*terminal*.py`
- 開発時テスト: `test_app_audio.py`, `test_audio_issue.py` など

**保持されたファイル:**
- Strudelドキュメント（将来の参考資料として）
- 本体機能コード（完全に保持）

#### 🔧 実装内容
**1. .gitignore更新**
```bash
# Strudel integration docs (private - not for public release)
docs/STRUDEL_LOCAL_SETUP.md
docs/STRUDEL_WEBSOCKET_API.md  
docs/STRUDEL_WEBSOCKET_INTEGRATION_PLAN.md
docs/STRUDEL_WEBSOCKET_SETUP.md
docs/TERMINAL_FEATURE_PLAN.md
```

**2. 依存関係の無効化**
- `midi_input_system.py`: WebSocket機能を無効化に変更
- 残存する参照の安全な処理

**3. アプリケーション動作確認**
- 全機能正常動作確認済み
- MIDIルーティング、オーディオシステム、UI操作すべて正常

#### 📊 整理結果
- **ディレクトリ**: クリーンで整理された構成
- **Git管理**: 公開すべきでないドキュメントの適切な除外
- **機能**: 本体機能への影響一切なし
- **保守性**: 不要コードの除去により向上

### 2025-07-17: JavaScriptターミナル機能プロトタイプ実装
**プロトタイプ開発**: ライブコーディング統合に向けた実験的実装

#### 🎯 実装目標
- DominoPyにターミナル機能を追加してStrudelライブコーディングとの連携を実現
- フレキシブルなレイアウト対応（ドッキング、タブ表示）
- Node.js統合によるJavaScript実行環境の構築
- 将来的な汎用ターミナル化への拡張基盤準備

#### 📋 実装内容

**1. JavaScript専用ターミナル作成**
- `JavaScriptTerminalWidget`: Node.js実行環境を統合したターミナル
- シンタックスハイライト機能（JavaScriptキーワード、文字列、コメント）
- リアルタイムコード実行とエラーハンドリング
- 一時ファイル管理とプロセス制御

**2. フレキシブルレイアウト実装**
- `TerminalDockWidget`: 右側・下側・フローティングドッキング対応
- `TerminalTabWidget`: タブベースのレイアウト
- 設定保存・復元機能（QSettings）
- 動的なレイアウト切り替え

**3. プロトタイプテスト環境**
- `test_terminal_prototype.py`: スタンドアローンテストアプリケーション
- 全レイアウトモードの動作確認
- サンプルJavaScriptコードの自動実行テスト

#### 🔧 技術的詳細

**新規作成ファイル:**
- `src/ui/javascript_terminal_widget.py`: メインターミナルウィジェット
- `src/ui/terminal_dock_widget.py`: ドッキング＆タブ機能
- `test_terminal_prototype.py`: プロトタイプテストアプリ
- `docs/TERMINAL_FEATURE_PLAN.md`: 実装計画ドキュメント

**主要クラス:**
- `JavaScriptTerminalWidget`: 核となるターミナル機能
- `JavaScriptHighlighter`: シンタックスハイライト
- `TerminalDockWidget`: ドッキング管理
- `TerminalTabWidget`: タブレイアウト管理

**技術スタック:**
- PySide6 (QProcess, QPlainTextEdit, QDockWidget, QTabWidget)
- Node.js v18.17.0 (JavaScript実行環境)
- QSyntaxHighlighter (シンタックスハイライト)
- QSettings (設定永続化)

#### ✅ 成果
- 完全に動作するJavaScriptターミナルプロトタイプ
- 3つのレイアウトモード（右ドッキング、下ドッキング、タブ表示）
- Node.js統合による安定したJavaScript実行環境
- 拡張可能なアーキテクチャ設計
- 包括的なテスト環境とドキュメント

#### 🧪 テスト結果
- Node.js実行環境: ✅ 正常動作 (v18.17.0)
- JavaScript実行: ✅ 正常動作（console.log、配列操作、数学演算）
- シンタックスハイライト: ✅ 正常動作
- レイアウト切り替え: ✅ 正常動作
- エラーハンドリング: ✅ 正常動作

#### 🚀 将来の拡張計画
1. **DominoPyメインUI統合**: 実際のアプリケーションへの組み込み
2. **Strudel統合**: npm + Strudelライブラリの統合
3. **MIDI連携**: DominoPyとの双方向MIDI通信
4. **汎用ターミナル化**: 他言語サポート拡張

#### 📚 アーキテクチャ設計パターン
- **プロトタイプ開発**: 段階的な実装とテスト
- **モジュラー設計**: 機能別クラス分離
- **設定永続化**: ユーザー設定の保存・復元
- **クロスプラットフォーム**: PySide6標準機能の活用

---

### 2025-07-17: 拍子変更時の小節番号バー同期機能実装
**コミット**: `29453f9` - "Fix time signature change synchronization in measure bar"

#### 🎯 実装目標
- 拍子変更時に小節番号バーが小節線に正確に追従するように修正
- 正攻法によるアーキテクチャで安定した同期システムを実装
- 重複コードを削除し保守性を向上

#### 📋 実装内容

**1. 根本原因の特定と解決**
- 問題: MeasureBarWidgetに`midi_project`参照が初期化時に設定されていない
- 解決: `main_window.py`で`piano_roll`と同時に`measure_bar`にも`set_midi_project()`を呼び出し

**2. 適切な通知システムの実装**
- `MeasureBarWidget.on_time_signature_changed()`メソッドを追加
- 拍子変更時に`update()`のみを呼び出し、データの再設定は行わない
- 強制更新ではなく、適切な通知による更新を実現

**3. 動的な拍子情報取得**
- `paintEvent()`で毎回`midi_project.get_current_time_signature()`を呼び出し
- 最新の拍子情報を常に反映する仕組みを実装

**4. 重複コードの削除とリファクタリング**
- `MidiProject.calculate_ticks_per_measure()`メソッドを新規作成
- 拍子計算ロジックを中央集権化
- `measure_bar_widget.py`と`piano_roll_widget.py`の重複コード（約40行）を削除

#### 🔧 技術的詳細

**修正されたファイル:**
- `src/midi_data_model.py`: 拍子計算メソッドの追加
- `src/ui/main_window.py`: 初期化とイベント処理の修正
- `src/ui/measure_bar_widget.py`: 通知システムと描画ロジックの実装
- `src/ui/piano_roll_widget.py`: 重複コード削除とメソッド追加

**追加されたメソッド:**
- `MidiProject.calculate_ticks_per_measure()`: 拍子からticks per measureを計算
- `MeasureBarWidget.on_time_signature_changed()`: 拍子変更通知の受信
- `MeasureBarWidget._calculate_measure_number_at_tick()`: 拍子変更を考慮した小節番号計算
- `PianoRollWidget._draw_measure_lines_simple()`: 単一拍子での小節線描画
- `PianoRollWidget._draw_measure_lines_with_time_signature_changes()`: 拍子変更対応小節線描画

#### ✅ 成果
- 拍子変更時に小節番号バーが正確に追従
- 小節線と小節番号の完全な同期を実現
- 保守性の高い正攻法アーキテクチャを実装
- 約40行のコード削減と重複排除
- 全ての拍子（4/4、3/4、2/4、6/8、9/8、12/8など）で正常動作

#### 🐛 解決した問題
1. **拍子変更時の小節番号バー未更新** - 適切な初期化と通知システムで解決
2. **小節線と小節番号の不整合** - 動的な拍子情報取得で解決
3. **重複コードによる保守性問題** - 中央集権化された計算メソッドで解決
4. **強制更新による潜在的な不安定性** - 正攻法の通知システムで解決

#### 📚 実装パターン
- **動的情報取得**: 描画時に最新の状態を取得する設計
- **適切な通知**: 強制更新ではなく通知による更新
- **中央集権化**: 共通ロジックを一箇所に集約
- **保守性重視**: 将来の拡張を考慮したアーキテクチャ

---

### 2025-07-16: Mac版アプリバンドル実装
**コミット**: `7e5eb4e` - "Implement Mac app bundle creation with PyInstaller"

#### 🎯 実装目標
- macOSでメニューバーに「Python」ではなく「DominoPy」を表示
- クロスプラットフォーム対応を維持しながらネイティブアプリ化
- 開発効率を損なわない配布戦略の確立

#### 📋 実装内容

**1. ハイブリッド配布戦略の採用**
- Pythonスクリプト版: 開発者・上級者向け
- ネイティブアプリ版: 一般ユーザー向け
- 開発フローは変更なし

**2. PyInstallerによるアプリバンドル化**
- py2appからPyInstallerに変更（Python runtimeエラー回避）
- `DominoPy.spec`設定ファイル作成
- FluidSynthライブラリの動的リンクを解決

**3. 音声出力問題の解決**
- FluidSynth依存関係をバンドルに含める
- `/usr/local/Cellar/fluid-synth/2.4.6/lib/libfluidsynth.3.3.6.dylib`を同梱
- サウンドフォントファイル（`default.sf2`）の適切な配置

**4. アプリケーション設定の最適化**
- `src/main.py`でアプリケーション名設定を追加:
  ```python
  app.setApplicationName("DominoPy")
  app.setApplicationDisplayName("DominoPy")
  app.setOrganizationName("DominoPy")
  app.setOrganizationDomain("pydomino.app")
  ```
- Info.plistでバンドル情報を設定
- CFBundleName, CFBundleDisplayNameの適切な設定

**5. モジュール依存関係の解決**
- srcモジュールのimportエラーを修正
- PyInstaller設定でsrcディレクトリを適切に配置
- pathex設定でプロジェクトルートを追加

#### 🔧 技術的詳細

**作成・変更されたファイル:**
- `DominoPy.spec`: PyInstaller設定ファイル
- `setup.py`: py2app設定（参考用）
- `BUILD_INSTRUCTIONS.md`: ビルド手順書
- `docs/DEVELOPMENT_PLAN.md`: 開発計画更新
- `src/main.py`: アプリケーション名設定追加

**依存関係:**
- PyInstaller 6.14.2
- pyaudio 0.2.14
- FluidSynth 2.4.6 (Homebrew)

**ビルドコマンド:**
```bash
pip install pyinstaller pyaudio
pyinstaller DominoPy.spec
```

#### ✅ 成果
- macOSでメニューバーに「DominoPy」と正しく表示
- 音声出力が正常に動作
- 約215MBのスタンドアロンアプリケーション作成
- 開発フローに影響なし

#### 🐛 解決した問題
1. **Python runtimeエラー** - py2appからPyInstallerに変更
2. **音声が出ない** - FluidSynthライブラリを手動で同梱
3. **srcモジュールエラー** - pathexとdatasの設定で解決
4. **メニューバー表示** - アプリケーション名設定で解決

#### 📚 ドキュメント更新
- 開発計画にPhase 1完了をマーク
- ビルド手順書の作成
- トラブルシューティング情報の追加

---

### 以前の開発内容

#### 基本機能実装（継続中）
- **MIDI機能**: 外部MIDI機器との接続・ルーティング
- **オーディオ機能**: FluidSynthによる音声合成
- **ピアノロール**: ノート編集、再生機能
- **バーチャルキーボード**: マウス・キーボード入力対応
- **設定管理**: 各種設定の保存・読み込み

#### UI改善
- **メニューバー**: File, Edit, Audio, Settings等の整理
- **ピアノキーボード表示**: 黒鍵と白鍵の適切な配置
- **テーマ対応**: ライト・ダークテーマ

#### 技術基盤
- **PySide6**: クロスプラットフォームGUI
- **MIDI処理**: python-rtmidi
- **音声合成**: FluidSynth + pyaudio
- **設定管理**: JSON形式での永続化

---

## 今後の開発予定

### Phase 2: 他OS対応
- Windows版（PyInstaller）
- Linux版（PyInstaller/AppImage）

### Phase 3: CI/CD自動化
- GitHub Actions設定
- 自動ビルド・テスト
- リリース自動化

---

## 開発メモ

### 学んだ教訓
1. **py2app vs PyInstaller**: PyInstallerの方が依存関係解決が優秀
2. **動的ライブラリ**: Homebrewでインストールしたライブラリは手動で同梱が必要
3. **アプリ名表示**: setApplicationName()だけでなくInfo.plistの設定も重要

### 今後の注意点
- FluidSynthのバージョンアップ時はパス更新が必要
- 他のHomebrewライブラリ使用時も同様の対応が必要
- アプリサイズ最適化の検討

---

**最終更新**: 2025-07-17  
**次回更新予定**: Windows版実装時