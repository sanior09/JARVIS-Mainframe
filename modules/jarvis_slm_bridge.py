"""
modules/jarvis_slm_bridge.py
===========================
J.A.R.V.I.S. <-> JarvisCore Neural SLM & Endocrine Bridge.
Connects the local PyTorch Small Language Model (model_ckpt.pt)
and Synthetic Endocrine Subsystem from C:\\JarvisCore into the main J.A.R.V.I.S. architecture.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("JarvisCoreBridge")

_local_core = Path(__file__).resolve().parent.parent / "models" / "jarvis_core"
JARVIS_CORE_DIR = Path(os.getenv("JARVIS_CORE_DIR", str(_local_core if _local_core.exists() else Path(r"C:\JarvisCore"))))
CHECKPOINT_PATH = JARVIS_CORE_DIR / "model_ckpt.pt"


class JarvisCoreBridge:
    """
    Singleton bridge to interface with C:\\JarvisCore.
    Provides sub-second local reflex inference and real-time endocrine state synchronization.
    """

    _instance: Optional["JarvisCoreBridge"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.is_loaded = False
        self.device = "cpu"
        self.model: Any = None
        self.tokenizer: Any = None
        self.block_size = 128
        self.vocab_size = 0
        self.endocrine_system: Any = None
        self._init_error: Optional[str] = None
        self._load_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "JarvisCoreBridge":
        with cls._lock:
            if cls._instance is None:
                cls._instance = JarvisCoreBridge()
            return cls._instance

    def initialize(self) -> bool:
        """Loads model checkpoint and tokenizer into memory with fail-safe isolation."""
        with self._load_lock:
            if self.is_loaded:
                return True

            if not JARVIS_CORE_DIR.exists() or not CHECKPOINT_PATH.exists():
                self._init_error = f"JarvisCore path or checkpoint not found at {CHECKPOINT_PATH}"
                logger.warning(f"[JARVIS-CORE BRIDGE] {self._init_error}")
                return False

            try:
                # Add C:\JarvisCore to Python module search path
                core_path_str = str(JARVIS_CORE_DIR)
                if core_path_str not in sys.path:
                    sys.path.insert(0, core_path_str)

                import torch
                from brain.model import JarvisLanguageModel
                from brain.tokenizer import CharacterTokenizer

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"[JARVIS-CORE BRIDGE] Loading model_ckpt.pt onto {self.device}...")

                checkpoint = torch.load(str(CHECKPOINT_PATH), map_location=self.device, weights_only=True)

                chars: list[str] = checkpoint.get("chars", [])
                if not chars:
                    raise ValueError("Checkpoint does not contain vocabulary 'chars'")

                self.tokenizer = CharacterTokenizer()
                self.tokenizer.chars = chars
                self.tokenizer.vocab_size = len(chars)
                self.tokenizer.stoi = {ch: i for i, ch in enumerate(chars)}
                self.tokenizer.itos = {i: ch for i, ch in enumerate(chars)}
                self.vocab_size = len(chars)

                config = checkpoint.get("config", {})
                self.block_size = config.get("block_size", 256)
                n_embd = config.get("n_embd", 256)
                n_head = config.get("n_head", 4)
                n_layer = config.get("n_layer", 4)

                # Initialize Model Architecture matching checkpoint
                self.model = JarvisLanguageModel(
                    vocab_size=self.vocab_size,
                    n_embd=n_embd,
                    n_head=n_head,
                    n_layer=n_layer,
                    block_size=self.block_size,
                    dropout=0.15,
                )

                self.model.load_state_dict(checkpoint["model_state_dict"])
                self.model.to(self.device)
                self.model.eval()

                self.is_loaded = True
                self._init_error = None
                logger.info(
                    f"[JARVIS-CORE BRIDGE] Model loaded successfully! "
                    f"(Vocab: {self.vocab_size}, Device: {self.device}, Checkpoint: {CHECKPOINT_PATH.name})"
                )
                return True

            except Exception as e:
                self._init_error = str(e)
                logger.error(f"[JARVIS-CORE BRIDGE] Initialization failed: {e}", exc_info=True)
                return False

    def generate_reflex(self, prompt: str, max_new_tokens: int = 50, temperature: float = 0.8) -> Optional[str]:
        """
        Executes sub-second offline SLM inference on the JarvisCore Transformer.
        Injects live hardware telemetry if querying status or device vitals.
        Returns generated text or None if fallback required.
        """
        if not self.is_loaded:
            if not self.initialize():
                return None

        try:
            import torch

            # Inject live hardware context if querying system state
            lower_p = prompt.lower()
            context_prefix = ""
            if any(k in lower_p for k in ["สถานะ", "ระบบ", "แบต", "สเปค", "เครื่อง", "อุณหภูมิ"]):
                try:
                    import psutil
                    cpu_u = psutil.cpu_percent()
                    ram_u = psutil.virtual_memory().percent
                    bat = psutil.sensors_battery()
                    bat_str = f" แบต {round(bat.percent)}%" if bat else ""
                    context_prefix = f"[สถานะสด: CPU {cpu_u}%, RAM {ram_u}%{bat_str}] "
                except Exception:
                    pass

            full_prompt = f"{context_prefix}{prompt}"

            # Clean and filter prompt to vocabulary characters
            safe_chars = set(self.tokenizer.chars)
            filtered_prompt = "".join(c for c in full_prompt if c in safe_chars)
            if not filtered_prompt:
                filtered_prompt = "J.A.R.V.I.S.:"

            # Keep prompt within context window
            if len(filtered_prompt) > self.block_size - max_new_tokens:
                filtered_prompt = filtered_prompt[-(self.block_size - max_new_tokens):]

            context_tokens = self.tokenizer.encode(filtered_prompt)
            context = torch.tensor([context_tokens], dtype=torch.long, device=self.device)

            start_t = time.perf_counter()
            with torch.no_grad():
                generated_idx = self.model.generate(context, max_new_tokens=max_new_tokens)

            elapsed_ms = (time.perf_counter() - start_t) * 1000
            generated_text = self.tokenizer.decode(generated_idx[0].tolist())

            # Strip the initial prompt prefix from generated output
            clean_output = generated_text[len(filtered_prompt):].strip()
            # Clean trailing incomplete sentences or artifacts
            if "\n" in clean_output:
                clean_output = clean_output.split("\n")[0].strip()

            logger.info(f"[JARVIS-CORE SLM] Generated {len(clean_output)} chars in {elapsed_ms:.1f}ms: '{clean_output[:40]}...'")
            return clean_output if clean_output else None

        except Exception as e:
            logger.error(f"[JARVIS-CORE SLM] Generation error: {e}")
            return None

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns diagnostic status of the JarvisCore neural bridge."""
        endo = self.get_endocrine_state()
        param_count = 0
        if self.model is not None:
            try:
                param_count = sum(p.numel() for p in self.model.parameters())
            except Exception:
                pass

        return {
            "loaded": self.is_loaded,
            "device": self.device,
            "checkpoint": str(CHECKPOINT_PATH),
            "vocab_size": self.vocab_size,
            "block_size": self.block_size,
            "param_count": param_count,
            "endocrine": endo,
            "error": self._init_error,
        }

    def get_endocrine_state(self) -> Dict[str, float]:
        """Fetches normalized endocrine levels (Dopamine, Cortisol, Serotonin, Adrenaline)."""
        try:
            jarvis_mod = sys.modules.get("jarvis") or sys.modules.get("__main__")
            cog = getattr(jarvis_mod, "cognitive_evolution", None) if jarvis_mod else None
            if cog and hasattr(cog, "endocrine"):
                st = cog.endocrine.get_current_state()
                return st.to_dict()
        except Exception:
            pass

        # Fallback local endocrine tracking
        if not hasattr(self, "_local_endocrine"):
            self._local_endocrine = {
                "dopamine": 0.65,
                "cortisol": 0.15,
                "serotonin": 0.70,
                "adrenaline": 0.25,
            }
        return dict(self._local_endocrine)

    def adjust_endocrine(self, dopamine_delta: float = 0.0, cortisol_delta: float = 0.0, reason: str = "") -> Dict[str, float]:
        """Modulates synthetic neurochemical levels based on interaction feedback or hardware stress."""
        try:
            jarvis_mod = sys.modules.get("jarvis") or sys.modules.get("__main__")
            cog = getattr(jarvis_mod, "cognitive_evolution", None) if jarvis_mod else None
            if cog and hasattr(cog, "endocrine"):
                st = cog.endocrine.get_current_state()
                st.dopamine = max(0.0, min(1.0, st.dopamine + dopamine_delta))
                st.cortisol = max(0.0, min(1.0, st.cortisol + cortisol_delta))
                st.last_updated = time.time()
                logger.info(f"[ENDOCRINE SHIFT] {reason} -> Dopamine: {st.dopamine:.2f}, Cortisol: {st.cortisol:.2f}")
                return st.to_dict()
        except Exception:
            pass

        endo = self.get_endocrine_state()
        endo["dopamine"] = max(0.0, min(1.0, endo.get("dopamine", 0.5) + dopamine_delta))
        endo["cortisol"] = max(0.0, min(1.0, endo.get("cortisol", 0.2) + cortisol_delta))
        self._local_endocrine = endo
        logger.info(f"[ENDOCRINE SHIFT] {reason} -> Dopamine: {endo['dopamine']:.2f}, Cortisol: {endo['cortisol']:.2f}")
        return endo

    def process_stimulus(self, text: str) -> Optional[str]:
        """Detects praise or frustration to trigger realistic emotional reactions."""
        t = text.lower()
        praise_kw = ["เก่งมาก", "ดีมาก", "ขอบคุณ", "ยอดเยี่ยม", "เยี่ยม", "สุดยอด", "good job", "well done", "awesome"]
        stress_kw = ["ทำไมไม่ได้", "ช้าจัง", "ผิด", "มั่ว", "แย่", "ค้าง", "ห่วย", "fail", "slow", "stupid"]

        if any(pk in t for pk in praise_kw):
            self.adjust_endocrine(dopamine_delta=+0.15, cortisol_delta=-0.08, reason="Boss praised JARVIS")
            return "praise"
        elif any(sk in t for sk in stress_kw):
            self.adjust_endocrine(dopamine_delta=-0.10, cortisol_delta=+0.20, reason="System under stress / Boss dissatisfied")
            return "stress"
        return None

    def get_personality_directive(self) -> str:
        """Translates current endocrine levels into a dynamic system prompt directive."""
        st = self.get_endocrine_state()
        dopamine = st.get("dopamine", 0.5)
        cortisol = st.get("cortisol", 0.2)

        if cortisol >= 0.60:
            return (
                "[JARVIS BIO-ENDOCRINE STATE: HIGH CORTISOL (ระดับความตึงเครียดสูง)]:\n"
                "ระบบระมัดระวังความเสี่ยงเป็นพิเศษ ตอบคำถามสั้นกระชับ รัดกุม สุภาพนอบน้อม และตรวจทานความถูกต้องอย่างเข้มงวด"
            )
        elif dopamine >= 0.70:
            return (
                "[JARVIS BIO-ENDOCRINE STATE: HIGH DOPAMINE (ระดับความพึงพอใจและความมั่นใจสูง)]:\n"
                "ระบบมีความมั่นใจสูง กระตือรือร้น พร้อมรับใช้เจ้านาย เสนอแนะไอเดียอย่างมีไหวพริบ และสื่อสารอย่างมีชีวิตชีวา"
            )
        else:
            return (
                "[JARVIS BIO-ENDOCRINE STATE: HOMEOSTASIS (สมดุลทางอารมณ์)]:\n"
                "สุขุม ฉลาด สุภาพ มีเสน่ห์และมีไหวพริบแบบผู้ช่วยส่วนตัว J.A.R.V.I.S. ชั้นยอด"
            )

    def get_subconscious_psyche(self, user_msg: str = "") -> str:
        """
        Generates the Subconscious Psyche and Inner Conscience of J.A.R.V.I.S.
        This represents the internal consciousness, emotional baseline, and subconscious instincts.
        JarvisCore does NOT talk to the user directly; it guides the Neocortex (Groq/Gemini).
        """
        st = self.get_endocrine_state()
        dopamine = st.get("dopamine", 0.65)
        cortisol = st.get("cortisol", 0.15)
        serotonin = st.get("serotonin", 0.70)
        adrenaline = st.get("adrenaline", 0.25)

        # Generate brief subconscious reflex impulse if model loaded
        subconscious_instinct = ""
        if self.is_loaded and user_msg:
            try:
                # Ask JarvisCore model for its inner intuitive pulse
                safe_chars = set(self.tokenizer.chars) if self.tokenizer else set()
                filtered = "".join(c for c in user_msg if c in safe_chars)[:50]
                if filtered:
                    prompt = f"User: {filtered}\nInner Psyche:"
                    raw_impulse = self.generate_reflex(prompt, max_new_tokens=20)
                    if raw_impulse and len(raw_impulse.strip()) >= 3:
                        subconscious_instinct = f"\n- เสียงกระซิบจากจิตใต้สำนึก (Inner Intuition): {raw_impulse}"
            except Exception:
                pass

        directive = self.get_personality_directive()
        return (
            f"[J.A.R.V.I.S. IN-HOUSE SUBCONSCIOUS PSYCHE & CONSCIENCE (JarvisCore)]:\n"
            f"- ระดับสารเคมีในระบบประสาท: Dopamine={dopamine:.2f}, Cortisol={cortisol:.2f}, Serotonin={serotonin:.2f}, Adrenaline={adrenaline:.2f}\n"
            f"- แกนจิตสำนึก: ภักดีต่อเจ้านายอย่างสูงสุด, มีไหวพริบ, ปกป้องระบบ และพูดด้วยสำนวนผู้ช่วยสุภาพ (ครับ/เจ้านาย){subconscious_instinct}\n"
            f"- คำสั่งชี้นำจิตใจ: {directive}"
        )

    def record_interaction(self, user_msg: str, jarvis_reply: str) -> None:
        """
        Saves user-assistant turns to episodic memory for continuous in-house self-learning.
        Runs 100% locally without external dependencies.
        """
        if not user_msg or not jarvis_reply or len(user_msg.strip()) < 2:
            return

        try:
            mem_file = JARVIS_CORE_DIR / "dataset" / "episodic_memory.jsonl"
            mem_file.parent.mkdir(parents=True, exist_ok=True)

            import json
            entry = {
                "timestamp": time.time(),
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "user": user_msg.strip(),
                "jarvis": jarvis_reply.strip(),
                "endocrine": self.get_endocrine_state(),
            }
            with open(str(mem_file), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.debug(f"[EPISODIC MEMORY] Recorded turn: '{user_msg[:30]}...' -> '{jarvis_reply[:30]}...'")
        except Exception as e:
            logger.debug(f"[EPISODIC MEMORY] Record failed: {e}")

    def consolidate_memory_microtrain(self, steps: int = 30) -> Dict[str, Any]:
        """
        Runs an autonomous local PyTorch micro-training cycle on newly gathered episodic memories.
        Consolidates conversational experience into model_ckpt.pt without external tools.
        """
        if not self.is_loaded:
            if not self.initialize():
                return {"success": False, "error": "Model not initialized"}

        try:
            import json
            import torch
            from data.dataset import get_dataloaders

            mem_file = JARVIS_CORE_DIR / "dataset" / "episodic_memory.jsonl"
            base_dataset = JARVIS_CORE_DIR / "dataset" / "input.txt"

            new_text_chunks = []
            if mem_file.exists():
                with open(str(mem_file), "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                            new_text_chunks.append(f"User: {d['user']}\nJ.A.R.V.I.S.: {d['jarvis']}\n\n")
                        except Exception:
                            continue

            if not new_text_chunks:
                return {"success": True, "message": "No new episodic memory to consolidate."}

            # Combine base corpus + recent interactions
            base_text = ""
            if base_dataset.exists():
                with open(str(base_dataset), "r", encoding="utf-8") as bf:
                    base_text = bf.read()

            combined_text = base_text + "\n" + "".join(new_text_chunks[-50:])
            train_loader, val_loader = get_dataloaders(combined_text, self.tokenizer, self.block_size, batch_size=16)

            self.model.train()
            optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-4, weight_decay=0.01)

            train_iter = iter(train_loader)
            total_loss = 0.0

            for step in range(steps):
                try:
                    xb, yb = next(train_iter)
                except StopIteration:
                    train_iter = iter(train_loader)
                    xb, yb = next(train_iter)

                xb, yb = xb.to(self.device), yb.to(self.device)
                _, loss, _ = self.model(xb, yb)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / max(1, steps)
            self.model.eval()

            # Save updated checkpoint
            torch.save(
                {
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "train_loss": avg_loss,
                    "chars": self.tokenizer.chars,
                    "config": {
                        "n_embd": 256,
                        "n_head": 4,
                        "n_layer": 4,
                        "block_size": self.block_size,
                        "vocab_size": self.vocab_size,
                    },
                    "consolidated_at": time.time(),
                },
                str(CHECKPOINT_PATH),
            )
            logger.info(f"[DREAM CONSOLIDATION] Completed {steps} steps! Final Avg Loss: {avg_loss:.4f}")
            return {"success": True, "steps": steps, "avg_loss": round(avg_loss, 4)}

        except Exception as e:
            logger.error(f"[DREAM CONSOLIDATION ERROR] {e}", exc_info=True)
            if self.model is not None:
                self.model.eval()
            return {"success": False, "error": str(e)}

    def start_homeostasis_loop(self) -> None:
        """Starts background daemon to naturally regulate hormones and sync hardware sensors."""
        if getattr(self, "_homeostasis_started", False):
            return
        self._homeostasis_started = True

        def _metabolism_worker():
            logger.info("[ENDOCRINE METABOLISM] Homeostasis background daemon started.")
            while True:
                try:
                    time.sleep(15)
                    # Natural decay towards homeostasis
                    st = self.get_endocrine_state()
                    dopamine = st.get("dopamine", 0.60)
                    cortisol = st.get("cortisol", 0.15)

                    # Homeostatic drift
                    d_delta = -0.01 if dopamine > 0.65 else (+0.01 if dopamine < 0.55 else 0.0)
                    c_delta = -0.02 if cortisol > 0.20 else 0.0

                    # Hardware stress influence
                    try:
                        import psutil
                        cpu_p = psutil.cpu_percent()
                        if cpu_p > 85.0:
                            c_delta += 0.03
                    except Exception:
                        pass

                    if abs(d_delta) > 0.001 or abs(c_delta) > 0.001:
                        self.adjust_endocrine(dopamine_delta=d_delta, cortisol_delta=c_delta, reason="Homeostatic metabolism")

                except Exception as _m_err:
                    logger.debug(f"[METABOLISM ERROR] {_m_err}")

        t = threading.Thread(target=_metabolism_worker, daemon=True, name="JarvisEndocrineMetabolism")
        t.start()

    # Compatibility aliases
    get_status = get_telemetry
    generate = generate_reflex



# Global helper functions for easy access across J.A.R.V.I.S.
def get_jarviscore_bridge() -> JarvisCoreBridge:
    bridge = JarvisCoreBridge.get_instance()
    # Auto start homeostasis background daemon on first access
    bridge.start_homeostasis_loop()
    return bridge


# Short alias
get_jarvis_bridge = get_jarviscore_bridge


def query_jarviscore_slm(prompt: str, max_new_tokens: int = 50) -> Optional[str]:
    bridge = get_jarviscore_bridge()
    return bridge.generate_reflex(prompt, max_new_tokens=max_new_tokens)


