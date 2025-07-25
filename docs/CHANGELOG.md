# DominoPy 変更履歴

## 概要
このファイルは、DominoPyの各バージョンでの変更点を記録します。
[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/)形式に従います。

## [Unreleased]

### Added
- Mac版アプリバンドル作成機能
- PyInstaller設定ファイル（DominoPy.spec）
- ビルド手順書（BUILD_INSTRUCTIONS.md）
- 開発履歴ドキュメント（DEVELOPMENT_HISTORY.md）
- 変更履歴管理システム（CHANGELOG.md）

### Changed
- メニューバーでのアプリ名表示を「Python」から「DominoPy」に変更
- アプリケーション設定の最適化（setApplicationName等）

### Fixed
- macOSでの音声出力問題（FluidSynthライブラリ同梱）
- srcモジュールの import エラー
- アプリバンドル作成時のPython runtime エラー

## [0.1.0] - 2025-07-16

### Added
- 初期リリース
- MIDI入出力機能
- ピアノロール編集機能
- バーチャルキーボード
- FluidSynthによる音声合成
- 設定管理機能
- クロスプラットフォーム対応（開発版）

---

## 変更タイプの説明

- **Added**: 新機能
- **Changed**: 既存機能の変更
- **Deprecated**: 今後削除予定の機能
- **Removed**: 削除された機能
- **Fixed**: バグ修正
- **Security**: セキュリティ関連の修正

---

## 次回更新予定

### Windows版対応
- PyInstallerでのWindows版アプリ作成
- Windows固有の依存関係解決
- インストーラー作成

### Linux版対応
- AppImageによるLinux版配布
- 主要ディストリビューションでの動作確認

### CI/CD自動化
- GitHub Actionsによる自動ビルド
- 複数OS対応の自動テスト
- 自動リリース機能

---

**最終更新**: 2025-07-16