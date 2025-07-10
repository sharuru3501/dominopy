# PyDomino クラッシュ修正履歴

## 2025-07-10 20:45:10 - QtGUI Segmentation Fault

### 症状
- `QPaintDevice::devicePixelRatio()` で null pointer 参照
- セグメンテーションフォルト（SIGSEGV）
- QtのGUI描画処理中にクラッシュ

### 原因分析
設定変更時の音楽情報ウィジェット強制更新処理で、ウィジェットの状態チェックが不十分だった可能性。

### 修正内容

1. **main_window.py の _on_settings_applied() メソッド**
   - try-except文で例外処理を追加
   - hasattr()でオブジェクトの存在チェックを強化
   - None チェックを追加

2. **piano_roll_widget.py のズーム関数**
   - _zoom_horizontal() と _zoom_vertical() に例外処理を追加
   - isVisible() チェックを追加してからupdate()を呼び出し
   - エラーログとトレースバック出力を追加

### 修正後の安全性対策
- オブジェクトの存在確認
- ウィジェットの表示状態確認
- 例外キャッチとログ出力
- Fallback処理の実装

### 予防策
- GUI関連の処理は常にオブジェクトの存在確認を行う
- update()呼び出し前にはisVisible()チェックを行う
- 設定変更時の強制更新は最小限に留める

### 関連する修正ファイル
- `/src/ui/main_window.py`
- `/src/ui/piano_roll_widget.py`