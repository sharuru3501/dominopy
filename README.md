# PyDomino MIDI Sequencer

PyDomino は Python と PySide6 で構築されたモダンな MIDI シーケンサーです。

## 特徴

- **直感的なピアノロール**: ノートの入力・編集が簡単
- **リアルタイム再生**: 高品質なオーディオ出力
- **音楽理論サポート**: 音名・コード名の自動表示
- **テンポ・拍子制御**: リアルタイムでの変更が可能
- **メトロノーム機能**: ビジュアル・オーディオガイド
- **クロスプラットフォーム**: Windows、macOS、Linux対応
- **ホットキー対応**: 効率的な作業フロー

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
pydominodev/
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

## ドキュメント

- [使用方法](docs/USAGE_GUIDE.md) - 基本的な使用方法
- [技術仕様](docs/TECHNICAL_SPEC.md) - アーキテクチャと設計
- [開発計画](docs/DEVELOPMENT_PLAN.md) - 開発ロードマップ
- [オーディオ設定](docs/AUDIO_SETUP.md) - オーディオシステムの設定
- [要件](docs/REQUIREMENTS.md) - システム要件

## トラブルシューティング

### デバッグツール
```bash
# デバッグモードで実行
python run_debug.py

# システム診断
python tests/test_diagnostics.py

# オーディオデバッグ
python tests/test_audio_debug.py

# 安定性テスト
python tests/test_stability.py
```

### よくある問題
- [クラッシュ修正ガイド](docs/CRASH_FIXES.md)
- [ペースト問題の解決](docs/PASTE_TROUBLESHOOTING.md)

## 開発

### テスト実行
```bash
# 全テスト実行
python -m pytest tests/

# 特定のテスト
python tests/test_features.py
```

### ライセンス
このプロジェクトはオープンソースです。