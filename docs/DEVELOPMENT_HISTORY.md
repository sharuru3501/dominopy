# PyDomino 開発履歴

## 概要
PyDominoは、PySide6を使用したクロスプラットフォーム対応のMIDIピアノロールアプリケーションです。
このドキュメントは、開発過程で実装された機能や修正の詳細な履歴を記録します。

## 開発履歴

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