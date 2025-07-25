# 🎹 MIDI設定ガイド - DAWとの連携方法

DominoPyとDAW（Logic Pro、Ableton Live、Cubase、FL Studio、Studio One等）を連携させる方法を説明します。

## 📋 目次
- [MIDIルーティングの仕組み](#midiルーティングの仕組み)
- [基本的なMIDI設定](#基本的なmidi設定)
- [macOSでのDAW連携](#macosでのdaw連携)
- [Windows・Linux対応](#windowslinux対応)
- [トラブルシューティング](#トラブルシューティング)

---

## 🔄 MIDIルーティングの仕組み

### 基本的なデータフロー
```
┌─────────────┐    MIDI    ┌─────────────┐    Audio    ┌─────────────┐
│  DominoPy   │ ────────▶ │     DAW     │ ────────▶ │  スピーカー   │
│  (作曲)     │           │  (音源)     │           │            │
└─────────────┘           └─────────────┘           └─────────────┘
```

### 詳細なMIDIルーティング
```
DominoPy                    仮想MIDIドライバー          DAW
┌─────────────────┐        ┌──────────────┐        ┌──────────────────┐
│  🎹 Piano Roll  │        │              │        │  🎵 Track 1      │
│  🎛️ Virtual KB  │ ──────▶│ IAC Driver   │──────▶ │  🎺 Track 2      │
│  📝 Note Input  │        │   Bus 1-17   │        │  🥁 Track 3      │
└─────────────────┘        └──────────────┘        └──────────────────┘
                                  │
                           ┌──────────────┐
                           │ MIDI Router  │
                           │ (DominoPy)   │
                           └──────────────┘
                                  │
                           ┌──────────────┐
                           │ FluidSynth   │ ──▶ 🔊 Internal Audio
                           │ (Built-in)   │
                           └──────────────┘
```

### 設定パターン比較
```
パターン1: 内蔵音源のみ
DominoPy ──▶ FluidSynth ──▶ 🔊

パターン2: DAW音源のみ  
DominoPy ──▶ 仮想MIDI ──▶ DAW ──▶ 🔊

パターン3: ハイブリッド (推奨)
DominoPy ──┬▶ FluidSynth ──┬▶ 🔊
           └▶ 仮想MIDI ──▶ DAW ──┘
```

---

## 🔧 基本的なMIDI設定

### 1. MIDI出力設定を開く
1. DominoPyを起動
2. メニューバー **Audio** → **MIDI Routing...** をクリック
3. MIDI Output Settings ダイアログが開きます

### 2. 出力先の選択
**Primary Output** で以下から選択：
- **🔊 Internal FluidSynth (Built-in)** - DominoPy内蔵音源
- **🎹 IAC Driver (Virtual MIDI)** - DAWとの連携用（macOS）
- **🎹 その他の仮想MIDIドライバー** - Windows/Linux

### 3. ルーティング設定
✅ **Enable External MIDI Routing** - DAWに信号を送信  
✅ **Keep Internal Audio (FluidSynth)** - 内蔵音源も同時使用

---

## 🍎 macOSでのDAW連携

> **📝 対応DAW:** Logic Pro、Ableton Live、Cubase、FL Studio、Studio One、Reaper、Pro Tools、GarageBand等、MIDI入力をサポートする全てのDAWで使用可能です。

### Step 1: IAC Driverを有効化（macOS標準機能）

#### IAC Driverの設定
1. **Audio MIDI Setup** アプリを開く（Applications > Utilities）
2. **Window** → **Show MIDI Studio** をクリック
3. **IAC Driver** をダブルクリック
4. ✅ **Device is online** にチェック
5. **Ports** タブで **Bus 1** が有効になっていることを確認

```
Audio MIDI Setup
┌─────────────────────────────────────┐
│ ☐ IAC Driver                        │ ← これをダブルクリック
│   └─ ☐ Bus 1                        │
│   └─ ☐ Bus 2                        │
└─────────────────────────────────────┘
                ⬇
┌─────────────────────────────────────┐
│ ✅ Device is online                 │ ← チェックを入れる
│                                     │
│ Ports: [Bus 1] [Bus 2] ...         │
└─────────────────────────────────────┘
```

### Step 2: DominoPy側設定
1. **Audio** → **MIDI Routing...** を開く
2. **Primary Output**: **IAC Driver (Virtual MIDI)** を選択
3. ✅ **Enable External MIDI Routing** をチェック
4. **Apply** をクリック

### Step 3: DAW別設定例

#### Logic Pro の場合
1. 新しいプロジェクトを作成
2. **Software Instrument** トラックを追加
3. 好きな音源（Sculpture、Vintage Electric Pianos等）をロード
4. トラックの **入力** を **IAC Driver Bus 1** に設定
5. 🔴 **Record Enable** ボタンを押す

#### Ableton Live の場合
1. **Preferences** → **MIDI** タブを開く
2. **Input** セクションで **IAC Driver Bus 1** を **On** にする
3. 新しい **MIDI Track** を作成
4. **MIDI From** を **IAC Driver Bus 1** に設定
5. 好きな音源をロード & 🔴 **Arm** ボタンを押す

#### その他のDAW（共通手順）
1. **MIDI入力設定** で **IAC Driver Bus 1** を有効化
2. **MIDIトラック** の入力を **IAC Driver Bus 1** に設定
3. **音源** をロード
4. **録音可能状態** にする

---

## 🖥️ Windows・Linux対応

基本的なMIDI概念は同じですが、仮想MIDIドライバーの設定方法が異なります：

### Windows
**必要なソフトウェア:**
- **loopMIDI** (推奨) - 無料の仮想MIDIドライバー
- **MIDI Yoke** - クラシックな選択肢
- **Virtual MIDI Piano Keyboard** - オープンソース

**基本的な流れ:**
1. 仮想MIDIドライバーをインストール・設定
2. DominoPy: Primary Outputを仮想MIDIポートに設定
3. DAW: MIDI入力を同じ仮想MIDIポートに設定

### Linux
**必要な設定:**
- **ALSA Sequencer** - 標準MIDI システム
- **Jack** - プロオーディオ環境
- **a2jmidid** - ALSA-Jack ブリッジ

**基本的な流れ:**
1. ALSA/Jackで仮想MIDIポートを作成
2. DominoPy: Primary Outputを仮想ポートに設定
3. DAW: MIDI入力を同じポートに設定

> 📝 **コミュニティ募集中**: Windows/Linux環境での詳細手順をご存知の方は、
> [GitHub Issues](https://github.com/sharuru3501/pydomino/issues) で
> 情報共有をお願いします！具体的な手順やスクリーンショットなど、
> ユーザー同士で助け合いましょう。

---

## 🎚️ 複数トラック・音源管理

### トラック別音源設定の例
```
┌─────────────────────────────────────────────────────────────────┐
│                     DominoPy Tracks                            │
├─────────────┬───────────────────┬───────────────────────────────┤
│ Track 00    │ Internal FluidSynth │ 🎹 ピアノ (低レイテンシ)        │
│ Track 01    │ IAC Driver Bus 1    │ 🥁 Logic Pro - ドラム          │
│ Track 02    │ IAC Driver Bus 2    │ 🎸 Ableton - ベース           │
│ Track 03    │ Soundfont (.sf2)    │ 🎮 チップチューン音源           │
├─────────────┴───────────────────┴───────────────────────────────┤
│                        ⬇ MIDI データ                            │
├─────────────────────────────────────────────────────────────────┤
│                         DAW                                     │
├─────────────┬───────────────────┬───────────────────────────────┤
│ MIDI Track 1│ IAC Driver Bus 1    │ 🥁 Battery/Addictive Drums     │
│ MIDI Track 2│ IAC Driver Bus 2    │ 🎸 Bass Amp/Trilian           │
│ Audio Track │ Record from DominoPy│ 🎤 Live Recording             │
└─────────────┴───────────────────┴───────────────────────────────┘
                        ⬇
                    🔊 Final Audio Output
```

### 設定方法
1. **トラックリスト** で設定したいトラックを選択
2. **Audio Source** をクリック
3. 以下から選択：
   - **Internal FluidSynth** - 内蔵音源
   - **IAC Driver Bus 1-17** - 各DAWトラックに対応
   - **Soundfont (.sf2)** - カスタム音源

---

## 🔍 トラブルシューティング

### 問題: DAWで音が鳴らない
**確認チェックリスト:**
- ✅ 仮想MIDIドライバーが有効になっているか
- ✅ DominoPy: Enable External MIDI Routing がON
- ✅ DAW: MIDI入力が正しい仮想ポートに設定されているか
- ✅ DAW: トラックが録音可能状態になっているか

### 問題: 音が重複して聞こえる
**原因:** 内蔵音源とDAW音源が同時に鳴っている
```
DominoPy (FluidSynth) ──┬▶ 🔊 ピアノ音
                       │
仮想MIDI ──▶ DAW ──────┘▶ 🔊 DAW音源
                         = 🔊🔊 重複!
```
**解決方法:** 
- DominoPy: **Keep Internal Audio** をOFF にする
- または DAW側の音源をミュート

### 問題: 音が鳴り続ける
**原因:** Note Offメッセージが送信されていない
**解決方法:**
1. DominoPyを再起動
2. DAW側で **All Notes Off** を実行（通常 Cmd+Shift+. など）

### 問題: 仮想キーボードで外部音源が鳴らない
**確認事項:**
- ✅ アクティブトラックのAudio SourceがIAC Driver Bus Xに設定されているか
- ✅ Enable External MIDI Routing がON になっているか

---

## 💡 実用的な使い方

### 1. ハイブリッド構成（推奨）
```
┌─────────────────────────────────────────────────────────────┐
│  メインメロディー: DAWの高品質音源 (Kontakt、Omnisphere等)     │
│  ドラム・ベース: 内蔵FluidSynth (低レイテンシ)               │  
│  エフェクト音: Soundfont (.sf2)                            │
└─────────────────────────────────────────────────────────────┘
```

### 2. レコーディングワークフロー
```
作曲フェーズ:  DominoPy (高速編集)
  ⬇
アレンジフェーズ: DominoPy → DAW (MIDI録音)
  ⬇  
ミックスフェーズ: DAW (最終調整)
```

### 3. ライブ演奏
- **仮想キーボード** + 外部MIDI音源
- **リアルタイム演奏** が可能
- **複数のDAW** を同時使用可能

### 4. 楽器別最適化
```
🎹 ピアノ → Logic Pro (高品質ピアノ音源)
🥁 ドラム → 内蔵FluidSynth (低レイテンシ)
🎸 ギター → Ableton Live (アンプシミュレーター)
🎻 ストリングス → Cubase (オーケストラ音源)
```

---

## 🎉 まとめ

これでDominoPyとあらゆるDAWの完璧な連携ができました！

**対応環境:**
- ✅ **macOS**: IAC Driver（標準機能）
- ✅ **Windows**: loopMIDI等（要インストール）
- ✅ **Linux**: ALSA/Jack（要設定）

**対応DAW:** Logic Pro、Ableton Live、Cubase、FL Studio、Studio One、Reaper、Pro Tools、GarageBand、Reason、Bitwig Studio など

---

## 🤝 コミュニティサポート

**質問・情報共有:**
- [GitHub Issues](https://github.com/sharuru3501/pydomino/issues) - 質問・バグ報告
- [GitHub Discussions](https://github.com/sharuru3501/pydomino/discussions) - 一般的な議論

**貢献をお待ちしています:**
- Windows/Linux詳細手順の投稿
- 新しいDAW対応情報
- トラブルシューティング事例

一緒にDominoPyをより良いソフトウェアにしていきましょう！