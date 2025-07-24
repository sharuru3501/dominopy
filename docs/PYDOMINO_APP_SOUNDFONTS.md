# PyDomino.app サウンドフォント追加ガイド

## 概要

PyDomino.appでは、デフォルトでTimGM6mb.sf2サウンドフォントが内蔵されていますが、追加のサウンドフォントを使用することができます。

## サウンドフォント追加方法

### 1. サウンドフォントフォルダーを開く

PyDomino.appのサウンドフォントフォルダーは以下の場所にあります：

```
~/Library/Application Support/PyDomino/soundfonts/
```

### 2. フォルダーの作成

初回使用時は自動的にフォルダーが作成されますが、手動で作成することもできます：

```bash
mkdir -p ~/Library/Application\ Support/PyDomino/soundfonts/
```

### 3. サウンドフォントファイルの配置

`.sf2` ファイルを上記のフォルダーに配置してください：

```bash
# 例：FluidR3_GM.sf2をコピーする場合
cp /path/to/FluidR3_GM.sf2 ~/Library/Application\ Support/PyDomino/soundfonts/
```

### 4. PyDomino.appの再起動

サウンドフォントを追加した後は、PyDomino.appを再起動してください。

## サウンドフォント選択

1. PyDomino.appを起動
2. メニューバーから `Audio` → `Audio Settings...` を選択
3. 利用可能なサウンドフォントから選択

## 推奨サウンドフォント

### 高品質サウンドフォント
- **FluidR3_GM.sf2** (約140MB) - 高品質なGeneral MIDI音源
- **MuseScore_General.sf2** (約35MB) - バランスの取れた音質

### 軽量サウンドフォント
- **TimGM6mb.sf2** (約6MB) - デフォルト、軽量で高品質
- **GeneralUser GS.sf2** (約30MB) - 汎用的な音源

## 注意事項

### ファイル形式
- 対応形式：`.sf2` (SoundFont 2.0)
- 大きすぎるファイル（500MB以上）は避けてください

### ライセンス
- 使用するサウンドフォントのライセンスを確認してください
- 商用利用の場合は、ライセンスに注意が必要です

### 容量管理
- 複数のサウンドフォントを配置すると容量が増加します
- 不要なファイルは削除してください

## Python版との違い

| 項目 | Python版 (run_app.py) | PyDomino.app |
|------|----------------------|-------------|
| サウンドフォント保存場所 | `./soundfonts/` | `~/Library/Application Support/PyDomino/soundfonts/` |
| 設定方法 | プロジェクトフォルダーに配置 | アプリケーションサポートフォルダーに配置 |
| 再起動の必要性 | 不要（自動検出） | 必要 |

## トラブルシューティング

### サウンドフォントが認識されない場合
1. ファイルパスを確認：`~/Library/Application Support/PyDomino/soundfonts/`
2. ファイル形式を確認：`.sf2` 拡張子
3. PyDomino.appを再起動
4. ファイルサイズを確認：10KB以上のファイルのみ認識

### フォルダーが見つからない場合
```bash
# Finderで開く
open ~/Library/Application\ Support/PyDomino/soundfonts/

# 存在しない場合は作成
mkdir -p ~/Library/Application\ Support/PyDomino/soundfonts/
```

### 権限エラーが発生する場合
```bash
# フォルダーの権限を確認
ls -la ~/Library/Application\ Support/PyDomino/

# 権限を修正（必要に応じて）
chmod 755 ~/Library/Application\ Support/PyDomino/soundfonts/
```

## 参考リンク

- [TimGM6mb.sf2 GitHub](https://github.com/musescore/MuseScore/tree/master/share/sound)
- [FluidR3_GM.sf2 配布サイト](https://member.keymusician.com/Member/FluidR3_GM/index.html)
- [SoundFont形式について](https://en.wikipedia.org/wiki/SoundFont)