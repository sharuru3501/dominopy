# 🎹 DominoPy MIDI Sequencer

**Modern MIDI sequencer inspired by Domino, built with Python & PySide6**

DominoPy は Python と PySide6 で構築されたモダンな MIDI シーケンサーです。MIDIシーケンサー「Domino」にインスパイアされ、現代的な技術で再構築されました。

## 特徴

- **直感的なピアノロール**: ノートの入力・編集が簡単
- **リアルタイム再生**: 高品質なオーディオ出力
- **音楽理論サポート**: 音名・コード名の自動表示
- **テンポ・拍子制御**: リアルタイムでの変更が可能
- **メトロノーム機能**: ビジュアル・オーディオガイド
- **クロスプラットフォーム**: Windows、macOS、Linux対応
- **ホットキー対応**: 効率的な作業フロー
- **DAW連携**: Logic Pro、Ableton Live等との完全互換
- **バーチャルキーボード**: リアルタイム演奏機能

## 開始方法

### 必要要件
- Python 3.11+
- 依存関係は `requirements.txt` を参照

### インストール
```bash
pip install -r requirements.txt
```

### 実行
```bash
python run_app.py
```

## ディレクトリ構造

```
dominopy/
├── src/                    # メインソースコード
│   ├── audio_system.py     # オーディオシステム
│   ├── playback_engine.py  # 再生エンジン
│   ├── midi_*.py          # MIDI関連
│   └── ui/                # ユーザーインターフェース
├── tests/                 # テストファイル・診断ツール
├── docs/                  # ドキュメント
├── soundfonts/            # サウンドフォント
└── venv/                  # 仮想環境
```

## 📚 ドキュメント

- **[🎵 MIDI設定ガイド](docs/MIDI_SETUP.md)** - DAWとの連携方法（重要）
- **[📖 使用方法](docs/USAGE_GUIDE.md)** - 基本的な使用方法
- **[🔧 技術仕様](docs/TECHNICAL_SPEC.md)** - アーキテクチャと設計  
- **[🔊 オーディオ設定](docs/AUDIO_SETUP.md)** - オーディオシステムの設定

## 🤝 コントリビューション

DominoPyへの貢献を歓迎します！

1. **フォーク** このリポジトリをフォーク
2. **ブランチ作成** (`git checkout -b feature/amazing-feature`)
3. **コミット** (`git commit -m 'Add amazing feature'`)
4. **プッシュ** (`git push origin feature/amazing-feature`)
5. **プルリクエスト** 作成

## 📝 ライセンス

このプロジェクトは **MIT License** の下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

### 依存関係ライセンス
- **PySide6**: LGPL v3 / Commercial
- **mido**: MIT License
- **pyfluidsynth**: LGPL v2.1

## 🙏 謝辞

- **Domino** - オリジナルMIDIシーケンサーへの敬意とインスパイア
- **オープンソースコミュニティ** - 素晴らしいライブラリとツールの提供

---

**DominoPy** - Made with ❤️ for music creators