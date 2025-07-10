#!/usr/bin/env python3
"""
PyDomino 軽量化とメモリ最適化チェック
"""
import os
import re

def remove_debug_prints(file_path):
    """DEBUGプリント文を削除"""
    if not os.path.exists(file_path):
        return 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # DEBUG print文のパターンを削除
    patterns = [
        r'print\(f?"DEBUG:.*?\).*?# DEBUG\n',  # DEBUG comment付き
        r'print\(f?"DEBUG:.*?\)\n',           # DEBUG: で始まる
        r'print\(f?".*DEBUG.*?\)\n',          # DEBUG含む
    ]
    
    original_count = content.count('print(')
    
    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    # 空の行の削除（複数連続する空行を1つに）
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    new_count = content.count('print(')
    removed = original_count - new_count
    
    return removed

def main():
    """メイン関数"""
    files_to_optimize = [
        'src/ui/piano_roll_widget.py',
        'src/ui/main_window.py',
        'src/playback_engine.py',
        'src/audio_system.py',
        'src/music_theory.py',
    ]
    
    total_removed = 0
    
    for file_path in files_to_optimize:
        full_path = f'/Users/shinnosuke/dev/pydominodev/{file_path}'
        removed = remove_debug_prints(full_path)
        if removed > 0:
            print(f"✅ {file_path}: {removed} debug prints removed")
            total_removed += removed
        else:
            print(f"ℹ️  {file_path}: No debug prints found")
    
    print(f"\n🎯 Total: {total_removed} debug prints removed")
    print("\n📊 Memory optimization recommendations:")
    print("• Removed verbose debug output")
    print("• Reduced string formatting overhead")  
    print("• Cleaned up redundant logging")
    
    if total_removed > 50:
        print("• ⚠️  Consider using a proper logging framework for future debug needs")

if __name__ == "__main__":
    main()