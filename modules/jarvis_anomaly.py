"""
JARVIS Predictive Anomaly Detection
Uses IsolationForest to learn normal system patterns and alert on anomalies.
"""
import os
import sqlite3
import logging
import psutil
import requests
from dotenv import load_dotenv

try:
    from sklearn.ensemble import IsolationForest
    # pyrefly: ignore [missing-import]
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "memory_core.db")
logger = logging.getLogger("JarvisAnomaly")

def init_anomaly_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telemetry_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_percent REAL,
                    ram_percent REAL
                )
            ''')
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to init anomaly DB: {e}")

init_anomaly_db()

def log_telemetry():
    """Logs current telemetry to DB. Returns (cpu, ram)"""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO telemetry_history (cpu_percent, ram_percent) VALUES (?, ?)', (cpu, ram))
            
            cursor.execute('DELETE FROM telemetry_history WHERE id NOT IN (SELECT id FROM telemetry_history ORDER BY id DESC LIMIT 1000)')
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log telemetry: {e}")
    return cpu, ram

def check_anomaly() -> str:
    """
    Trains on recent data and predicts if current state is anomalous.
    Returns warning string if anomalous, else empty string.
    """
    if not ML_AVAILABLE:
        return ""
        
    cpu, ram = log_telemetry()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT cpu_percent, ram_percent FROM telemetry_history ORDER BY id ASC')
            data = cursor.fetchall()
            
        if len(data) < 20:
            return "" 
            
        X = np.array(data)  # type: ignore
        
        clf = IsolationForest(contamination=0.05, random_state=42)  # type: ignore
        clf.fit(X)
        
        current_X = np.array([[cpu, ram]])  # type: ignore
        prediction = clf.predict(current_X)
        
        if prediction[0] == -1:
            alert_msg = f"🚨 [ANOMALY DETECTED]: CPU: {cpu}% | RAM: {ram}%. พฤติกรรมระบบผิดปกติจากค่าเฉลี่ยที่เรียนรู้ไว้!"
            
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                load_dotenv(os.path.join(base_dir, ".env"))
                line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
                line_user_id = os.getenv("LINE_USER_ID")
                if line_token and line_user_id:
                    url = "https://api.line.me/v2/bot/message/push"
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {line_token}"
                    }
                    data = {
                        "to": line_user_id,
                        "messages": [{"type": "text", "text": alert_msg}]
                    }
                    requests.post(url, headers=headers, json=data, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send anomaly LINE alert: {e}")
                
            return alert_msg
        return ""
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        return ""
