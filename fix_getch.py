#!/usr/bin/env python3
"""
Script to fix all _getch() calls in C++ files for macOS compatibility
"""

import os
import re
from pathlib import Path

def fix_getch_in_file(file_path):
    """Fix _getch() calls in a single file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Replace _getch() calls with empty statements
        # This removes the interactive pauses but keeps the algorithms functional
        original_content = content

        # Pattern 1: _getch () ;  // Wait for user to press a key
        content = re.sub(r'\s*_getch\(\)\s*;\s*//\s*Wait for user to press a key', '   // User input removed for automated execution', content)

        # Pattern 2: _getch() ; (standalone)
        content = re.sub(r'\s*_getch\(\)\s*;', '   // User input removed for automated execution', content)

        # Pattern 3: _getch() calls in if statements
        content = re.sub(r'if\s*\(\s*_getch\(\)\s*==\s*27\s*\)', 'if (false)  // ESC key check removed', content)

        # Pattern 4: _kbhit() calls
        content = re.sub(r'if\s*\(\s*_kbhit\(\)\s*\)', 'if (false)  // Key press check removed', content)

        # Pattern 5: _getch() in error messages
        content = re.sub(r'printf\s*\(\s*"[^"]*Press any key[^"]*"\s*\)\s*;\s*_getch\(\)\s*;\s*exit\s*\(\s*1\s*\)\s*;',
                        'printf("\\n"); exit(1);', content)

        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_all_getch_calls():
    """Fix _getch() calls in all C++ files"""
    print("🔧 Fixing _getch() calls for macOS compatibility...")

    cpp_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.CPP') or file.endswith('.cpp'):
                cpp_files.append(os.path.join(root, file))

    fixed_count = 0
    for cpp_file in cpp_files:
        if fix_getch_in_file(cpp_file):
            print(f"   ✅ Fixed: {cpp_file}")
            fixed_count += 1
        else:
            print(f"   - No changes: {cpp_file}")

    print(f"\n✅ Fixed _getch() calls in {fixed_count} files")
    return fixed_count

if __name__ == "__main__":
    fix_all_getch_calls()
