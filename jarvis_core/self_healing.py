import logging
import traceback
from functools import wraps

logger = logging.getLogger("JarvisSelfHealing")

def jarvis_self_heal(func):
    """
    3. Autonomous Self-Healing Subroutine
    A decorator that catches unhandled exceptions, prevents system crashes,
    and logs the stack trace for the ASI to analyze and self-patch later.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[SELF-HEALING] Intercepted crash in '{func.__name__}': {e}")
            logger.debug(f"Traceback:\n{error_details}")
            
            # In a full ASI, this would trigger LLM to rewrite the function's AST.
            # For now, it isolates the failure and returns a safe fallback.
            fallback_response = f"⚠️ [SYSTEM] ตรวจพบข้อผิดพลาดในสับรูทีน '{func.__name__}' แต่ระบบ Self-Healing ได้ทำการระงับความเสียหายไว้แล้วครับ"
            
            # Return empty/safe defaults depending on expected return type
            if "dict" in str(func.__annotations__.get("return", "")):
                return {"error": str(e), "message": fallback_response}
            return fallback_response
    return wrapper
