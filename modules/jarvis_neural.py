

import logging
import numpy as np
import time
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger("JarvisNeural")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [NEURAL] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

class NeuralRiskEngine:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.is_trained = False
        self._train_model()

    def _train_model(self):
        """
        Generate synthetic historical data simulating Lenovo IdeaPad S340 workloads.
        Features: [CPU %, RAM %, Disk %]
        Labels: 
        0 = SAFE (Normal Load)
        1 = WARNING (Heavy Load, but stable)
        2 = CRITICAL (Overload / Swap Thrashing)
        """
        logger.info("Initializing Cognitive Matrix... Training Neural Risk Model.")
        start_time = time.time()
        
        X_train = []
        y_train = []
        
        for _ in range(300):
            cpu = np.random.uniform(5, 40)
            ram = np.random.uniform(30, 60)
            disk = np.random.uniform(10, 50)
            X_train.append([cpu, ram, disk])
            y_train.append(0)

        for _ in range(200):
            cpu = np.random.uniform(60, 95)
            ram = np.random.uniform(65, 85)
            disk = np.random.uniform(50, 80)
            X_train.append([cpu, ram, disk])
            y_train.append(1)

        for _ in range(100):
            cpu = np.random.uniform(90, 100)
            ram = np.random.uniform(90, 99)
            disk = np.random.uniform(80, 99)
            X_train.append([cpu, ram, disk])
            y_train.append(2)

        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        elapsed = time.time() - start_time
        logger.info(f"Neural Matrix Trained Successfully in {elapsed:.3f}s. Accuracy baseline established.")

    def predict_risk(self, cpu: float, ram: float, disk: float) -> dict:
        """
        Predict the risk level based on current telemetry.
        Returns a dictionary with status, risk percentage, and recommendation.
        """
        if not self.is_trained:
            return {"status": "UNKNOWN", "risk_percent": 0, "message": "Neural Engine Offline"}

        features = np.array([[cpu, ram, disk]])
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        
        risk_score = (probabilities[1] * 50) + (probabilities[2] * 100)
        risk_score = min(max(risk_score, 0), 100) 

        status_map = {0: "SAFE", 1: "WARNING", 2: "CRITICAL"}
        status = status_map[prediction]

        message = "ระบบทำงานในสภาวะปกติครับเจ้านาย"
        if status == "WARNING":
            message = "พบโหลดการทำงานสูง (Warning) แนะนำให้ปิดโปรแกรมที่ไม่ได้ใช้งานเพื่อประหยัดทรัพยากรครับ"
        elif status == "CRITICAL":
            message = "อันตราย! ระบบประเมินความเสี่ยงระดับ CRITICAL! การใช้ทรัพยากรพุ่งสูงเกินขีดจำกัด อาจทำให้ระบบล่มหรือจอฟ้าได้ครับ!"

        return {
            "status": status,
            "risk_percent": round(risk_score, 1),
            "message": message,
            "telemetry_used": {"cpu": cpu, "ram": ram, "disk": disk}
        }

_engine = None

def predict_system_failure(cpu: float = 0.0, ram: float = 0.0, disk: float = 0.0, *args, **kwargs) -> float:
    """
    Predict system failure risk (0.0 to 1.0) using NeuralRiskEngine with graceful fallback.
    Never returns None.
    """
    global _engine
    try:
        c = float(cpu) if cpu is not None else 0.0
        r = float(ram) if ram is not None else 0.0
        d = float(disk) if disk is not None else 0.0
        if _engine is None:
            _engine = NeuralRiskEngine()
        result = _engine.predict_risk(c, r, d)
        risk = float(result.get("risk_percent", 0.0)) / 100.0
        return max(0.0, min(1.0, risk))
    except Exception as e:
        logger.error(f"Error in predict_system_failure: {e}")
        try:
            c = float(cpu) if cpu is not None else 0.0
            r = float(ram) if ram is not None else 0.0
            d = float(disk) if disk is not None else 0.0
            heuristic_risk = (max(0.0, c - 70) * 0.4 + max(0.0, r - 80) * 0.4 + max(0.0, d - 85) * 0.2) / 30.0
            return max(0.0, min(1.0, float(heuristic_risk)))
        except Exception:
            return 0.0

def build_and_train_matrix(X_real=None, y_real=None):
    """
    Active learning retraining hook for telemetry data.
    """
    global _engine
    try:
        if _engine is None:
            _engine = NeuralRiskEngine()
        if X_real is not None and y_real is not None and len(X_real) > 0:
            import numpy as np
            X_arr = np.array(X_real)
            if len(X_arr.shape) > 1 and X_arr.shape[1] > 3:
                X_arr = X_arr[:, :3]
            y_arr = np.array(y_real)
            _engine.model.fit(X_arr, y_arr)
            _engine.is_trained = True
            logger.info(f"Neural matrix successfully updated with {len(X_arr)} records.")
    except Exception as e:
        logger.error(f"Failed to update neural matrix: {e}")

