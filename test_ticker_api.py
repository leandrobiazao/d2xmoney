"""
Test script for ticker mappings API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/ticker-mappings"

def test_get_all_mappings():
    """Test GET /api/ticker-mappings/"""
    print("=" * 60)
    print("TEST 1: GET all ticker mappings")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {len(data)} mappings")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_mapping(nome, ticker):
    """Test POST /api/ticker-mappings/"""
    print("\n" + "=" * 60)
    print(f"TEST 2: POST create mapping ({nome} -> {ticker})")
    print("=" * 60)
    try:
        payload = {
            "nome": nome,
            "ticker": ticker
        }
        response = requests.post(f"{BASE_URL}/", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 201:
            print("✅ Success! Mapping created")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_specific_mapping(nome):
    """Test GET /api/ticker-mappings/<nome>"""
    print("\n" + "=" * 60)
    print(f"TEST 3: GET specific mapping for '{nome}'")
    print("=" * 60)
    try:
        # URL encode the nome
        import urllib.parse
        encoded_nome = urllib.parse.quote(nome)
        response = requests.get(f"{BASE_URL}/{encoded_nome}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 200:
            print("✅ Success! Mapping found")
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_file_exists():
    """Check if ticker.json file exists"""
    print("\n" + "=" * 60)
    print("TEST 4: Check if ticker.json file exists")
    print("=" * 60)
    import os
    from pathlib import Path
    
    file_path = Path("backend/data/ticker.json")
    if file_path.exists():
        print(f"✅ File exists at: {file_path.absolute()}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ File contains {len(data)} mappings:")
            print(json.dumps(data, indent=2))
            return True
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False
    else:
        print(f"❌ File does not exist at: {file_path.absolute()}")
        return False

if __name__ == "__main__":
    print("\n🧪 Testing Ticker Mappings API\n")
    
    # Test 1: Get all mappings (should be empty initially)
    test1 = test_get_all_mappings()
    
    # Test 2: Create a mapping
    test2 = test_create_mapping("PETROBRAS ON NM", "PETR4")
    
    # Check if file was created
    test4 = check_file_exists()
    
    # Test 3: Get all mappings again (should have 1 now)
    test1b = test_get_all_mappings()
    
    # Test 4: Get specific mapping
    test3 = test_get_specific_mapping("PETROBRAS ON NM")
    
    # Test 5: Create another mapping
    test5 = test_create_mapping("VALE ON NM", "VALE3")
    
    # Check file again
    test4b = check_file_exists()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"GET all (initial): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"POST create (PETR4): {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"File created: {'✅ PASS' if test4 else '❌ FAIL'}")
    print(f"GET all (after): {'✅ PASS' if test1b else '❌ FAIL'}")
    print(f"GET specific: {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"POST create (VALE3): {'✅ PASS' if test5 else '❌ FAIL'}")
    print(f"File updated: {'✅ PASS' if test4b else '❌ FAIL'}")
    
    if all([test1, test2, test4, test1b, test3, test5, test4b]):
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check the output above.")
        sys.exit(1)

