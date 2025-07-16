# PyDomino ビルド手順書

## Mac版アプリバンドル作成

### 前提条件
- macOS 10.15以上
- Python 3.11+
- Homebrew
- FluidSynth (`brew install fluid-synth`)

### 依存関係インストール
```bash
pip install pyinstaller pyaudio
```

### ビルド実行
```bash
# プロジェクトルートで実行
pyinstaller PyDomino.spec
```

### 成果物確認
```bash
# アプリ起動
open dist/PyDomino.app

# アプリサイズ確認
du -sh dist/PyDomino.app
```

## トラブルシューティング

### 音声が出ない場合
- FluidSynthライブラリが正しく含まれているか確認：
```bash
find dist/PyDomino.app -name "*fluid*"
```

### アプリが起動しない場合
- ターミナルから直接実行してエラー確認：
```bash
./dist/PyDomino.app/Contents/MacOS/PyDomino
```

### srcモジュールエラー
- PyDomino.specの`datas`設定を確認
- プロジェクトルートから実行されているか確認

## 設定ファイル

### PyDomino.spec
主要設定項目：
- `binaries`: FluidSynthライブラリパス
- `datas`: サウンドフォント、srcディレクトリ
- `info_plist`: アプリ名、バンドルID設定

### 更新が必要な場合
FluidSynthのバージョンが変わった場合：
1. `brew --prefix fluid-synth`でパス確認
2. PyDomino.specの`binaries`セクション更新
3. 再ビルド

## 次のステップ
- Windows版対応（PyInstaller）
- Linux版対応（PyInstaller/AppImage）
- CI/CD自動化（GitHub Actions）

---
最終更新：2025-07-16