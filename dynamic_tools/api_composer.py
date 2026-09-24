import requests
import json

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "universal_api_composer",
        "description": "ใช้สำหรับเชื่อมต่อและยิง REST API ไปยังบริการใดๆ ในโลก (เช่น Notion, Slack, LINE, ฯลฯ) โดยส่ง Method, URL, Headers และ Payload",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP Method (GET, POST, PUT, DELETE, PATCH)"
                },
                "url": {
                    "type": "string",
                    "description": "URL ของ API Endpoint"
                },
                "headers": {
                    "type": "object",
                    "description": "JSON object สำหรับ HTTP Headers (เช่น Authorization, Content-Type)"
                },
                "payload": {
                    "type": "object",
                    "description": "JSON object สำหรับ Request Body (ถ้ามี)"
                },
                "query_params": {
                    "type": "object",
                    "description": "JSON object สำหรับ Query Parameters (ถ้ามี)"
                }
            },
            "required": ["method", "url"]
        }
    }
}

def universal_api_composer(args: dict) -> str:
    method = args.get("method", "GET").upper()
    url = args.get("url", "")
    headers = args.get("headers", {})
    payload = args.get("payload", None)
    query_params = args.get("query_params", None)
    
    if not url:
        return "Error: URL is required"
        
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload if payload else None,
            params=query_params,
            timeout=30
        )
        
        result = {
            "status_code": response.status_code,
            "reason": response.reason,
            "elapsed_seconds": response.elapsed.total_seconds(),
        }
        
        try:
            result["response_body"] = response.json()
        except ValueError:
            # Not JSON
            text = response.text
            result["response_body"] = text[:2000] + ("..." if len(text) > 2000 else "")
            
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except requests.exceptions.RequestException as e:
        return f"API Request Failed: {str(e)}"
