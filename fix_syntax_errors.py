#!/usr/bin/env python3
"""
Syntax error fixer for PyDomino files
"""
import re

def fix_syntax_errors(file_path):
    """Fix common syntax errors from automated cleanup"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix indentation issues
    fixes = [
        # Remove orphaned else statements
        (r'\n\s+else:\s*\n\s+(\w)', r'\n        \1'),
        # Fix orphaned exception handlers  
        (r'\n\s+except Exception as e:\s*\n\s*\n', r'\n                except Exception as e:\n                    pass\n'),
        # Fix orphaned lines with excessive indentation
        (r'\n\s{20,}(\w)', r'\n            \1'),
        # Remove orphaned comment lines
        (r'\n\s+#.*?\n\s*\n', r'\n\n'),
        # Clean up multiple empty lines
        (r'\n\s*\n\s*\n\s*\n', r'\n\n'),
        # Fix orphaned return statements
        (r'\n\s{20,}return', r'\n            return'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    file_path = "/Users/shinnosuke/dev/pydominodev/src/ui/piano_roll_widget.py"
    fix_syntax_errors(file_path)
    print("✅ Syntax errors fixed")