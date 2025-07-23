# PyDomino 開発履歴

## 概要
PyDominoは、PySide6を使用したクロスプラットフォーム対応のMIDIピアノロールアプリケーションです。
このドキュメントは、開発過程で実装された機能や修正の詳細な履歴を記録します。

## 開発履歴

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
- Strudelローカル実行環境確立により、PyDomino内実装が不要となったため整理
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
- PyDominoにターミナル機能を追加してStrudelライブコーディングとの連携を実現
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
1. **PyDominoメインUI統合**: 実際のアプリケーションへの組み込み
2. **Strudel統合**: npm + Strudelライブラリの統合
3. **MIDI連携**: PyDominoとの双方向MIDI通信
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
- macOSでメニューバーに「Python」ではなく「PyDomino」を表示
- クロスプラットフォーム対応を維持しながらネイティブアプリ化
- 開発効率を損なわない配布戦略の確立

#### 📋 実装内容

**1. ハイブリッド配布戦略の採用**
- Pythonスクリプト版: 開発者・上級者向け
- ネイティブアプリ版: 一般ユーザー向け
- 開発フローは変更なし

**2. PyInstallerによるアプリバンドル化**
- py2appからPyInstallerに変更（Python runtimeエラー回避）
- `PyDomino.spec`設定ファイル作成
- FluidSynthライブラリの動的リンクを解決

**3. 音声出力問題の解決**
- FluidSynth依存関係をバンドルに含める
- `/usr/local/Cellar/fluid-synth/2.4.6/lib/libfluidsynth.3.3.6.dylib`を同梱
- サウンドフォントファイル（`default.sf2`）の適切な配置

**4. アプリケーション設定の最適化**
- `src/main.py`でアプリケーション名設定を追加:
  ```python
  app.setApplicationName("PyDomino")
  app.setApplicationDisplayName("PyDomino")
  app.setOrganizationName("PyDomino")
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
- `PyDomino.spec`: PyInstaller設定ファイル
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
pyinstaller PyDomino.spec
```

#### ✅ 成果
- macOSでメニューバーに「PyDomino」と正しく表示
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