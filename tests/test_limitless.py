import sys
import json
import os

# Add JARVIS to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dynamic_tools.code_interpreter import code_interpreter
from dynamic_tools.browser_agent import universal_browser_agent
from dynamic_tools.api_composer import universal_api_composer

def run_tests():
    print("=== 1. Testing Code Interpreter ===")
    code = "import math\nprint(f'PI is approximately {math.pi}')\n"
    res1 = code_interpreter({"code": code})
    print(res1)
    
    print("\n=== 2. Testing Universal Browser Agent ===")
    res2 = universal_browser_agent({
        "actions": [
            {"action": "goto", "url": "https://example.com"},
            {"action": "extract_text", "selector": "h1"}
        ]
    })
    print(res2)
    
    print("\n=== 3. Testing Universal API Composer ===")
    res3 = universal_api_composer({
        "method": "GET",
        "url": "https://httpbin.org/get",
        "query_params": {"test": "jarvis"}
    })
    
    try:
        data = json.loads(res3)
        print(f"Status Code: {data.get('status_code')}")
        print(f"Response: {json.dumps(data.get('response_body', {}).get('args'), indent=2)}")
    except Exception as e:
        print(f"Error parsing API response: {e}\nRaw: {res3}")

if __name__ == "__main__":
    run_tests()
