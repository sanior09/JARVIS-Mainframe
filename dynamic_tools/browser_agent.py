import json
from playwright.sync_api import sync_playwright

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "universal_browser_agent",
        "description": "ควบคุมเว็บบราวเซอร์แบบ Headless (Playwright) รองรับ JavaScript, การล็อกอิน, และดึงข้อมูลแบบไดนามิกได้อย่างแม่นยำ",
        "parameters": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "description": "รายการของ Action ที่ต้องการให้ทำเรียงตามลำดับ เช่น [{'action': 'goto', 'url': 'https://google.com'}, {'action': 'fill', 'selector': 'input[name=\"q\"]', 'text': 'jarvis'}, {'action': 'click', 'selector': 'input[name=\"btnK\"]'}, {'action': 'extract_text', 'selector': 'body'}]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["goto", "click", "fill", "extract_text", "screenshot"]},
                            "url": {"type": "string"},
                            "selector": {"type": "string"},
                            "text": {"type": "string"}
                        },
                        "required": ["action"]
                    }
                }
            },
            "required": ["actions"]
        }
    }
}

def universal_browser_agent(args: dict) -> str:
    actions = args.get("actions", [])
    if not actions:
        return "ไม่มีคำสั่ง (actions) ส่งมาให้"
        
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            for step in actions:
                action = step.get("action")
                try:
                    if action == "goto":
                        page.goto(step.get("url", ""), timeout=30000)
                        results.append(f"Navigated to {step.get('url')}")
                    elif action == "click":
                        page.click(step.get("selector", ""), timeout=15000)
                        results.append(f"Clicked {step.get('selector')}")
                    elif action == "fill":
                        page.fill(step.get("selector", ""), step.get("text", ""), timeout=15000)
                        results.append(f"Filled {step.get('selector')}")
                    elif action == "extract_text":
                        # Wait a bit for dynamic content
                        page.wait_for_timeout(2000)
                        content = page.locator(step.get("selector", "body")).inner_text()
                        # limit content length to prevent huge context
                        content = content[:4000] + ("..." if len(content) > 4000 else "")
                        results.append(f"Extracted Text:\n{content}")
                    elif action == "screenshot":
                        # In a real scenario we could save it to disk and return the path
                        path = "screenshot_browser.png"
                        page.screenshot(path=path)
                        results.append(f"Screenshot saved to {path}")
                except Exception as ex:
                    results.append(f"Error on action '{action}': {str(ex)}")
                    break # Stop executing further actions if one fails
                    
            browser.close()
            return "\n".join(results)
            
    except Exception as e:
        return f"Browser Error: {e}"
