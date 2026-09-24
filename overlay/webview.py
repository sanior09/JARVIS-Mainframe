"""
webview.py -- JARVIS WebView Component
Configures QWebEngineView to load the Flask frontend.
"""
from __future__ import annotations
import logging
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget
from state import CONFIG

logger = logging.getLogger(__name__)

_OFFLINE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{margin:0;background:#0a0e1a;display:flex;flex-direction:column;
align-items:center;justify-content:center;height:100vh;
font-family:"Segoe UI",sans-serif;color:#4fc3f7;}
.pulse{width:60px;height:60px;border-radius:50%;border:3px solid #4fc3f7;
border-top-color:transparent;animation:spin 1s linear infinite;margin-bottom:20px;}
@keyframes spin{to{transform:rotate(360deg);}}
h2{margin:0 0 8px;font-weight:300;letter-spacing:3px;}
p{margin:0;font-size:12px;opacity:0.6;}
</style></head>
<body><div class="pulse"></div>
<h2>J.A.R.V.I.S.</h2>
<p>Establishing connection to Mainframe...</p>
</body></html>"""


class JarvisWebView(QWebEngineView):
    """Chromium WebView pre-configured for the JARVIS Flask frontend."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._configure_settings()
        self.show_offline()

    def load_backend(self) -> None:
        logger.info("[WebView] Loading %s", CONFIG.backend_url)
        self.setUrl(QUrl(CONFIG.backend_url))

    def show_offline(self) -> None:
        self.setHtml(_OFFLINE_HTML, QUrl("about:blank"))

    def _configure_settings(self) -> None:
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.MediaAudioCapture, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.MediaVideoCapture, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

    def createWindow(self, _type):
        return self