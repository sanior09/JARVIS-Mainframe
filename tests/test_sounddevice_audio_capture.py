"""
Unit tests verifying all core voice modules capture audio via
sounddevice.RawInputStream (16,000 Hz, Mono, int16) on Windows default mic
while preserving existing STT / VAD / Wake Word pipelines.
"""

import os
import struct
import sys
import threading
import wave
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
for p in (BASE_DIR, MODULES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from modules.audio_capture import (
    pcm16_rms,
    pcm16_to_wav_bytes,
    record_utterance_from_stream,
)


def _pcm_chunk(amplitude: int, frames: int = 512) -> bytes:
    return struct.pack(f"<{frames}h", *([amplitude] * frames))


def test_audio_capture_helpers_and_utterance_framing():
    silence = _pcm_chunk(0, 512)
    speech = _pcm_chunk(2000, 512)
    assert pcm16_rms(silence) == 0.0
    assert pcm16_rms(speech) == pytest.approx(2000.0, rel=1e-3)

    wav_bytes = pcm16_to_wav_bytes(speech, sample_rate=16000, channels=1)
    with wave.open(BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.readframes(512) == speech

    # 20 speech chunks (~0.64s) followed by 25 silent chunks (~0.8s > pause_threshold=0.7s)
    chunks = [(speech, False)] * 20 + [(silence, False)] * 25
    mock_stream = MagicMock()
    mock_stream.read.side_effect = chunks

    utterance = record_utterance_from_stream(
        mock_stream,
        sample_rate=16000,
        blocksize=512,
        energy_threshold=800.0,
        pause_threshold=0.7,
        listen_timeout=2.0,
        phrase_limit=5.0,
    )
    assert len(utterance) > len(speech) * 20


def test_vad_bargein_uses_sounddevice_default_mic():
    import jarvis_vad_bargein as vad_mod

    mgr = vad_mod.AudioInteractionManager(confidence_threshold=0.6, silence_duration=0.7)
    mgr.vad_model = None  # Force RMS fallback path cleanly in test

    captured_kwargs = {}

    class FakeStream:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self._reads = 0

        def start(self):
            pass

        def read(self, frames):
            self._reads += 1
            if self._reads >= 3:
                mgr._is_running = False
            return _pcm_chunk(0, frames), False

        def stop(self):
            pass

        def close(self):
            pass

    mgr._is_running = True
    with patch.object(vad_mod.sd, "RawInputStream", side_effect=FakeStream):
        mgr._audio_processing_worker()

    assert captured_kwargs["samplerate"] == 16000
    assert captured_kwargs["channels"] == 1
    assert captured_kwargs["dtype"] == "int16"
    assert captured_kwargs["blocksize"] == 512
    assert captured_kwargs.get("device") is None


def test_wake_word_engine_uses_sounddevice_and_google_callback():
    import jarvis_core.wake_word as ww_mod

    engine = ww_mod.WakeWordEngine()
    captured_kwargs = {}
    wake_detected = threading.Event()
    received_phrases = []

    silence = _pcm_chunk(0, 512)
    speech = _pcm_chunk(2500, 512)
    # 16 ambient calibration chunks + 15 speech chunks + 25 silence chunks
    seq = [silence] * 16 + [speech] * 15 + [silence] * 25

    class FakeStream:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self._idx = 0

        def start(self):
            pass

        def read(self, frames):
            if self._idx < len(seq):
                data = seq[self._idx]
                self._idx += 1
                return data, False
            engine.is_listening = False
            return silence, False

        def stop(self):
            pass

        def close(self):
            pass

    def _on_wake(command="", full_text=""):
        received_phrases.append(full_text)
        wake_detected.set()
        engine.is_listening = False

    with (
        patch.object(ww_mod.sd, "RawInputStream", side_effect=FakeStream),
        patch.object(engine.recognizer, "recognize_google", return_value="สวัสดี จาร์วิส") as mock_google,
    ):
        engine.on_wake_callback = _on_wake
        engine.is_listening = True
        engine._listen_loop()

    assert captured_kwargs["samplerate"] == 16000
    assert captured_kwargs["channels"] == 1
    assert captured_kwargs["dtype"] == "int16"
    assert captured_kwargs.get("device") is None
    mock_google.assert_called_once()
    assert mock_google.call_args.kwargs.get("language") == "th-TH"
    assert wake_detected.is_set()
    assert received_phrases == ["สวัสดี จาร์วิส"]


def test_streaming_stt_uses_sounddevice_raw_input_stream(monkeypatch):
    import jarvis_stt_stream as stream_mod

    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    mock_dg_conn = MagicMock()
    mock_dg_ctx = MagicMock()
    mock_dg_ctx.__enter__.return_value = mock_dg_conn
    mock_dg_ctx.__exit__.return_value = False
    mock_dg_client = MagicMock()
    mock_dg_client.listen.v1.connect.return_value = mock_dg_ctx

    captured_kwargs = {}
    sent_payload = b"\x01\x02" * 512

    class FakeStream:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def start(self):
            cb = captured_kwargs["callback"]
            cb(sent_payload, 1024, None, None)
            engine._listen_done_event.set()

        def stop(self):
            pass

        def close(self):
            pass

    with patch.object(stream_mod, "DeepgramClient", return_value=mock_dg_client):
        engine = stream_mod.StreamingSTTEngine()
        with patch.object(stream_mod.sd, "RawInputStream", side_effect=FakeStream):
            engine.listen_and_transcribe()

    assert captured_kwargs["samplerate"] == 16000
    assert captured_kwargs["channels"] == 1
    assert captured_kwargs["dtype"] == "int16"
    assert captured_kwargs["blocksize"] == 1024
    assert captured_kwargs.get("device") is None
    mock_dg_conn.send_media.assert_called_once_with(sent_payload)


def test_local_engine_stt_module_uses_sounddevice_default_mic(monkeypatch):
    import local_engine

    monkeypatch.setenv("STT_MIN_RMS", "500")
    stt = local_engine.STTModule(language="th-TH", energy_threshold=800, pause_threshold=0.7)
    assert stt._device_index is None

    captured_kwargs = {}
    speech = _pcm_chunk(2000, 512)
    silence = _pcm_chunk(0, 512)
    # 20 speech chunks (~0.64s >= 0.5s minimum) + 25 silence chunks
    seq = [speech] * 20 + [silence] * 25

    class FakeStream:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self._idx = 0

        def start(self):
            pass

        def read(self, frames):
            data = seq[self._idx] if self._idx < len(seq) else silence
            self._idx += 1
            return data, False

        def stop(self):
            pass

        def close(self):
            pass

    with (
        patch.object(local_engine.sd, "RawInputStream", side_effect=FakeStream),
        patch.object(local_engine, "transcribe_audio", return_value="เปิดไฟห้องนอน") as mock_transcribe,
    ):
        result = stt.listen_and_transcribe()

    assert captured_kwargs["samplerate"] == 16000
    assert captured_kwargs["channels"] == 1
    assert captured_kwargs["dtype"] == "int16"
    assert captured_kwargs.get("device") is None
    mock_transcribe.assert_called_once()
    assert result == "เปิดไฟห้องนอน"
