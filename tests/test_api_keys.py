# test_api_keys.py (temporal, para validar)

"""
Quick test for API keys configuration

Run this after creating config/api_keys.py:
    python test_api_keys.py
"""

print("Testing API keys configuration...\n")

try:
    from config.api_keys import (
        validate_api_keys,
        is_provider_configured,
        get_api_config,
        print_configuration_status
    )
    print("✅ Import successful\n")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nMake sure you've created config/api_keys.py")
    print("You can copy from template:")
    print("    cp config/api_keys.template.py config/api_keys.py")
    exit(1)

# Print full status
print_configuration_status()

# Try to get config (will fail if keys not set, which is OK)
print("\n" + "="*70)
print("Testing get_api_config()...")
print("="*70)

for provider in ["api_football", "odds_api"]:
    try:
        config = get_api_config(provider)
        print(f"\n✅ {provider}: Configuration valid")
        print(f"   Base URL: {config['base_url']}")
        print(f"   Rate limit: {config['rate_limit']} req/min")
    except ValueError as e:
        print(f"\n⚠️  {provider}: {e}")
        print(f"   This is expected if you haven't set your API key yet.")

print("\n" + "="*70)
print("\nNext steps:")
print("1. Get API keys from:")
print("   - https://www.football-data.org/client/register")
print("   - https://the-odds-api.com/")
print("2. Edit config/api_keys.py and replace 'YOUR_KEY_HERE'")
print("3. Run this test again to verify")
print("="*70)