"""
Diagnostic Script - Troubleshoot Config Imports

This script helps identify configuration import issues.

RUN FROM PROJECT ROOT:
    python diagnostic_check.py
"""
import sys
from pathlib import Path

print("="*80)
print("CONFIGURATION DIAGNOSTIC CHECK")
print("="*80)

# 1. Check Python version
print(f"\n1. Python Version: {sys.version}")
print(f"   Python Path: {sys.executable}")

# 2. Check current directory
print(f"\n2. Current Directory: {Path.cwd()}")

# 3. Check project structure
print("\n3. Project Structure Check:")
project_root = Path.cwd()

expected_files = [
    "config/__init__.py",
    "config/core_config.py",
    "config/soccer_config.py",
    "config/api_keys.py",
    "core/__init__.py",
    "core/models.py",
    "tests/test_config.py"
]

all_exist = True
for file_path in expected_files:
    full_path = project_root / file_path
    exists = full_path.exists()
    symbol = "✅" if exists else "❌"
    print(f"   {symbol} {file_path}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n   ⚠️  Some files are missing! Please ensure all files are in place.")
    sys.exit(1)

# 4. Check sys.path
print(f"\n4. sys.path includes:")
for p in sys.path[:5]:  # Show first 5
    print(f"   - {p}")

# 5. Try importing config package
print("\n5. Importing config package...")
try:
    import config
    print(f"   ✅ config package imported successfully")
    print(f"   Location: {config.__file__}")
except ImportError as e:
    print(f"   ❌ Failed to import config: {e}")
    sys.exit(1)

# 6. Check what's available in config
print("\n6. Available in config package:")
import config
available = dir(config)
expected_exports = [
    'API_KEYS',
    'validate_api_keys',
    'is_provider_configured',
    'get_api_config',
    'KellyConfig',
    'RiskConfig',
    'DEFAULT_KELLY_CONFIG',
    'DEFAULT_RISK_CONFIG',
    'SoccerConfig',
    'SUPPORTED_SOCCER_LEAGUES',
    'DEFAULT_SOCCER_CONFIG'
]

for item in expected_exports:
    if item in available:
        print(f"   ✅ {item}")
    else:
        print(f"   ❌ {item} - MISSING!")

# 7. Try importing each submodule
print("\n7. Submodule imports:")
submodules = [
    ('config.core_config', ['KellyConfig', 'RiskConfig']),
    ('config.soccer_config', ['SUPPORTED_SOCCER_LEAGUES', 'DEFAULT_SOCCER_CONFIG']),
    ('config.api_keys', ['API_KEYS', 'validate_api_keys'])
]

for module_name, expected_items in submodules:
    try:
        module = __import__(module_name, fromlist=expected_items)
        missing = [item for item in expected_items if not hasattr(module, item)]
        
        if missing:
            print(f"   ⚠️  {module_name} - missing: {', '.join(missing)}")
        else:
            print(f"   ✅ {module_name}")
    except ImportError as e:
        print(f"   ❌ {module_name} - {e}")

# 8. Check if there are .pyc files that might be stale
print("\n8. Checking for stale .pyc files...")
pyc_files = list(project_root.rglob("*.pyc"))
if pyc_files:
    print(f"   Found {len(pyc_files)} .pyc files")
    print("   Consider deleting __pycache__ directories:")
    print("   Windows: Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force")
    print("   Linux/Mac: find . -type d -name __pycache__ -exec rm -rf {} +")
else:
    print("   ✅ No .pyc files found")

# 9. Final test - Try the actual import from test_config.py
print("\n9. Final Import Test (as in test_config.py):")
try:
    from config import (
        DEFAULT_KELLY_CONFIG,
        DEFAULT_RISK_CONFIG,
        DEFAULT_SOCCER_CONFIG,
        SUPPORTED_SOCCER_LEAGUES,
        API_KEYS,
        validate_api_keys
    )
    print("   ✅ All imports successful!")
    
    # Run validation
    print("\n10. Running validate_api_keys():")
    validation = validate_api_keys()
    for provider, status in validation.items():
        configured = "✅" if status["configured"] else "❌"
        print(f"      {configured} {provider}")
    
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    print("\n   SOLUTION:")
    print("   1. Delete all __pycache__ directories")
    print("   2. Ensure you're running from project root")
    print("   3. Check that config/__init__.py has the correct exports")
    sys.exit(1)

print("\n" + "="*80)
print("✅ ALL DIAGNOSTIC CHECKS PASSED")
print("="*80)
print("\nYou should now be able to run: python -m tests.test_config")