// [SECURITY MATRIX] Intercept all fetch requests to inject Authentication Token
const originalFetch = window.fetch;
window.fetch = async function() {
    let [resource, config] = arguments;
    if (!config) config = {};
    if (!config.headers) config.headers = {};
    if (window.JARVIS_TOKEN) {
        config.headers['X-JARVIS-TOKEN'] = window.JARVIS_TOKEN;
    }
    return originalFetch(resource, config);
};

const statusBar = document.getElementById('status-bar');
const neuralCore = document.querySelector('.neural-core-container');
window.isYouTubeIframeAPIReady = false;
window.onYouTubeIframeAPIReady = function() { window.isYouTubeIframeAPIReady = true; };

let speechQueue = [];
const MAX_SPEECH_QUEUE = 10; // [MED-005] ป้องกัน speechQueue สะสม RAM ไม่จำกัด
let currentAudio = null;
let isJarvisSpeaking = false;
let recognition = null; // [UX/UI INTELLIGENCE] เพิ่มตัวแปรสถานะการคิด
let isContinuousMode = false;
let timeoutTimer = null;
let isThinking = false; // [UX/UI INTELLIGENCE] เพิ่มตัวแปรสถานะการคิด
let webcamStream = null;
let isProcessingQueue = false;
let visionModel = null;
let handsDetector = null;
let latestHandLandmarks = null;
let activeDraggedHologram = null;
let currentHoveredHologram = null;
let smoothedHandX = null;
let smoothedHandY = null;
let lastHoverCheckTime = 0;
let hasClickedThisPinch = false;
let isVisionActive = false;
let hologramVideoPlayer = null; // [NACHAPOL PROTOCOL] เพิ่มตัวแปรสำหรับจัดการ Video Player
let lastDetectionTime = 0;
let lastFaceDetectionTime = 0;
let lastVerifyUserTime = 0;
let lastFacePredictions = [];
let offscreenCaptureCanvas = null;
let offscreenCaptureCtx = null;
const DETECTION_INTERVAL = 150; // ตรวจจับทุก 150ms (~6.5 fps) ลดลง CPU ได้อย่างมากในขณะที่ยังดูลื่น
let lastStatusBarTime = 0;
let isDetecting = false; // [NACHAPOL PROTOCOL OPTIMIZED] ล็อคสถานะป้องกันการประมวลผลเฟรมภาพซ้อนทับกัน
let hudDetectedObject = null; // Stores {name: '', box: [ymin, xmin, ymax, xmax], expireTime: 0}
let activeArBlueprint = null; // Stores active blueprint layout structure

// --- [VOICE REACTIVITY ENGINE] ---
let micStream = null;
let audioContext = null;
let analyserNode = null;
let micSource = null;
let voiceVisualizerAnimationId = null;
const frequencyData = new Uint8Array(32);

async function initVoiceVisualizer() {
    if (audioContext) return; // Already initialized
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyserNode = audioContext.createAnalyser();
        analyserNode.fftSize = 64;
        micSource = audioContext.createMediaStreamSource(micStream);
        micSource.connect(analyserNode);
        
        startVoiceVisualizerLoop();
    } catch (e) {
        console.warn("[AUDIO KERNEL] Voice Visualizer init failed:", e);
    }
}

function startVoiceVisualizerLoop() {
    if (!analyserNode) return;
    analyserNode.getByteFrequencyData(frequencyData);
    
    let sum = 0;
    for (let i = 0; i < frequencyData.length; i++) sum += frequencyData[i];
    let averageVolume = sum / frequencyData.length;
    
    const ring2 = document.querySelector('.ring-2');
    const ring4 = document.querySelector('.ring-4');
    const ring5 = document.querySelector('.ring-5');

    // Only react to voice if JARVIS is listening and JARVIS is NOT speaking
    if (neuralCore && neuralCore.classList.contains('listening') && !isJarvisSpeaking) {
        let scaleMultiplier = 1 + (averageVolume / 255) * 0.25; 
        let glowIntensity = averageVolume / 255;
        
        if (averageVolume > 10) {
            if (ring2) ring2.style.transform = `scale(${scaleMultiplier})`;
            if (ring4) {
                ring4.style.transform = `scale(${scaleMultiplier + 0.05})`;
                ring4.style.boxShadow = `0 0 ${30 + glowIntensity * 50}px rgba(255, 255, 255, ${0.8 + glowIntensity * 0.2}), inset 0 0 ${20 + glowIntensity * 30}px rgba(255, 255, 255, ${0.5 + glowIntensity * 0.5})`;
            }
            if (ring5) ring5.style.transform = `scale(${scaleMultiplier - 0.05})`;
        } else {
            resetRings(ring2, ring4, ring5);
        }
    } else {
        resetRings(ring2, ring4, ring5);
    }

    voiceVisualizerAnimationId = requestAnimationFrame(startVoiceVisualizerLoop);
}

function resetRings(ring2, ring4, ring5) {
    if (ring2 && ring2.style.transform !== 'scale(1)') ring2.style.transform = 'scale(1)';
    if (ring4 && ring4.style.transform !== 'scale(1)') {
        ring4.style.transform = 'scale(1)';
        ring4.style.boxShadow = '';
    }
    if (ring5 && ring5.style.transform !== 'scale(1)') ring5.style.transform = 'scale(1)';
}
// ------------------------------------

async function toggleCamera() {
    const container = document.getElementById('camera-container');
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('vision-overlay');
    const btn = document.querySelector('button[onclick="toggleCamera()"]');
    const statusMsg = document.getElementById('status-bar');

    if (!webcamStream) {
        try {
            webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = webcamStream;
            container.style.display = 'block';
            btn.innerText = 'VISION: ON';
            playWakeSound();
            isVisionActive = true;

            // [NACHAPOL PROTOCOL] ป้องกันระบบหยุดทำงานเมื่อสายสัญญาณหลุด
            webcamStream.getVideoTracks()[0].onended = () => {
                handleCameraFailure();
            };
        } catch (err) {
            statusMsg.innerText = 'CRITICAL: CAMERA ACCESS DENIED - CHECK HARDWARE';
        }
        initVisionSystem(video, canvas);
    } else {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
        container.style.display = 'none';
        btn.innerText = 'VISION: OFF';
        isVisionActive = false;
        isDetecting = false; // [OPTIMIZED] คืนค่าล็อกเมื่อปิดกล้อง
    }
}

function handleCameraFailure() {
    if (!isVisionActive) return;
    statusBar.innerText = 'CAMERA DISCONNECTED. ATTEMPTING AUTO-RECONNECT...';
    webcamStream = null;
    isDetecting = false; // [OPTIMIZED] คืนค่าล็อกเมื่อกล้องหลุด
    setTimeout(() => {
        console.warn("[JARVIS] Camera connection lost. Retrying sequence...");
        toggleCamera();
    }, 5000);
}

function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load script ${src}`));
        document.head.appendChild(script);
    });
}

// Advanced Vision Core - Thermal Matrix variables
let isThermalMode = false;
let isSpatialMode = false;
let homographyMatrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]; // 3x3 Homography Inverse Default

// Simulated electronics component positions (source space)
let simulatedComponents = {
    resistorR14: { name: 'Resistor R14', x: 75, y: 40, temp: 45.0, rate: 1.1, baseTemp: 45.0 },
    capacitorC1: { name: 'Capacitor C1', x: 230, y: 60, temp: 35.0, rate: 0.5, baseTemp: 35.0 },
    regulatorU2: { name: 'Regulator U2', x: 150, y: 120, temp: 50.0, rate: 0.7, baseTemp: 50.0 }
};
let anomalyLogged = { resistorR14: false, capacitorC1: false, regulatorU2: false };

let threeJsContext = {
    scene: null, camera: null, renderer: null, controls: null,
    animationId: null, chassisMesh: null, faceParticles: null, activeScanTarget: 'chassis'
};

// Offscreen canvases for raw thermal video capture
let offscreenThermalCanvas = document.createElement('canvas');
let offscreenThermalCtx = offscreenThermalCanvas.getContext('2d');
offscreenThermalCanvas.width = 80;
offscreenThermalCanvas.height = 60;

function getIronbowColor(value) {
    // Map luminance value (0-255) to the Ironbow thermal color lookup table (LUT)
    let r = 0, g = 0, b = 0;
    if (value < 64) {
        r = Math.round(value * 0.5);
        g = 0;
        b = Math.round(value * 4);
    } else if (value < 128) {
        r = Math.round((value - 64) * 3 + 32);
        g = 0;
        b = Math.round(255 - (value - 64) * 3);
    } else if (value < 192) {
        r = 255;
        g = Math.round((value - 128) * 3);
        b = 0;
    } else {
        r = 255;
        g = 255;
        b = Math.round((value - 192) * 4);
    }
    return { r, g, b };
}

function drawThermalOverlay(srcCanvas, dstCtx, width, height, H_inv) {
    const srcCtx = srcCanvas.getContext('2d');
    const srcData = srcCtx.getImageData(0, 0, srcCanvas.width, srcCanvas.height);
    const srcPixels = srcData.data;

    const dstData = dstCtx.createImageData(width, height);
    const dstPixels = dstData.data;

    const srcW = srcCanvas.width;
    const srcH = srcCanvas.height;

    const h00 = H_inv[0], h01 = H_inv[1], h02 = H_inv[2];
    const h10 = H_inv[3], h11 = H_inv[4], h12 = H_inv[5];
    const h20 = H_inv[6], h21 = H_inv[7], h22 = H_inv[8];

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const w = h20 * x + h21 * y + h22;
            if (Math.abs(w) > 0.0001) {
                // Backward map: destination coordinates to source coordinates
                const xs = Math.round((h00 * x + h01 * y + h02) / w);
                const ys = Math.round((h10 * x + h11 * y + h12) / w);

                if (xs >= 0 && xs < srcW && ys >= 0 && ys < srcH) {
                    const dstIdx = (y * width + x) * 4;
                    const srcIdx = (ys * srcW + xs) * 4;

                    const r = srcPixels[srcIdx];
                    const g = srcPixels[srcIdx + 1];
                    const b = srcPixels[srcIdx + 2];
                    const luminance = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
                    const thermal = getIronbowColor(luminance);

                    dstPixels[dstIdx] = thermal.r;
                    dstPixels[dstIdx + 1] = thermal.g;
                    dstPixels[dstIdx + 2] = thermal.b;
                    dstPixels[dstIdx + 3] = 160; // Opacity blend
                }
            }
        }
    }

    // Put morphed image onto a temporary buffer and draw onto the target context
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    tempCanvas.getContext('2d').putImageData(dstData, 0, 0);
    dstCtx.drawImage(tempCanvas, 0, 0);
}

function warpCoordinate(x, y, H) {
    // Warp component center point coordinates using homography forward matrix coefficients
    const h00 = H[0], h01 = H[1], h02 = H[2];
    const h10 = H[3], h11 = H[4], h12 = H[5];
    const h20 = H[6], h21 = H[7], h22 = H[8];
    const w = h20 * x + h21 * y + h22;
    if (Math.abs(w) > 0.0001) {
        return {
            x: (h00 * x + h01 * y + h02) / w,
            y: (h10 * x + h11 * y + h12) / w
        };
    }
    return { x, y };
}

async function loadCalibrationFromDB() {
    try {
        const res = await fetch('/api/spatial/calibration');
        const data = await res.json();
        if (data && data.homography_matrix) {
            homographyMatrix = data.homography_matrix;
            // Approximate matching UI slider positions
            document.getElementById('slider-tx').value = -homographyMatrix[2];
            document.getElementById('slider-ty').value = -homographyMatrix[5];
            document.getElementById('slider-persp').value = homographyMatrix[6];
            updateCalibrationValues();
        }
    } catch (e) {
        console.error("[SPATIAL CORE] FAILED TO LOAD CALIBRATION MATRIX:", e);
    }
}

function updateCalibrationValues() {
    const tx = parseFloat(document.getElementById('slider-tx').value);
    const ty = parseFloat(document.getElementById('slider-ty').value);
    const scale = parseFloat(document.getElementById('slider-scale').value);
    const rot = parseFloat(document.getElementById('slider-rot').value);
    const persp = parseFloat(document.getElementById('slider-persp').value);

    document.getElementById('val-tx').innerText = tx;
    document.getElementById('val-ty').innerText = ty;
    document.getElementById('val-scale').innerText = scale.toFixed(2);
    document.getElementById('val-rot').innerText = rot.toFixed(2);
    document.getElementById('val-persp').innerText = persp.toFixed(4);

    // Homography matrix mathematical coefficients
    const cos = Math.cos(rot);
    const sin = Math.sin(rot);
    homographyMatrix = [
        cos / scale, sin / scale, -tx,
        -sin / scale, cos / scale, -ty,
        persp, persp, 1.0
    ];
}

function initCalibrationSliders() {
    const sliders = ['slider-tx', 'slider-ty', 'slider-scale', 'slider-rot', 'slider-persp'];
    sliders.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateCalibrationValues);
        }
    });
    updateCalibrationValues();
}

async function saveCalibration() {
    try {
        const res = await fetch('/api/spatial/calibration', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ homography_matrix: homographyMatrix })
        });
        const data = await res.json();
        if (data.status === 'saved') {
            statusBar.innerText = 'CALIBRATION MATRIX COMMITTED TO NACHAPOL ARCHIVE';
            playWakeSound();
        } else {
            statusBar.innerText = 'CALIBRATION WRITE FAILURE';
        }
    } catch (err) {
        console.error("[DATABASE KERNEL] CALIBRATION DB WRITE FAILURE:", err);
        statusBar.innerText = 'CRITICAL: BACKEND DB ACCESS OFFLINE';
    }
}

function toggleThermalMode() {
    isThermalMode = !isThermalMode;
    const btn = document.getElementById('thermal-toggle');
    const panel = document.getElementById('calibration-panel');
    if (isThermalMode) {
        btn.innerText = 'THERMAL: ON';
        btn.style.background = 'rgba(255, 70, 50, 0.2)';
        btn.style.borderColor = '#ff4632';
        btn.style.color = '#ff4632';
        panel.style.display = 'block';
        playWakeSound();
    } else {
        btn.innerText = 'THERMAL: OFF';
        btn.style.background = '';
        btn.style.borderColor = '';
        btn.style.color = '';
        panel.style.display = 'none';
    }
}

function toggleSpatialMode() {
    isSpatialMode = !isSpatialMode;
    const btn = document.getElementById('spatial-toggle');
    if (isSpatialMode) {
        btn.innerText = 'SPATIAL: ON';
        btn.style.background = 'rgba(55, 226, 255, 0.2)';
        btn.style.borderColor = '#37e2ff';
        btn.style.color = '#37e2ff';
        openSpatialScannerHologram();
    } else {
        btn.innerText = 'SPATIAL: OFF';
        btn.style.background = '';
        btn.style.borderColor = '';
        btn.style.color = '';
        closeSpatialHologram();
    }
}

function openSpatialScannerHologram() {
    let existingWin = document.getElementById('spatial-hologram-win');
    if (existingWin) return;

    const container = document.querySelector('.hud-container');
    const win = document.createElement('div');
    win.className = 'hologram-window';
    win.id = 'spatial-hologram-win';

    win.style.left = '450px';
    win.style.top = '150px';
    win.style.width = '380px';
    win.style.height = '430px';

    win.innerHTML = `
        <div class="hologram-header">
            <span class="hologram-title">SPATIAL SCANNER CORE</span>
            <div style="display: flex; gap: 10px; pointer-events: all;">
                <span class="hologram-btn" onclick="toggleSpatialMode()">[X]</span>
            </div>
        </div>
        <div class="hologram-content" style="height: calc(100% - 35px);">
            <div class="spatial-container">
                <div class="spatial-controls" style="pointer-events: all;">
                    <button class="nachapol-btn" onclick="setSpatialScanTarget('chassis')" style="font-size: 8px; padding: 4px 8px;">PMMA CHASSIS</button>
                    <button class="nachapol-btn" onclick="setSpatialScanTarget('face')" style="font-size: 8px; padding: 4px 8px;">3D FACE CLOUD</button>
                </div>
                <div id="spatial-canvas-container" style="width: 100%; height: 220px; border: 1px dashed rgba(55, 226, 177, 0.2); background: rgba(0, 5, 5, 0.4);"></div>
                <div class="spatial-annotations" id="spatial-ann-panel">Scanning target...</div>
            </div>
        </div>
    `;
    container.appendChild(win);
    makeDraggable(win);

    setTimeout(() => {
        initThreeJsSpatial();
    }, 100);
}

function closeSpatialHologram() {
    const win = document.getElementById('spatial-hologram-win');
    if (win) {
        if (threeJsContext.animationId) {
            cancelAnimationFrame(threeJsContext.animationId);
        }
        win.remove();
    }
    isSpatialMode = false;
    const btn = document.getElementById('spatial-toggle');
    if (btn) {
        btn.innerText = 'SPATIAL SCANNER';
        btn.style.background = '';
        btn.style.borderColor = '';
        btn.style.color = '';
    }
}

function setSpatialScanTarget(target) {
    if (!threeJsContext.scene) return;
    threeJsContext.activeScanTarget = target;
    if (target === 'chassis') {
        if (threeJsContext.chassisMesh) threeJsContext.chassisMesh.visible = true;
        if (threeJsContext.faceParticles) threeJsContext.faceParticles.visible = false;
    } else {
        if (threeJsContext.chassisMesh) threeJsContext.chassisMesh.visible = false;
        if (threeJsContext.faceParticles) threeJsContext.faceParticles.visible = true;
    }
}

function initThreeJsSpatial() {
    const container = document.getElementById('spatial-canvas-container');
    if (!container) return;

    const scene = new THREE.Scene();
    threeJsContext.scene = scene;

    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(0, 3, 5);
    threeJsContext.camera = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);
    threeJsContext.renderer = renderer;

    if (typeof THREE.OrbitControls !== 'undefined') {
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        threeJsContext.controls = controls;
    }

    const gridHelper = new THREE.GridHelper(8, 20, 0x00c8ff, 0x003344);
    scene.add(gridHelper);

    const chassisGeom = new THREE.BoxGeometry(2.5, 1.6, 1.2);
    const wireframe = new THREE.WireframeGeometry(chassisGeom);
    const chassisLine = new THREE.LineSegments(wireframe);
    chassisLine.material.color.setHex(0x00c8ff);
    scene.add(chassisLine);
    threeJsContext.chassisMesh = chassisLine;

    const cylGeom = new THREE.CylinderGeometry(0.3, 0.3, 1, 8, 1, true);
    const cylWire = new THREE.WireframeGeometry(cylGeom);
    const cyl1 = new THREE.LineSegments(cylWire);
    cyl1.material.color.setHex(0x00ffff);
    cyl1.position.set(-0.6, 0, 0);
    chassisLine.add(cyl1);

    const cyl2 = new THREE.LineSegments(cylWire);
    cyl2.material.color.setHex(0x00ffff);
    cyl2.position.set(0.6, 0, 0);
    chassisLine.add(cyl2);

    const pointsGeom = new THREE.BufferGeometry();
    const count = 300;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        const u = Math.random();
        const v = Math.random();
        const theta = u * 2.0 * Math.PI;
        const phi = Math.acos(2.0 * v - 1.0);
        let x = Math.sin(phi) * Math.cos(theta);
        let y = Math.sin(phi) * Math.sin(theta);
        let z = Math.cos(phi);

        if (z > 0) {
            z = z * 1.4;
            x = x * 0.75;
            y = y * 1.3 - 0.15;
        } else {
            z = z * 0.2;
        }
        positions[i * 3] = x * 1.0;
        positions[i * 3 + 1] = y * 1.3 - 0.1;
        positions[i * 3 + 2] = z * 1.0;
    }
    pointsGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const pointsMat = new THREE.PointsMaterial({ color: 0x00c8ff, size: 0.07, transparent: true, opacity: 0.85 });
    const faceParticles = new THREE.Points(pointsGeom, pointsMat);
    scene.add(faceParticles);
    threeJsContext.faceParticles = faceParticles;

    faceParticles.visible = false;

    function animate() {
        threeJsContext.animationId = requestAnimationFrame(animate);

        if (threeJsContext.activeScanTarget === 'chassis' && chassisLine) {
            chassisLine.rotation.y += 0.008;
            chassisLine.rotation.x += 0.003;
        } else if (threeJsContext.activeScanTarget === 'face' && faceParticles) {
            faceParticles.rotation.y += 0.01;
        }

        updateAnnotationsPanel();

        if (threeJsContext.controls) threeJsContext.controls.update();
        renderer.render(scene, camera);
    }
    animate();
}

let lastAnnotationTime = 0;
function updateAnnotationsPanel() {
    const panel = document.getElementById('spatial-ann-panel');
    if (!panel) return;

    const now = performance.now();
    if (now - lastAnnotationTime < 125) return; // ทำงานแค่ 8 ครั้ง/วินาที แทนที่จะเป็น 60 ครั้ง
    lastAnnotationTime = now;

    const randX = (Math.random() * 0.05 - 0.025).toFixed(4);
    const randY = (Math.random() * 0.05 - 0.025).toFixed(4);
    const randZ = (Math.random() * 0.05 - 0.025).toFixed(4);

    if (threeJsContext.activeScanTarget === 'chassis') {
        panel.innerHTML = `
<strong>[TARGET: PMMA CHASSIS BLUEPRINT]</strong><br>
Structure: Polymethyl Methacrylate (Acrylic)<br>
Formula: [C5O2H8]n Polymer Chain Model<br>
Thickness: 5.00mm | Density: 1.18 g/cm³<br>
Tensile Strength: 70.0 MPa | Yield: 55 MPa<br>
Glass Transition (Tg): 105.0°C | Melting: 160.0°C<br>
Scan Tolerance: ±0.12mm (Level 10 Clearance)<br>
Dynamic Node Delta:<br>
- Node Alpha: [X: ${(150 + parseFloat(randX) * 10).toFixed(2)}, Y: ${(100 + parseFloat(randY) * 10).toFixed(2)}, Z: -60.00]<br>
- Node Beta:  [X: -150.00, Y: -100.00, Z: ${(60 + parseFloat(randZ) * 10).toFixed(2)}]<br>
Matrix Stress Coefficient: ${(0.15 + Math.random() * 0.02).toFixed(4)} GPa
        `;
    } else {
        panel.innerHTML = `
<strong>[TARGET: 3D FACE POINT-CLOUD MASK]</strong><br>
Point Cloud Density: 300 nodes scanned<br>
Coherence Factor: ${(98.5 + Math.random() * 1.4).toFixed(2)}%<br>
Biometric ID: Primary Operator (Level 10 Clearance)<br>
Ref Vertex Vector:<br>
- Nose Bridge Node: [X: ${randX}, Y: 0.1500, Z: 1.2500]<br>
- Chin Anchor Node: [X: 0.0000, Y: -1.7500, Z: ${randZ}]<br>
Processing Rate: 100 frames/sec (Zero Latency Mode)
        `;
    }
}

function updateCircuitThermalSimulation(ctx) {
    const container = document.getElementById('camera-container');
    let hasAnomaly = false;

    // [NACHAPOL PROTOCOL] Hardware Data Integration Placeholder
    // TODO: Replace with real setInterval/fetch logic outside of requestAnimationFrame
    // For now, we wait for actual hardware data payload structure.

    for (let key in simulatedComponents) {
        let comp = simulatedComponents[key];

        // รอรับค่าจริงจาก Hardware Sensor (ตอนนี้ใช้ค่าฐานไปก่อน)

        const warped = warpCoordinate(comp.x, comp.y, homographyMatrix);
        const isHot = comp.temp > 80.0;
        ctx.strokeStyle = isHot ? '#ff3333' : 'rgba(55, 226, 177, 0.7)';
        ctx.fillStyle = ctx.strokeStyle;
        ctx.lineWidth = 1;

        ctx.beginPath();
        ctx.arc(warped.x, warped.y, isHot ? 8 : 4, 0, 2 * Math.PI);
        ctx.stroke();

        if (isHot) {
            ctx.beginPath();
            ctx.moveTo(warped.x - 12, warped.y);
            ctx.lineTo(warped.x + 12, warped.y);
            ctx.moveTo(warped.x, warped.y - 12);
            ctx.lineTo(warped.x, warped.y + 12);
            ctx.stroke();
            ctx.fillText(`ANOMALY: ${comp.temp.toFixed(1)}°C`, warped.x + 15, warped.y + 4);
            hasAnomaly = true;
        } else {
            ctx.fillText(`${comp.name}: ${comp.temp.toFixed(1)}°C`, warped.x + 8, warped.y + 3);
        }

        if (isHot && !anomalyLogged[key]) {
            anomalyLogged[key] = true;
            triggerAnomalyLog(comp.name, comp.temp);
        } else if (!isHot && anomalyLogged[key]) {
            anomalyLogged[key] = false;
        }
    }

    if (hasAnomaly) {
        container.classList.add('hazard-critical');
    } else {
        container.classList.remove('hazard-critical');
    }
}

function triggerAnomalyLog(name, temp) {
    speak(`WARNING: Restricted Alert. Component ${name} temperature vector has breached physical limits at ${temp.toFixed(1)} degrees Celsius.`);

    fetch('/api/telemetry/anomaly', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            component: name,
            temperature: parseFloat(temp.toFixed(1)),
            limit: 80.0
        })
    })
        .then(res => res.json())
        .then(data => {
            console.log(`[THERMAL SENTINEL] Anomaly logged: ${data.description}`);
        })
        .catch(err => console.error("[THERMAL SENTINEL] DATABASE WRITE FAILURE:", err));
}

async function initVisionSystem(video, canvas) {
    // Load MediaPipe Hand Tracking scripts
    if (!handsDetector) {
        try {
            if (typeof Hands === 'undefined') {
                await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js");
            }
            if (typeof Camera === 'undefined') {
                await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js");
            }

            handsDetector = new Hands({
                locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
            });

            handsDetector.setOptions({
                maxNumHands: 1, // ใช้มือเดียวในการควบคุม UI เพื่อความประหยัด
                modelComplexity: 0, // 0 = Lite (เร็วที่สุดและกินสเปคน้อยที่สุด), 1 = Full (ช้ากว่า)
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            handsDetector.onResults(onHandResults);
        } catch (err) {
            console.error("[VISION CORE] DEPENDENCY LOAD FAILURE (MEDIAPIPE HANDS):", err);
        }
    }

    if (!visionModel) {
        statusBar.innerText = 'LOADING VISION CORE (ML)...';
        try {
            if (typeof tf === 'undefined') {
                await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow/tfjs");
            }
            if (typeof tf !== 'undefined') {
                // บังคับใช้ WebGL backend เพื่อให้ประมวลผลบนการ์ดจอได้ (ลื่นขึ้นอย่างมหาศาล)
                await tf.setBackend('webgl').catch(() => console.warn("WebGL not supported, falling back to CPU"));
            }
            if (typeof blazeface === 'undefined') {
                await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface");
            }
            visionModel = await blazeface.load();
        } catch (err) {
            console.error("[VISION CORE] DEPENDENCY LOAD FAILURE (ML MODEL):", err);
            statusBar.innerText = 'ERROR: FAILED TO LOAD VISION CORE';
            return;
        }
    }

    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;
    const ctx = canvas.getContext('2d');

    if (!offscreenCaptureCanvas) {
        offscreenCaptureCanvas = document.createElement('canvas');
        offscreenCaptureCanvas.width = 640;
        offscreenCaptureCanvas.height = 360;
        offscreenCaptureCtx = offscreenCaptureCanvas.getContext('2d');
    }

    let qrTimeout = null;
    const qrToastLink = document.getElementById('qr-toast-link');

    window.currentSpatialARData = null;

    function drawSpatialARBlueprintOverlay(ctx, width, height, arData) {
        if (!arData || !arData.cad_nodes) return;

        const nodes = arData.cad_nodes;
        ctx.strokeStyle = "rgba(0, 191, 255, 0.8)"; // Blue Spectrum Guideline
        ctx.lineWidth = 2;
        ctx.beginPath();

        nodes.forEach((node, index) => {
            // Matrix Transformation & tracking jitter simulation
            const scaleX = width / 640;
            const scaleY = height / 360;
            const projX = (node.x * scaleX) + (Math.sin(performance.now() / 1500) * 5);
            const projY = (node.y * scaleY) + (Math.cos(performance.now() / 1500) * 5);

            ctx.fillStyle = "rgba(0, 191, 255, 0.6)";
            ctx.beginPath();
            ctx.arc(projX, projY, 6, 0, 2 * Math.PI);
            ctx.fill();

            if (index === 0) ctx.moveTo(projX, projY);
            else ctx.lineTo(projX, projY);

            ctx.fillStyle = "#00FFFF";
            ctx.font = "14px 'Sarabun', sans-serif";
            ctx.fillText(`[${node.id}]`, projX + 12, projY - 12);

            if (node.label) {
                ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
                const textWidth = ctx.measureText(node.label).width;
                ctx.fillRect(projX + 10, projY + 5, textWidth + 20, 25);
                ctx.fillStyle = "#00FFFF";
                ctx.fillText(node.label, projX + 15, projY + 22);
            }
        });
        ctx.stroke();
    }

    async function detectFrame() {
        if (!isVisionActive) {
            return;
        }

        if (isDetecting) {
            requestAnimationFrame(detectFrame);
            return;
        }

        const now = performance.now();
        if (now - lastDetectionTime >= DETECTION_INTERVAL) {
            lastDetectionTime = now;

            if (video.readyState === 4) {
                isDetecting = true;
                try {
                    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        canvas.style.width = "100%";
                        canvas.style.height = "100%";
                    }

                    offscreenCaptureCtx.drawImage(video, 0, 0, 640, 360);

                    if (window.jsQR) {
                        const qrImageData = offscreenCaptureCtx.getImageData(0, 0, 640, 360);
                        const qrCode = jsQR(qrImageData.data, qrImageData.width, qrImageData.height, { inversionAttempts: "dontInvert" });

                        if (qrCode) {
                            if (qrTimeout) {
                                clearTimeout(qrTimeout);
                                qrTimeout = null;
                            }

                            const qrData = qrCode.data;
                            let label = qrData;
                            try {
                                const url = new URL(qrData);
                                let hostname = url.hostname.replace('www.', '');
                                let capitalized = hostname.charAt(0).toUpperCase() + hostname.slice(1);
                                label = `🔗 เปิดลิงก์: ${capitalized}`;
                            } catch (e) {
                                label = `🔍 สแกนพบ: ${qrData.length > 25 ? qrData.substring(0, 25) + '...' : qrData}`;
                            }

                            if (qrToastLink) {
                                qrToastLink.innerText = label;
                                qrToastLink.style.display = 'block';
                                qrToastLink.onclick = () => {
                                    createHologramWindow("QR STREAM: LINK", qrData, null, "Spatial-Map");
                                    if (qrData.startsWith('http://') || qrData.startsWith('https://')) {
                                        window.open(qrData, '_blank');
                                    }
                                };
                            }
                        } else {
                            if (qrToastLink && qrToastLink.style.display === 'block' && !qrTimeout) {
                                qrTimeout = setTimeout(() => {
                                    qrToastLink.style.display = 'none';
                                    qrTimeout = null;
                                }, 1500);
                            }
                        }
                    }

                    // Hands & Face detection run concurrently via Promise.all
                    let handsPromise = Promise.resolve();
                    if (handsDetector) {
                        handsPromise = handsDetector.send({ image: offscreenCaptureCanvas }).catch(handsErr => {
                            console.error("Hands detection error:", handsErr);
                        });
                    }

                    // ปรับแต่งลดปริมาณการประมวลผล Face Detection เหลือ 1 ครั้งต่อวินาที (ลดภาระ CPU อย่างมาก)
                    let facePromise;
                    if (now - lastFaceDetectionTime >= 1000) {
                        lastFaceDetectionTime = now;
                        facePromise = visionModel.estimateFaces(offscreenCaptureCanvas, false).then(preds => {
                            lastFacePredictions = preds || [];
                            return lastFacePredictions;
                        }).catch(faceErr => {
                            console.error("Face detection error:", faceErr);
                            return lastFacePredictions;
                        });
                    } else {
                        facePromise = Promise.resolve(lastFacePredictions);
                    }

                    const [_, predictions] = await Promise.all([handsPromise, facePromise]);

                    ctx.clearRect(0, 0, canvas.width, canvas.height);

                    if (isThermalMode) {
                        offscreenThermalCtx.drawImage(video, 0, 0, 80, 60);
                        drawThermalOverlay(offscreenThermalCanvas, ctx, canvas.width, canvas.height, homographyMatrix);
                    }

                    updateCircuitThermalSimulation(ctx);

                    if (window.currentSpatialARData) {
                        drawSpatialARBlueprintOverlay(ctx, canvas.width, canvas.height, window.currentSpatialARData);
                    }

                    if (predictions && predictions.length > 0) {
                        predictions.forEach(prediction => {
                            const scaleX = canvas.width / 640;
                            const scaleY = canvas.height / 360;
                            const start = [prediction.topLeft[0] * scaleX, prediction.topLeft[1] * scaleY];
                            const end = [prediction.bottomRight[0] * scaleX, prediction.bottomRight[1] * scaleY];
                            const size = [end[0] - start[0], end[1] - start[1]];

                            ctx.strokeStyle = isThermalMode ? '#ff3333' : '#00c8ff';
                            ctx.lineWidth = isThermalMode ? 2 : 4;
                            ctx.strokeRect(start[0], start[1], size[0], size[1]);
                            ctx.fillStyle = ctx.strokeStyle;
                            ctx.fillRect(start[0], start[1], 20, 5);
                            ctx.fillRect(start[0], start[1], 5, 20);

                            if (isSpatialMode && threeJsContext.activeScanTarget === 'face') {
                                ctx.beginPath();
                                ctx.strokeStyle = 'rgba(55, 226, 255, 0.4)';
                                ctx.moveTo(start[0], start[1]);
                                ctx.lineTo(end[0], end[1]);
                                ctx.moveTo(start[0] + size[0], start[1]);
                                ctx.lineTo(start[0], start[1] + size[1]);
                                ctx.stroke();
                            }

                            if (prediction.probability && prediction.probability[0] > 0.95) {
                                const nowTime = Date.now();
                                // บังคับส่ง API เช็คสิทธิ์เฉพาะทุกๆ 3 วินาที แทนการยิงทุกๆ 100ms ป้องกันเซิร์ฟเวอร์ค้าง
                                if (nowTime - lastVerifyUserTime >= 3000) {
                                    lastVerifyUserTime = nowTime;
                                    fetch('/api/verify_user', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ detected: true, timestamp: nowTime })
                                    })
                                        .then(res => res.json())
                                        .then(data => {
                                            window.lastUserIdentity = data.authenticated ? "SUBJECT IDENTIFIED: SIR" : "UNKNOWN SUBJECT: INTRUDER";
                                        }).catch(err => console.error("Verify user error:", err));
                                }

                                const userLabel = window.lastUserIdentity || "SCANNING IDENTITY...";
                                ctx.fillText(userLabel, start[0], start[1] - 10);
                            } else {
                                ctx.fillText("SCANNING IDENTITY...", start[0], start[1] - 10);
                            }
                        });
                    }

                    let showLaserDisplay = false;

                    // [VISUAL FEEDBACK: HAND LANDMARKS OVERLAY]
                    if (latestHandLandmarks && latestHandLandmarks.length > 0) {
                        const points = latestHandLandmarks[0];
                        const thumb = points[4];
                        const index = points[8];

                        if (thumb && index) {
                            const tx = thumb.x * canvas.width;
                            const ty = thumb.y * canvas.height;
                            const ix = index.x * canvas.width;
                            const iy = index.y * canvas.height;

                            // Draw glowing points on index tip and thumb tip
                            ctx.beginPath();
                            ctx.fillStyle = "rgba(0, 200, 255, 0.75)";
                            ctx.arc(tx, ty, 6, 0, 2 * Math.PI);
                            ctx.arc(ix, iy, 6, 0, 2 * Math.PI);
                            ctx.fill();

                            if (isSpatialMode) {
                                showLaserDisplay = true;
                                const distance_cm = (Math.hypot(ix - tx, iy - ty) / 4.5).toFixed(1);
                                const rangeDisplay = document.getElementById('laser-range-display');
                                if (rangeDisplay) {
                                    rangeDisplay.innerText = `🔗 HUD LASER RANGE: ${distance_cm} cm`;
                                    rangeDisplay.style.display = 'block';
                                }

                                // Draw laser tracer line (JARVIS cyan)
                                ctx.beginPath();
                                ctx.strokeStyle = "#00c8ff";
                                ctx.lineWidth = 3;
                                ctx.shadowColor = "#00c8ff";
                                ctx.shadowBlur = 6;
                                ctx.moveTo(tx, ty);
                                ctx.lineTo(ix, iy);
                                ctx.stroke();
                                ctx.shadowBlur = 0;
                            } else {
                                // Draw connector line
                                ctx.beginPath();
                                ctx.strokeStyle = "rgba(0, 200, 255, 0.5)";
                                ctx.lineWidth = 2.5;
                                ctx.moveTo(tx, ty);
                                ctx.lineTo(ix, iy);
                                ctx.stroke();
                            }

                            // Draw scanning text
                            ctx.font = "10px Orbitron";
                            ctx.fillStyle = "#00c8ff";
                            ctx.fillText("GESTURE LINK ACTIVE", Math.min(tx, ix), Math.min(ty, iy) - 15);
                        }
                    }

                    if (!showLaserDisplay) {
                        const rangeDisplay = document.getElementById('laser-range-display');
                        if (rangeDisplay) {
                            rangeDisplay.style.display = 'none';
                        }
                        ctx.shadowBlur = 0;
                    }

                    if (hudDetectedObject && Date.now() < hudDetectedObject.expireTime) {
                        const [ymin, xmin, ymax, xmax] = hudDetectedObject.box;
                        const startX = (xmin / 640) * canvas.width;
                        const startY = (ymin / 360) * canvas.height;
                        const boxWidth = ((xmax - xmin) / 640) * canvas.width;
                        const boxHeight = ((ymax - ymin) / 360) * canvas.height;

                        ctx.strokeStyle = '#ff6600';
                        ctx.lineWidth = 3;
                        ctx.shadowColor = '#ff6600';
                        ctx.shadowBlur = 8;
                        ctx.strokeRect(startX, startY, boxWidth, boxHeight);

                        ctx.fillStyle = 'rgba(255, 102, 0, 0.85)';
                        ctx.font = '12px Orbitron';
                        const labelText = hudDetectedObject.name;
                        const labelWidth = ctx.measureText(labelText).width;
                        ctx.fillRect(startX, startY - 20, labelWidth + 10, 20);

                        ctx.fillStyle = '#ffffff';
                        ctx.fillText(labelText, startX + 5, startY - 5);
                        ctx.shadowBlur = 0;

                        // Render Multi-Layer Spatial AR Matrix Blueprint Overlay
                        if (activeArBlueprint) {
                            const localW = 220;
                            const localH = 180;

                            // 1. Pins Layer
                            if (activeArBlueprint.pins) {
                                activeArBlueprint.pins.forEach(pin => {
                                    const px = startX + (pin.px[0] / localW) * boxWidth;
                                    const py = startY + (pin.px[1] / localH) * boxHeight;

                                    ctx.beginPath();
                                    ctx.arc(px, py, 4, 0, 2 * Math.PI);
                                    ctx.fillStyle = pin.color;
                                    ctx.fill();

                                    ctx.fillStyle = '#ffffff';
                                    ctx.font = '8px Orbitron';
                                    ctx.fillText(pin.name, px + 6, py + 3);
                                });
                            }

                            // 2. Structural Layer
                            if (activeArBlueprint.structural) {
                                activeArBlueprint.structural.forEach(struct => {
                                    const px = startX + (struct.px[0] / localW) * boxWidth;
                                    const py = startY + (struct.px[1] / localH) * boxHeight;

                                    ctx.beginPath();
                                    ctx.arc(px, py, 5, 0, 2 * Math.PI);
                                    ctx.strokeStyle = struct.color;
                                    ctx.lineWidth = 1.5;
                                    ctx.stroke();

                                    ctx.beginPath();
                                    ctx.moveTo(px - 8, py);
                                    ctx.lineTo(px + 8, py);
                                    ctx.moveTo(px, py - 8);
                                    ctx.lineTo(px, py + 8);
                                    ctx.stroke();

                                    ctx.fillStyle = '#ffffff';
                                    ctx.font = '8px Orbitron';
                                    ctx.fillText(struct.name, px + 8, py - 4);
                                });
                            }

                            // 3. Thermal hotspots Layer
                            if (activeArBlueprint.thermal_hotspots) {
                                activeArBlueprint.thermal_hotspots.forEach(hotspot => {
                                    const px = startX + (hotspot.px[0] / localW) * boxWidth;
                                    const py = startY + (hotspot.px[1] / localH) * boxHeight;

                                    const radius = 10 + Math.sin(Date.now() / 150) * 3;
                                    ctx.beginPath();
                                    ctx.arc(px, py, radius, 0, 2 * Math.PI);
                                    ctx.fillStyle = 'rgba(255, 102, 0, 0.4)';
                                    ctx.fill();
                                    ctx.strokeStyle = hotspot.color;
                                    ctx.lineWidth = 2;
                                    ctx.shadowColor = hotspot.color;
                                    ctx.shadowBlur = 10;
                                    ctx.stroke();
                                    ctx.shadowBlur = 0;

                                    ctx.fillStyle = '#ffffff';
                                    ctx.font = '8px Orbitron';
                                    ctx.fillText(`${hotspot.name} [HEAT]`, px + 12, py + 3);
                                });
                            }
                        }
                    } else {
                        activeArBlueprint = null;
                    }

                    // Throttle status bar DOM write (causes layout reflow)
                    const nowStatus = performance.now();
                    if (nowStatus - lastStatusBarTime > 500) {
                        lastStatusBarTime = nowStatus;
                        if (statusBar.innerText !== 'PROCESSING COMMAND...') {
                            statusBar.innerText = predictions && predictions.length > 0 ? 'SUBJECT IDENTIFIED' : 'VISION ACTIVE: SCANNING...';
                        }
                    }
                } catch (err) {
                    console.error("Vision Processing Exception:", err);
                } finally {
                    isDetecting = false;
                }
            }
        }
        requestAnimationFrame(detectFrame);
    }
    detectFrame();

// --- [NACHAPOL SSE STREAMING TTS ENGINE] ---
let ttsQueue = [];
let isPlayingTts = false;

async function enqueueTtsChunk(text, element = null) {
    ttsQueue.push({ text: text, element: element });
    processTtsQueue();
}

async function processTtsQueue() {
    if (isPlayingTts || ttsQueue.length === 0) return;
    isPlayingTts = true;
    isJarvisSpeaking = true;
    
    if (recognition) { try { recognition.abort(); } catch(e) {} }

    let prefetchPromise = null;

    while (ttsQueue.length > 0 || prefetchPromise) {
        let item;
        let response;
        let mainText;
        
        if (prefetchPromise) {
            const prefetched = await prefetchPromise;
            item = prefetched.item;
            response = prefetched.response;
            mainText = prefetched.mainText;
            prefetchPromise = null;
        } else {
            item = ttsQueue.shift();
            const targetElement = item.element || document.getElementById('chat-log');
            
            // Check for Holograms and Videos
            const hologramRegex = /\[WINDOW: (.*?)\]([\s\S]*?)\[END_WINDOW\]/gs;
            const videoRegex = /\[VIDEO: (.*?)\]/g;
            mainText = item.text;
            let match;
            
            while ((match = hologramRegex.exec(item.text)) !== null) {
                createHologramWindow(match[1], match[2].trim());
                mainText = mainText.replace(match[0], "");
            }
            if ((match = videoRegex.exec(item.text)) !== null) {
                createHologramWindow("Video Stream", "", match[1]);
                mainText = mainText.replace(match[0], "");
            }
            
            mainText = mainText.replace(/\[SILENT_EXECUTION\]/g, "").trim();
            if (!mainText) continue;

            try {
                response = await fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: mainText })
                });
            } catch (e) {
                console.error("TTS Stream Error:", e);
                typeWriter(mainText, targetElement, null);
                continue;
            }
        }

        if (!response || !response.ok) {
            typeWriter(mainText, item.element || document.getElementById('chat-log'), null);
            continue;
        }
        
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        currentAudio = new Audio(audioUrl);
        
        const eqElement = document.getElementById('visualizer');
        if (eqElement) eqElement.classList.add('active');

        const targetElement = item.element || document.getElementById('chat-log');
        
        // Start prefetching the NEXT chunk
        if (ttsQueue.length > 0) {
            const nextItem = ttsQueue.shift();
            let nextMainText = nextItem.text;
            const hr = /\[WINDOW: (.*?)\]([\s\S]*?)\[END_WINDOW\]/gs;
            const vr = /\[VIDEO: (.*?)\]/g;
            let m;
            while ((m = hr.exec(nextItem.text)) !== null) { nextMainText = nextMainText.replace(m[0], ""); }
            if ((m = vr.exec(nextItem.text)) !== null) { nextMainText = nextMainText.replace(m[0], ""); }
            nextMainText = nextMainText.replace(/\[SILENT_EXECUTION\]/g, "").trim();
            
            if (nextMainText) {
                prefetchPromise = fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: nextMainText })
                }).then(res => ({ item: nextItem, response: res, mainText: nextMainText })).catch(e => null);
            } else {
                ttsQueue.unshift(nextItem); // put it back if it's just hologram
            }
        }

        // Sync text typing with audio
        typeWriter(mainText, targetElement, currentAudio);

        await new Promise((resolve) => {
            currentAudio.onended = () => {
                if (eqElement) eqElement.classList.remove('active');
                resolve();
            };
            currentAudio.onerror = () => resolve();
            currentAudio.play().catch(e => resolve());
        });
    }
    
    isPlayingTts = false;
    isJarvisSpeaking = false;
    startContinuousTimer();
}
// -------------------------------------------

async function sendMessage(message = null, imageData = null) {
    if (typeof resetProactiveIdleTimer === 'function') resetProactiveIdleTimer();
    const text = message || '';
    let finalImage = imageData || selectedImageBase64;

    // Proactive Context Attachment: Auto-capture webcam frame if active
    if (!finalImage && (isVisionActive === true || (typeof webcamStream !== 'undefined' && webcamStream))) {
        const capturedFrame = captureWebcamFrame();
        if (capturedFrame) {
            finalImage = capturedFrame;
        }
    }

    if (!text && !finalImage) return;

    if (statusBar) statusBar.innerText = '';
    neuralCore.classList.remove('ha-error');

    isThinking = true; // [UX/UI INTELLIGENCE] ตั้งค่าสถานะการคิด
    let thinkingDelay = 0;
    const userDiv = document.createElement('div');
    userDiv.className = 'message user';
    if (finalImage) {
        userDiv.innerHTML = '<strong>USER:</strong> ' + (text ? text + ' ' : '') + '<span style="color: var(--neon-green); font-size: 10px;">[IMAGE ATTACHED]</span>';
    } else {
        userDiv.innerHTML = '<strong>USER:</strong> ' + text;
    }
    const chatLogEl = document.getElementById('chat-log');
    if (chatLogEl) {
        chatLogEl.appendChild(userDiv);
        chatLogEl.scrollTop = chatLogEl.scrollHeight;
    }

    playProcessingSound();
    neuralCore.classList.add('thinking');
    statusBar.innerText = 'PROCESSING COMMAND...';

    // 1. สร้างกล่องข้อความ HUD รอรับตัวอักษร
    const aiDiv = document.createElement('div');
    aiDiv.className = 'message jarvis';
    aiDiv.innerHTML = '<strong>JARVIS:</strong> ';
    const textSpan = document.createElement('span');
    aiDiv.appendChild(textSpan);
    if (chatLogEl) {
        chatLogEl.appendChild(aiDiv);
        chatLogEl.scrollTop = chatLogEl.scrollHeight;
    }

    let sentenceBuffer = "";
    let fullResponseBuffer = "";

    try {
        const response = await fetch('/chat_stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, image: finalImage })
        });

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            clearImageSelection();
            const inputEl = document.getElementById('user-input');
            if (inputEl) inputEl.value = '';
            neuralCore.classList.remove('thinking');
            isThinking = false;
            
            const data = await response.json();
            if (data.response) {
                enqueueTtsChunk(data.response, textSpan);
                statusBar.innerText = 'SYSTEM READY';
                if (data.standby === true) document.body.classList.add('standby-mode');
                else if (data.standby === false) document.body.classList.remove('standby-mode');
            }
            return;
        }

        clearImageSelection();
        const inputEl = document.getElementById('user-input');
        if (inputEl) inputEl.value = '';

        if (!response.body) throw new Error("ReadableStream not supported");

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        neuralCore.classList.remove('thinking');
        isThinking = false;
        pollHologramData();
        statusBar.innerText = 'TRANSMITTING STREAM...';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunkString = decoder.decode(value, { stream: true });
            const lines = chunkString.split('\n');

            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (!dataStr) continue;

                    try {
                        const data = JSON.parse(dataStr);
                        if (data.status === 'streaming') {
                            const chunk = data.chunk;
                            sentenceBuffer += chunk;
                            fullResponseBuffer += chunk;

                            if (/(?:\n|(?<=[.!?])\s+)/.test(chunk) || (chunk.includes(' ') && sentenceBuffer.length > 80)) {
                                const trimmed = sentenceBuffer.trim();
                                if (trimmed.length > 0) {
                                    enqueueTtsChunk(trimmed + " ", textSpan);
                                    sentenceBuffer = "";
                                }
                            }
                        } else if (data.status === 'done') {
                            if (sentenceBuffer.trim().length > 0) {
                                enqueueTtsChunk(sentenceBuffer.trim(), textSpan);
                            }
                            if (data.standby === true) document.body.classList.add('standby-mode');
                            else if (data.standby === false) document.body.classList.remove('standby-mode');
                            
                            statusBar.innerText = 'SYSTEM READY';

                            // Evaluate emergency visual hooks
                            const lowerResponse = fullResponseBuffer.toLowerCase();
                            const isEmergency = ["ฉุกเฉิน", "emergency", "red alert", "อันตราย"].some(k => lowerResponse.includes(k));
                            const isHAError = ["assistant", "ระบบบ้านอัจฉริยะ", "ขัดข้อง", "ไม่สามารถ", "error"].some(k => lowerResponse.includes(k)) &&
                                (lowerResponse.includes("ไม่") || lowerResponse.includes("error") || lowerResponse.includes("ล้มเหลว"));
                            const isOverload = ["เซิร์ฟเวอร์หลัก", "คลายความร้อน", "overloaded"].some(k => lowerResponse.includes(k));

                            if (isEmergency) {
                                document.body.classList.add('emergency-mode');
                                document.getElementById('current-ambiance').innerText = "ALERT: EMERGENCY";
                            } else if (!isHAError) {
                                document.body.classList.remove('emergency-mode');
                            }

                            if (isOverload) {
                                neuralCore.classList.add('system-overload');
                            } else {
                                neuralCore.classList.remove('system-overload');
                            }

                            if (isHAError) neuralCore.classList.add('ha-error');
                            else if (!isEmergency) neuralCore.classList.remove('ha-error');

                            startContinuousTimer();
                        } else if (data.status === 'error') {
                            textSpan.innerHTML += `<br><span style="color:red;">[ERROR]: ${data.message}</span>`;
                        }
                    } catch (e) {
                        console.error("SSE Parse Error:", e, dataStr);
                    }
                }
            }
        }


    } catch (err) {
        isThinking = false; // [UX/UI INTELLIGENCE] สิ้นสุดสถานะการคิดเมื่อเกิดข้อผิดพลาด
        neuralCore.classList.remove('thinking');
        statusBar.innerText = 'CRITICAL: LINK FAILURE - BACKEND OFFLINE';
        statusBar.className = 'system-error error';
    }
}

async function resetMemory() {
    if (confirm("ท่านแน่ใจนะว่าจะล้างความจำทั้งหมด?")) {
        try {
            const response = await fetch('/reset', { method: 'POST' });
            const data = await response.json();
            speak(data.response);
        } catch (e) {
            console.error('RESET FAILED.');
        }
    }
}

function playWakeSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(1760, audioCtx.currentTime + 0.05);
        gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.15);
    } catch (e) { }
}

function playPowerUpSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const masterGain = audioCtx.createGain();
        masterGain.connect(audioCtx.destination);
        const osc1 = audioCtx.createOscillator();
        const gain1 = audioCtx.createGain();
        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(40, audioCtx.currentTime);
        osc1.frequency.exponentialRampToValueAtTime(150, audioCtx.currentTime + 2.5);
        gain1.gain.setValueAtTime(0, audioCtx.currentTime);
        gain1.gain.linearRampToValueAtTime(0.15, audioCtx.currentTime + 0.5);
        gain1.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 2.8);
        osc1.connect(gain1); gain1.connect(masterGain);
        osc1.start(); osc1.stop(audioCtx.currentTime + 2.8);
    } catch (e) { }
}

function playHologramWhoosh() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(150, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.3);

        gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.1, audioCtx.currentTime + 0.15);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);

        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) { }
}

function playProcessingSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(440, audioCtx.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(660, audioCtx.currentTime + 0.05);
        gainNode.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.15);
    } catch (e) { }
}

function stopSpeaking() {
    speechQueue = [];
    isProcessingQueue = false;
    isJarvisSpeaking = false;
    if (currentAudio) {
        const audioToFade = currentAudio;
        currentAudio = null; // Instantly detach global ref

        try {
            let volume = audioToFade.volume;
            const fadeInterval = 15; // 15ms per step
            const steps = 10; // 10 steps total (150ms fade)
            const volStep = volume / steps;
            let currentStep = 0;

            const interval = setInterval(() => {
                currentStep++;
                if (currentStep >= steps) {
                    clearInterval(interval);
                    try {
                        audioToFade.pause();
                        audioToFade.src = "";
                    } catch (e) { }
                } else {
                    try {
                        audioToFade.volume = Math.max(0, volume - (volStep * currentStep));
                    } catch (e) {
                        clearInterval(interval);
                    }
                }
            }, fadeInterval);
        } catch (e) {
            audioToFade.pause();
            audioToFade.src = "";
        }
    }
}

function speak(text) {
    if (!text) return;
    // [OPTIMIZED] Split only by newline to prevent breaking numbered lists (e.g. "1. ") 
    // and to keep paragraphs intact within the UI bubbles.
    const sentences = text.split(/(?<=\n)/).filter(s => s.trim() !== "");
    // [MED-005] Guard: ไม่เพิ่มถ้าคิวเต็ม (ป้องกัน RAM สะสม)
    if (sentences.length === 0) {
        if (speechQueue.length < MAX_SPEECH_QUEUE) speechQueue.push(text.trim());
    } else {
        sentences.forEach(s => {
            if (speechQueue.length < MAX_SPEECH_QUEUE) speechQueue.push(s.trim());
        });
    }
    processSpeechQueue();
}

async function processSpeechQueue() {
    if (isProcessingQueue || speechQueue.length === 0) return;
    isProcessingQueue = true;
    isJarvisSpeaking = true;
    if (recognition) { try { recognition.abort(); } catch (e) { } }

    let nextAudioUrl = null;

    while (speechQueue.length > 0) {
        const text = speechQueue.shift();

        // [AUDIO KERNEL] Pre-fetch Audio Chunk
        let prefetchPromise = null;
        if (speechQueue.length > 0) {
            let nextText = speechQueue[0];
            let nextMainText = nextText.replace(/\[SILENT_EXECUTION\]/g, "").replace(/\[WINDOW: (.*?)\]([\s\S]*?)\[END_WINDOW\]/gs, "").replace(/\[VIDEO: (.*?)\]/g, "").trim();
            if (nextMainText) {
                prefetchPromise = fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: nextMainText })
                }).then(res => res.ok ? res.blob() : null).then(blob => blob ? URL.createObjectURL(blob) : null).catch(e => null);
            }
        }

        await performSpeak(text, nextAudioUrl);

        if (prefetchPromise) {
            nextAudioUrl = await prefetchPromise;
        } else {
            nextAudioUrl = null;
        }
    }
    isProcessingQueue = false;
    isJarvisSpeaking = false;
    startListening();
}

function typeWriter(text, element, audioSource) {
    return new Promise((resolve) => {
        let i = 0;
        let isFinished = false;

        const startType = (estimatedDuration = 0) => {
            let speed = (typeof estimatedDuration === 'number' && estimatedDuration > 0) ? (estimatedDuration / text.length) : 35;

            function type() {
                if (i < text.length) {
                    if (isFinished) {
                        element.innerHTML += text.substring(i).replace(/\n/g, '<br>');
                        const chatLogElement = document.getElementById('chat-log');
                        if (chatLogElement) chatLogElement.scrollTop = chatLogElement.scrollHeight;
                        resolve();
                        return;
                    }
                    let charToAppend = text.charAt(i);
                    if (charToAppend === '\n') {
                        element.innerHTML += '<br>';
                    } else {
                        element.innerHTML += charToAppend;
                    }
                    const chatLogElement = document.getElementById('chat-log');
                    if (chatLogElement) chatLogElement.scrollTop = chatLogElement.scrollHeight;
                    i++;
                    setTimeout(type, speed);
                } else resolve();
            }
            type();
        };

        if (audioSource instanceof Audio) {
            let started = false;
            audioSource.addEventListener('playing', () => {
                 if (started) return;
                 started = true;
                 const dur = (isNaN(audioSource.duration) || !isFinite(audioSource.duration)) ? 0 : audioSource.duration * 1000;
                 startType(dur);
            }, { once: true });
            audioSource.addEventListener('ended', () => { isFinished = true; });
            audioSource.addEventListener('error', () => { 
                 if (!started) { started = true; startType(0); }
                 isFinished = true; 
            }, { once: true });
            // Fallback in case playing event never fires
            setTimeout(() => { if (!started) { started = true; startType(0); } }, 2000);
        } else {
            startType(0);
        }
    });
}

function createHologramWindow(title, content, videoId = null, type = null) {
    if (title === "3D CAD EXTRACTOR") {
        try {
            window.currentSpatialARData = JSON.parse(content);
            console.log("Loaded CAD Blueprint for AR Projection", window.currentSpatialARData);
            return; // AR Blueprint mode does not spawn a text window
        } catch (e) { console.error("CAD Parse Error:", e); }
    }

    playHologramWhoosh();
    const container = document.querySelector('.hud-container');
    const win = document.createElement('div');
    win.className = 'hologram-window';

    const isSpatialMap = type === 'Spatial-Map' || (title && title.includes('SPATIAL MAP'));

    const isVideo = !!videoId;
    if (isSpatialMap) {
        win.style.width = '450px';
        win.style.minHeight = '350px';
        win.style.background = 'rgba(0, 229, 255, 0.08)'; // Cyan neon translucent
        win.style.borderColor = '#00e5ff'; // Neon Cyan border
        win.style.boxShadow = '0 0 20px rgba(0, 229, 255, 0.4), inset 0 0 15px rgba(0, 229, 255, 0.2)';
        win.style.backdropFilter = 'blur(12px)';
    } else if (isVideo) {
        win.style.width = '350px';
        win.style.minHeight = '80px';
        win.style.background = 'rgba(0, 20, 25, 0.8)';
    }

    const padding = 120;
    const widthLimit = isSpatialMap ? 500 : 350;
    const heightLimit = isSpatialMap ? 400 : (isVideo ? 100 : 350);
    const x = Math.random() * (window.innerWidth - widthLimit) + padding;
    const y = Math.random() * (window.innerHeight - heightLimit) + padding;

    win.style.left = `${x}px`;
    win.style.top = `${y}px`;

    let contentHtml = content;
    
    if (videoId && window.activeYtPlayer && typeof window.activeYtPlayer.destroy === 'function') {
        try { window.activeYtPlayer.destroy(); } catch(e) {}
    }
    let playerId = `yt-${Math.random().toString(36).substr(2, 9)}`;

    if (videoId) {
        let displayTitle = title ? title.replace('กำลังเล่น: ', '') : 'Unknown Audio';
        contentHtml = `
            <div class="custom-yt-player" style="position:relative; overflow:hidden; padding: 15px; display: flex; align-items: center; gap: 15px; background: rgba(0, 255, 255, 0.05); border-radius: 8px; border: 1px solid rgba(0, 255, 255, 0.2);">
                <div class="yt-controls" style="z-index: 2; position: relative; flex-shrink: 0;">
                    <button class="yt-playpause" id="btn-${playerId}" onclick="toggleYtPlay('${playerId}')" style="background: transparent; border: 1px solid #0ff; color: #0ff; border-radius: 50%; width: 40px; height: 40px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 10px rgba(0,255,255,0.3); transition: all 0.2s ease;">▶</button>
                </div>
                <div class="yt-info" style="z-index: 2; position: relative; flex-grow: 1; min-width: 0;">
                    <div class="yt-title" id="title-${playerId}" style="color: #fff; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 5px; font-size: 14px;">${displayTitle}</div>
                    <div class="yt-artist" id="artist-${playerId}" style="color: #0ff; font-size: 12px; opacity: 0.8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Audio Stream</div>
                </div>
                <div style="position:absolute; width:100%; height:100%; top:0px; left:0px; opacity:0.01; pointer-events:none; overflow:hidden; z-index:-1;">
                    <div id="${playerId}" style="width:100%; height:100%;"></div>
                </div>
            </div>`;
    } else if (isSpatialMap) {
        contentHtml = `<iframe width="100%" height="280" src="http://googleusercontent.com/maps.google.com/${encodeURIComponent(content)}&t=k&z=17&output=embed" frameborder="0" style="border: 0; filter: hue-rotate(180deg) brightness(0.9) contrast(1.2); pointer-events: all;" allowfullscreen></iframe>`;
    }

    win.innerHTML = `
        <div class="hologram-header">
            <span class="hologram-title">${title || 'DATA_STREAM'}</span>
            <div style="display: flex; gap: 10px; pointer-events: all;">
                <span class="hologram-btn" onclick="toggleFullscreen(this.closest('.hologram-window'))">[▢]</span>
                <span class="hologram-btn" onclick="closeHologram(this.closest('.hologram-window'))">[X]</span>
            </div>
        </div>
        <div class="hologram-content">
            ${contentHtml}
        </div>
        <div class="hologram-glitch"></div>
    `;

    container.appendChild(win);
    
    if (videoId) {
        let checkYtReady = setInterval(() => {
            if (window.YT && window.YT.Player) {
                clearInterval(checkYtReady);
                window[`player_${playerId}`] = new window.YT.Player(playerId, {
                    height: '200',
                    width: '200',
                    videoId: videoId,
                    playerVars: { 'autoplay': 1, 'controls': 0, 'disablekb': 1, 'fs': 0, 'modestbranding': 1, 'playsinline': 1, 'origin': window.location.origin },
                    events: {
                        'onReady': function(event) {
                            try {
                                let data = event.target.getVideoData();
                                if (data && data.title) document.getElementById(`title-${playerId}`).innerText = data.title;
                                if (data && data.author) document.getElementById(`artist-${playerId}`).innerText = data.author;
                                event.target.playVideo(); window.activeYtPlayer = event.target;
                            } catch(e) { console.error(e); }
                        },
                        'onStateChange': function(event) {
                            let btn = document.getElementById(`btn-${playerId}`);
                            if (!btn) return;
                            if (event.data == window.YT.PlayerState.PLAYING) {
                                btn.innerText = '⏸';
                            } else if (event.data == window.YT.PlayerState.PAUSED || event.data == window.YT.PlayerState.ENDED) {
                                btn.innerText = '▶';
                            }
                        }
                    }
                });
            }
        }, 200);
        setTimeout(() => clearInterval(checkYtReady), 10000);
    }

    makeDraggable(win);
}

// Custom YT Player toggle logic
function toggleYtPlay(playerId) {
    let player = window[`player_${playerId}`];
    if (player && typeof player.getPlayerState === 'function') {
        let state = player.getPlayerState();
        if (state === YT.PlayerState.PLAYING) {
            player.pauseVideo();
        } else {
            player.playVideo();
        }
    }
}

function makeDraggable(el) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

    el.style.cursor = 'move';
    el.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        // Prevent dragging if fullscreen mode is active
        if (el.classList.contains('fullscreen')) return;

        // Prevent dragging if clicking directly on a button with the class .hologram-btn
        if (e.target.classList.contains('hologram-btn') || e.target.closest('.hologram-btn')) {
            return;
        }

        // Prevent dragging if clicking button, input, anchor or iframe element
        if (e.target.closest('button') || e.target.closest('input') || e.target.closest('a') || e.target.closest('iframe')) {
            return;
        }

        e = e || window.event;
        e.preventDefault();

        pos3 = e.clientX;
        pos4 = e.clientY;

        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();

        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;

        el.style.top = (el.offsetTop - pos2) + "px";
        el.style.left = (el.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

function onHandResults(results) {
    if (results.multiHandLandmarks) {
        latestHandLandmarks = results.multiHandLandmarks;
        processHandTrackingForDrag(latestHandLandmarks);
    } else {
        latestHandLandmarks = null;
        hasClickedThisPinch = false;
        if (activeDraggedHologram) {
            activeDraggedHologram.style.transition = "";
            activeDraggedHologram = null;
            neuralCore.classList.remove('core-vibrating');
        }
    }
}

function processHandTrackingForDrag(landmarks) {
    if (!landmarks || landmarks.length === 0) {
        hasClickedThisPinch = false;
        if (activeDraggedHologram) {
            activeDraggedHologram.style.transition = "";
            activeDraggedHologram = null;
            neuralCore.classList.remove('core-vibrating');
        }
        return;
    }

    const points = landmarks[0];
    const wrist = points[0];
    const thumbTip = points[4];
    const indexTip = points[8];

    if (!thumbTip || !indexTip) return;

    // 1. นำระบบยิง API ไปควบคุมเมาส์ระดับ OS ออกทั้งหมด
    // Sensitivity scaling factor (Comfortable 1.8x movement mapping)
    const SENSITIVITY = 1.8;

    // Calculate 2D Euclidean distance (ignoring Z-axis for better reliability)
    const dx = thumbTip.x - indexTip.x;
    const dy = thumbTip.y - indexTip.y;
    const distance = Math.hypot(dx, dy);

    const PINCH_THRESHOLD = 0.08; // เพิ่มระยะ Pinch ให้จับง่ายขึ้น

    // Map and normalize coordinates with horizontal mirroring (1 - x)
    const pinchX = 1 - (thumbTip.x + indexTip.x) / 2;
    const pinchY = (thumbTip.y + indexTip.y) / 2;

    // Apply sensitivity centered around 0.5 coordinate
    let scaledPinchX = (pinchX - 0.5) * SENSITIVITY + 0.5;
    let scaledPinchY = (pinchY - 0.5) * SENSITIVITY + 0.5;

    // Clamp coordinates
    scaledPinchX = Math.max(0.0, Math.min(1.0, scaledPinchX));
    scaledPinchY = Math.max(0.0, Math.min(1.0, scaledPinchY));

    const raw_x_px = scaledPinchX * window.innerWidth;
    const raw_y_px = scaledPinchY * window.innerHeight;

    // 2. ปรับความสเถียรด้วย Exponential Moving Average (EMA) เพื่อลดอาการกระตุก
    const SMOOTHING_FACTOR = 0.25; // 0.25 ให้ความนุ่มนวลแต่ยังตามมือทัน
    if (smoothedHandX === null) {
        smoothedHandX = raw_x_px;
        smoothedHandY = raw_y_px;
    } else {
        smoothedHandX = smoothedHandX + (raw_x_px - smoothedHandX) * SMOOTHING_FACTOR;
        smoothedHandY = smoothedHandY + (raw_y_px - smoothedHandY) * SMOOTHING_FACTOR;
    }

    // สร้างหรืออัปเดตตำแหน่ง Hand Cursor (จุดที่เล็ง)
    let cursor = document.getElementById('hand-cursor');
    if (!cursor) {
        cursor = document.createElement('div');
        cursor.id = 'hand-cursor';
        cursor.className = 'hand-cursor';
        document.body.appendChild(cursor);
    }
    cursor.style.left = `${smoothedHandX}px`;
    cursor.style.top = `${smoothedHandY}px`;

    if (distance < PINCH_THRESHOLD) {
        if (!activeDraggedHologram && currentHoveredHologram) {
            // ดึงหน้าต่างที่ Hover อยู่มาเป็นเป้าหมายลาก
            activeDraggedHologram = currentHoveredHologram;
            console.log("[VISION CENTRAL CORE] Pinch-to-Drag bound to window:", activeDraggedHologram.querySelector('.hologram-title')?.innerText || "Hologram Window");
        }

        if (activeDraggedHologram) {
            const width = activeDraggedHologram.offsetWidth || 350;
            const height = activeDraggedHologram.offsetHeight || 300;

            // เคลื่อนย้ายด้วยพิกัดที่ผ่านการ Smooth แล้ว
            activeDraggedHologram.style.left = `${smoothedHandX - width / 2}px`;
            activeDraggedHologram.style.top = `${smoothedHandY - height / 2}px`;
            activeDraggedHologram.style.transition = "none";

            // เปลี่ยนกรอบจากสีเหลือง (Hover) เป็นสีส้ม (Active Drag)
            activeDraggedHologram.style.borderColor = 'var(--ironman-orange)';
            activeDraggedHologram.style.boxShadow = '0 0 20px rgba(255, 102, 0, 0.8), inset 0 0 15px rgba(255, 102, 0, 0.4)';

            neuralCore.classList.add('core-vibrating');
        }

        // อัปเดตเคอร์เซอร์เมื่อจีบ
        cursor.style.borderColor = '#ff6600';
        cursor.style.boxShadow = '0 0 15px #ff6600';
        cursor.style.width = '15px';
        cursor.style.height = '15px';
    } else {
        // คืนสถานะเคอร์เซอร์เมื่อปล่อย
        cursor.style.borderColor = '#00ffcc';
        cursor.style.boxShadow = '0 0 10px #00ffcc, inset 0 0 5px #00ffcc';
        cursor.style.width = '20px';
        cursor.style.height = '20px';

        // คลายการหยิบ
        if (activeDraggedHologram) {
            console.log("[VISION CENTRAL CORE] Pinch-to-Drag released.");
            activeDraggedHologram.style.transition = ""; // คืนค่า Transition CSS เดิม
            activeDraggedHologram.style.borderColor = ''; // คืนค่าสีเดิม
            activeDraggedHologram.style.boxShadow = '';
            activeDraggedHologram = null;
            neuralCore.classList.remove('core-vibrating');
        }

        // 3. ระบบตรวจจับการ Hover ล่วงหน้า (Throttled เพื่อประหยัด CPU)
        const now = performance.now();
        if (now - lastHoverCheckTime > 100) { // ทำงานแค่ 10 ครั้งต่อวินาที
            lastHoverCheckTime = now;

            const windows = document.querySelectorAll('.hologram-window');
            let closestWin = null;
            let minDistance = Infinity;
            const boundingThreshold = 300; // ระยะ Hover 

            windows.forEach(win => {
                // ล้างสถานะ Hover เก่าทั้งหมดก่อน
                win.classList.remove('hologram-hover');

                if (win.classList.contains('fullscreen')) return;

                const rect = win.getBoundingClientRect();
                const winX = rect.left + rect.width / 2;
                const winY = rect.top + rect.height / 2;

                const dist = Math.sqrt(Math.pow(winX - smoothedHandX, 2) + Math.pow(winY - smoothedHandY, 2));
                if (dist < minDistance) {
                    minDistance = dist;
                    closestWin = win;
                }
            });

            if (closestWin && minDistance < boundingThreshold) {
                currentHoveredHologram = closestWin;
                currentHoveredHologram.classList.add('hologram-hover');
            } else {
                currentHoveredHologram = null;
            }
        }
    }
}

function closeHologram(el) {
    if (!el) return;
    el.classList.add('hologram-exit');
    setTimeout(() => el.remove(), 400);
}

function closeAllHolograms() {
    const windows = document.querySelectorAll('.hologram-window');
    windows.forEach(win => closeHologram(win));
}

function toggleFullscreen(el) {
    el.classList.toggle('fullscreen');
}

function startContinuousTimer() {
    if (timeoutTimer) {
        clearTimeout(timeoutTimer);
        timeoutTimer = null;
    }
    if (isContinuousMode) {
        statusBar.innerText = 'JARVIS: LISTENING (CONTINUOUS)...';
        timeoutTimer = setTimeout(() => {
            isContinuousMode = false;
            statusBar.innerText = 'JARVIS: LISTENING (STANDBY)';
            timeoutTimer = null;
        }, 15000);
    }
}

function performSpeak(text, preFetchedUrl = null) {
    if (timeoutTimer) {
        clearTimeout(timeoutTimer);
        timeoutTimer = null;
    }
    return new Promise(async (resolve) => {
        let isSilent = false;
        if (text && text.includes('[SILENT_EXECUTION]')) {
            isSilent = true;
            text = text.replace(/\[SILENT_EXECUTION\]/g, "");
        }

        let mainText = text;
        const hologramRegex = /\[WINDOW: (.*?)\]([\s\S]*?)\[END_WINDOW\]/gs;
        const windows = [];
        const videoRegex = /\[VIDEO: (.*?)\]/g;
        let match;
        let videoId = null;

        while ((match = hologramRegex.exec(text)) !== null) {
            windows.push({ title: match[1], content: match[2].trim() });
            mainText = mainText.replace(match[0], "");
        }
        if ((match = videoRegex.exec(text)) !== null) {
            videoId = match[1];
            mainText = mainText.replace(match[0], "");
        }
        mainText = mainText.trim();
        if (!mainText && (windows.length > 0 || videoId)) mainText = "แสดงผลข้อมูลบนชุดโฮโลแกรมเรียบร้อยครับท่าน";

        const div = document.createElement('div');
        div.className = 'message jarvis';
        div.innerHTML = '<strong>JARVIS:</strong> ';
        const textSpan = document.createElement('span');
        div.appendChild(textSpan);
        const chatLogElement = document.getElementById('chat-log');
        if (chatLogElement) chatLogElement.appendChild(div);

        if (videoId) createHologramWindow("Video Stream", "", videoId);
        windows.forEach(w => createHologramWindow(w.title, w.content));

        if (isSilent) {
            if (mainText) {
                await typeWriter(mainText, textSpan, null);
            }
            startContinuousTimer();
            resolve();
            return;
        }

        if (!mainText) {
            startContinuousTimer();
            resolve();
            return;
        }

        try {
            let audioUrl = preFetchedUrl;
            if (!audioUrl) {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: mainText })
                });

                if (!response.ok) throw new Error('TTS API Failed');

                const blob = await response.blob();
                audioUrl = URL.createObjectURL(blob);
            }

            currentAudio = new Audio(audioUrl);
            currentAudio.preservesPitch = false;

            typeWriter(mainText, textSpan, currentAudio);

            currentAudio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                startContinuousTimer();
                resolve();
            };

            currentAudio.play().catch(e => {
                console.error("[AUDIO KERNEL] PLAYBACK STREAM INTERRUPTED:", e);
                typeWriter(mainText, textSpan, null);
                startContinuousTimer();
                resolve();
            });

        } catch (error) {
            console.error("[AUDIO KERNEL] SYNTHESIS ENGINE EXCEPTION:", error);
            typeWriter(mainText, textSpan, null);
            startContinuousTimer();
            resolve();
        }
    });
}

function startListening() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        try {
            console.warn("Web Speech API is not supported in this browser. Switching to text-only mode.");
            statusBar.innerText = '[SYSTEM DIAGNOSTIC] SPEECH RECOGNITION UNAVAILABLE. TEXT OVERRIDE ACTIVE.';
        } catch (err) {
            console.error("Failed to update status bar for non-supported speech API:", err);
        }
        return;
    }

    initVoiceVisualizer(); // [VOICE REACTIVITY] เริ่มต้นวิเคราะห์คลื่นเสียง

    if (!recognition) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.lang = 'th-TH';
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            neuralCore.classList.add('listening');
            statusBar.innerText = 'JARVIS: LISTENING...';
            neuralCore.classList.remove('ha-error');
        };

        recognition.onerror = (event) => {
            console.error("[AUDIO KERNEL] SPEECH RECOGNITION HARDWARE FAULT:", event.error);
            let errorMessage = "เกิดข้อผิดพลาดในการประมวลผลเสียงครับท่าน";
            switch (event.error) {
                case 'no-speech':
                    errorMessage = "ขออภัยครับท่าน ผมไม่ได้ยินเสียงของท่านเลย";
                    break;
                case 'audio-capture':
                    errorMessage = "เกรงว่าไมโครโฟนของท่านจะทำงานผิดปกติครับ";
                    break;
                case 'not-allowed':
                case 'service-not-allowed':
                    errorMessage = "ขออภัยครับท่าน ผมไม่ได้รับอนุญาตให้เข้าถึงไมโครโฟนของท่าน";
                    if (recognition) {
                        recognition.stop();
                        recognition = null;
                    }
                    break;
                case 'network':
                    errorMessage = "การเชื่อมต่อเครือข่ายขัดข้องครับท่าน";
                    break;
                case 'bad-grammar':
                    errorMessage = "กระผมไม่เข้าใจคำสั่งครับท่าน โปรดพูดให้ชัดเจนขึ้น";
                    break;
                case 'language-not-supported':
                    errorMessage = "ภาษาที่ท่านใช้ไม่รองรับครับท่าน";
                    break;
                default:
                    errorMessage = `เกิดข้อผิดพลาดที่ไม่คาดคิด: ${event.error} ครับท่าน`;
            }
            statusBar.innerText = `[AUDIO KERNEL] EXCEPTION: ${errorMessage}`;
            neuralCore.classList.add('ha-error');
        };

        let fastSpeechTimer = null;
        let lastDispatchedSpeech = "";
        let lastSpeechDispatchTime = 0;

        const processVoiceInput = (rawTranscript) => {
            if (!rawTranscript || rawTranscript.trim().length < 2) return;
            const cleanRaw = rawTranscript.trim();
            const now = Date.now();
            if (cleanRaw === lastDispatchedSpeech && now - lastSpeechDispatchTime < 2500) {
                return; // Prevent duplicate execution within cooldown
            }

            const lowerTranscript = cleanRaw.toLowerCase();
            const wakeWordRegex = /jarvis|จาร์วิส|จารวิส|จาวิส|จาวิด|จาวิท|ชาวิด|จาวิศ|จาวิช|จาหวิด|จารวิช|ชาวิศ/i;

            const extractAndCleanCommand = (transcript) => {
                const wakeWordGlobalRegex = /jarvis|จาร์วิส|จารวิส|จาวิส|จาวิด|จาวิท|ชาวิด|จาวิศ|จาวิช|จาหวิด|จารวิช|ชาวิศ/gi;
                let cmd = transcript.replace(wakeWordGlobalRegex, "").trim();
                const suffixRegex = /(ให้ฟังหน่อย|ฟังหน่อย|ให้หน่อย|หน่อย|ด้วยนะ|ด้วยดิ|นะ|ซิ|ดิ|ที|จัดมาเลย)$/i;
                let prevCmd;
                do {
                    prevCmd = cmd;
                    cmd = cmd.replace(suffixRegex, "").trim();
                } while (cmd !== prevCmd);
                return cmd;
            };

            const hasWakeWord = wakeWordRegex.test(lowerTranscript);
            let cleanedCommand = extractAndCleanCommand(cleanRaw);

            if (hasWakeWord && cleanedCommand === "") {
                lastDispatchedSpeech = cleanRaw;
                lastSpeechDispatchTime = now;
                if (!isContinuousMode) { isContinuousMode = true; playWakeSound(); }
                speak(Math.random() > 0.5 ? "ครับเจ้านาย" : "ครับผม");
                statusBar.innerText = 'JARVIS: AWAITING COMMAND...';
                return;
            }

            if (isContinuousMode || hasWakeWord) {
                lastDispatchedSpeech = cleanRaw;
                lastSpeechDispatchTime = now;
                if (!isContinuousMode) { isContinuousMode = true; playWakeSound(); }
                const finalCommand = cleanedCommand;
                if (finalCommand === "" || finalCommand.length < 2) {
                    speak("ครับเจ้านาย?");
                    statusBar.innerText = 'JARVIS: AWAITING COMMAND...';
                } else {
                    statusBar.innerText = `PROCESSING: ${finalCommand.toUpperCase()}`;

                    const lowerCommand = finalCommand.toLowerCase();

                    if (/(เซฟภาพนี้เข้าโฟลเดอร์โปรเจกต์|บันทึกภาพวงจร|บันทึกภาพพิมพ์เขียว|archive snapshot|save schematic)/i.test(lowerCommand)) {
                        if (!isVisionActive) {
                            speak("เกรงว่าระบบดวงตากล้องเว็บแคมจะยังไม่ได้เปิดใช้งาน กระผมไม่สามารถสแนปภาพคลังข้อมูลได้ครับเจ้านาย");
                            return;
                        }
                        const snapshotBase64 = captureWebcamFrame();
                        if (snapshotBase64) {
                            statusBar.innerText = 'ARCHIVING IMAGE TO DATABASE...';
                            fetch('/chat', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ message: "เรียกใช้เครื่องมือ archive_schematic_snapshot", image: snapshotBase64 })
                            }).then(res => res.json()).then(data => {
                                if (data && data.response) speak(data.response);
                                pollHologramData();
                            }).catch(err => {
                                statusBar.innerText = 'CRITICAL: ARCHIVE LINK FAILED';
                            });
                        }
                        return;
                    }
                    if (/(สิ่งนี้คืออะไร|นี่คืออะไร|มันคืออะไร)/i.test(lowerCommand)) {
                        if (!isVisionActive) return;
                        const snapshotBase64 = captureWebcamFrame();
                        if (snapshotBase64) {
                            statusBar.innerText = 'SCANNING COGNITIVE OBJECT...';
                            fetch('/chat', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ message: "เรียกใช้เครื่องมือ analyze_hud_object", image: snapshotBase64 })
                            }).then(res => res.json()).then(data => {
                                const cleanRes = JSON.parse(data.response);
                                if (cleanRes && cleanRes.box) {
                                    hudDetectedObject = {
                                        name: cleanRes.object_name.toUpperCase(),
                                        english_name: cleanRes.english_name,
                                        box: cleanRes.box,
                                        expireTime: Date.now() + 15000
                                    };
                                    speak(`สิ่งของสิ่งนี้คือ ${cleanRes.object_name} ครับเจ้านาย`);
                                }
                            });
                        }
                        return;
                    }
                    if (/(แสดงพิมพ์เขียวการต่อสายไฟ|แสดงพิมพ์เขียว|เปิดแบบประกอบ|show blueprint)/i.test(lowerCommand)) {
                        if (!hudDetectedObject || Date.now() > hudDetectedObject.expireTime) return;
                        const targetObj = hudDetectedObject.english_name || "arduino_uno";
                        fetch('/chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: "เรียกใช้เครื่องมือ get_assembly_blueprint", object_name: targetObj })
                        }).then(res => res.json()).then(data => {
                            const cleanRes = JSON.parse(data.response);
                            if (cleanRes) {
                                activeArBlueprint = cleanRes;
                                speak("ระบบดาวน์โหลดโมเดลพิมพ์เขียว AR เสร็จสมบูรณ์แล้วครับเจ้านาย");
                            }
                        });
                        return;
                    }
                    const activateLaserKeywords = ["เปิดระบบวัดระยะ", "เปิดเลเซอร์วัดระยะ", "เปิดระบบเลเซอร์", "activate rangefinder", "laser on", "จาวิด วัดขนาดให้ที", "วัดขนาดให้ที"];
                    const deactivateLaserKeywords = ["ปิดระบบวัดระยะ", "ปิดเลเซอร์วัดระยะ", "ปิดระบบเลเซอร์", "deactivate rangefinder", "laser off"];

                    if (activateLaserKeywords.some(keyword => lowerCommand.includes(keyword))) {
                        if (!webcamStream) {
                            toggleCamera();
                        }
                        if (!isSpatialMode) {
                            toggleSpatialMode();
                        }
                        speak("เปิดระบบเลเซอร์วัดระยะเรียบร้อยครับเจ้านาย");
                        statusBar.innerText = 'LASER RANGEFINDER: ACTIVE';
                    } else if (deactivateLaserKeywords.some(keyword => lowerCommand.includes(keyword))) {
                        if (isSpatialMode) {
                            toggleSpatialMode();
                        }
                        const laserDisplay = document.getElementById('laser-range-display');
                        if (laserDisplay) laserDisplay.style.display = 'none';

                        speak("ปิดระบบเลเซอร์วัดระยะแล้วครับ");
                        statusBar.innerText = 'LASER RANGEFINDER: OFFLINE';
                    } else {
                        sendMessage(finalCommand);
                    }
                }
            }
        };

        recognition.onresult = (event) => {
            const resultIndex = event.resultIndex;
            const result = event.results[resultIndex];
            const currentTranscript = (result && result[0] && result[0].transcript) ? result[0].transcript.trim() : "";

            neuralCore.classList.add('core-vibrating');
            setTimeout(() => neuralCore.classList.remove('core-vibrating'), 50);
            if (isJarvisSpeaking) stopSpeaking();

            // Relaxed confidence gate: only reject if confidence is known and extremely low (<0.25)
            if (result[0].confidence && result[0].confidence > 0 && result[0].confidence < 0.25) return;

            if (result.isFinal) {
                if (fastSpeechTimer) {
                    clearTimeout(fastSpeechTimer);
                    fastSpeechTimer = null;
                }
                processVoiceInput(currentTranscript);
            } else {
                // Fast-Path: trigger interim speech after 650ms of silence
                if (currentTranscript.length >= 3) {
                    if (fastSpeechTimer) clearTimeout(fastSpeechTimer);
                    fastSpeechTimer = setTimeout(() => {
                        processVoiceInput(currentTranscript);
                        fastSpeechTimer = null;
                    }, 650);
                }
            }
        };

        recognition.onend = () => {
            neuralCore.classList.remove('listening');
            if (recognition) {
                try {
                    recognition.start();
                } catch (e) {
                    console.error("[AUDIO KERNEL] ENGINE RESTART FAILURE:", e);
                    statusBar.innerText = '[CRITICAL] AUDIO INPUT SUBSYSTEM FAILURE';
                    neuralCore.classList.add('ha-error');
                }
            }
        };
    }
    try { recognition.start(); } catch (e) { }
}

// [NACHAPOL PROTOCOL] เริ่มระบบดักจับเสียง (Voice Recognition) ทันทีที่เจ้านายคลิกพื้นที่ใดก็ได้บนหน้าจอเป็นครั้งแรก
// เพื่อให้เป็นไปตามนโยบายความปลอดภัยและสิทธิ์การเข้าถึงไมโครโฟนของเบราว์เซอร์
document.addEventListener('DOMContentLoaded', () => {
    startListening();
});

document.addEventListener('click', function (e) {
    const target = e.target.closest('button');
    if (!target) return;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    target.appendChild(ripple);
    const rect = target.getBoundingClientRect();
    ripple.style.left = `${e.clientX - rect.left}px`;
    ripple.style.top = `${e.clientY - rect.top}px`;
    setTimeout(() => ripple.remove(), 600);
});

let isPollingRunning = false;

async function pollHologramData() {
    if (isPollingRunning) return;
    isPollingRunning = true;

    try {
        if (!isThinking) {
            const response = await fetch('/api/holograms');
            const holograms = await response.json();
            if (holograms && holograms.length > 0) {
                holograms.forEach(hologram => {
                    createHologramWindow(hologram.title, hologram.content, hologram.video_id, hologram.type);
                });
            }
        }
    } catch (error) {
        console.error("Error polling hologram data:", error);
    } finally {
        isPollingRunning = false;
        setTimeout(pollHologramData, 1000);
    }
}

pollHologramData();

// Initialize calibration and slider matrix settings on page load
loadCalibrationFromDB();
initCalibrationSliders();

// --- Image upload and vision integration logic ---
let selectedImageBase64 = null;

function processAndPreviewImage(file) {
    const reader = new FileReader();
    reader.onload = function (event) {
        const img = new Image();
        img.onload = function () {
            // Resize logic: max width/height of 800px
            let width = img.width;
            let height = img.height;
            const maxSize = 800;

            if (width > height) {
                if (width > maxSize) {
                    height *= maxSize / width;
                    width = maxSize;
                }
            } else {
                if (height > maxSize) {
                    width *= maxSize / height;
                    height = maxSize;
                }
            }

            // Draw compressed image to a canvas
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);

            // Compress image to JPEG quality 0.7
            const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
            selectedImageBase64 = dataUrl.split(',')[1];

            showImagePreview(dataUrl);
        };
        img.src = event.target.result;
    };
    reader.readAsDataURL(file);
}

function captureWebcamFrame() {
    const video = document.getElementById('webcam');
    if (!video || !webcamStream) {
        return null;
    }
    try {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Compress as JPEG 0.7 to save bandwidth
        const base64Data = canvas.toDataURL('image/jpeg', 0.7);
        return base64Data.split(',')[1];
    } catch (e) {
        console.error("[VISION CORE] FRAME CAPTURE EXCEPTION:", e);
        return null;
    }
}

function showImagePreview(dataUrl) {
    let previewContainer = document.getElementById('image-preview-container');
    if (!previewContainer) return;

    previewContainer.innerHTML = '';

    // Relative wrapper for laser scanner radar animation overlay
    const wrapper = document.createElement('div');
    wrapper.style.position = 'relative';
    wrapper.style.display = 'inline-block';
    wrapper.style.width = '40px';
    wrapper.style.height = '40px';
    wrapper.style.overflow = 'hidden';
    wrapper.style.borderRadius = '3px';
    wrapper.style.border = '1px solid var(--neon-green)';

    const img = document.createElement('img');
    img.src = dataUrl;
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';

    const scanner = document.createElement('div');
    scanner.className = 'laser-scanner-line';

    wrapper.appendChild(img);
    wrapper.appendChild(scanner);

    const removeBtn = document.createElement('span');
    removeBtn.innerHTML = '&times;';
    removeBtn.style.color = '#ff4b4b';
    removeBtn.style.cursor = 'pointer';
    removeBtn.style.fontSize = '18px';
    removeBtn.style.fontWeight = 'bold';
    removeBtn.style.marginLeft = '8px';
    removeBtn.style.userSelect = 'none';
    removeBtn.title = 'Remove Image';
    removeBtn.addEventListener('click', clearImageSelection);

    previewContainer.appendChild(wrapper);
    previewContainer.appendChild(removeBtn);
    previewContainer.style.display = 'flex';
}

function clearImageSelection() {
    selectedImageBase64 = null;
    const fileInput = document.getElementById('image-upload-input');
    if (fileInput) fileInput.value = '';

    const previewContainer = document.getElementById('image-preview-container');
    if (previewContainer) {
        previewContainer.style.display = 'none';
        previewContainer.innerHTML = '';
    }
}

function initImageUploadUI() {
    const inputArea = document.querySelector('.input-area');
    if (inputArea && !document.getElementById('image-upload-input')) {
        // Inject Laser Scan animation CSS rules dynamically
        const scanStyle = document.createElement('style');
        scanStyle.innerHTML = `
            @keyframes nachapol-laser-scan {
                0% { top: 0%; opacity: 0.3; }
                50% { top: 100%; opacity: 0.8; }
                100% { top: 0%; opacity: 0.3; }
            }
            .laser-scanner-line {
                position: absolute;
                left: 0;
                width: 100%;
                height: 2px;
                background: linear-gradient(90deg, transparent, #00c8ff, transparent);
                box-shadow: 0 0 8px #00c8ff, 0 0 12px rgba(0, 200, 255, 0.5);
                animation: nachapol-laser-scan 1.5s infinite linear;
                pointer-events: none;
                z-index: 10;
            }
        `;
        document.head.appendChild(scanStyle);

        // Create hidden input file
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.id = 'image-upload-input';
        fileInput.accept = 'image/*';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);

        // Create attachment button
        const attachBtn = document.createElement('button');
        attachBtn.className = 'nachapol-btn';
        attachBtn.id = 'attach-btn';
        attachBtn.type = 'button';
        attachBtn.innerHTML = '+';
        attachBtn.style.padding = '10px';
        attachBtn.style.marginRight = '10px';
        attachBtn.style.fontSize = '14px';
        attachBtn.style.display = 'flex';
        attachBtn.style.alignItems = 'center';
        attachBtn.style.justifyContent = 'center';
        attachBtn.style.cursor = 'pointer';
        attachBtn.addEventListener('click', () => fileInput.click());

        // Insert attachment button at the beginning of the input area (left of text box)
        inputArea.insertBefore(attachBtn, inputArea.firstChild);

        // Create preview container
        const previewContainer = document.createElement('div');
        previewContainer.id = 'image-preview-container';
        previewContainer.style.display = 'none';
        previewContainer.style.position = 'absolute';
        previewContainer.style.bottom = '65px';
        previewContainer.style.left = '10px';
        previewContainer.style.backgroundColor = 'rgba(0, 20, 20, 0.95)';
        previewContainer.style.border = '1px solid var(--neon-green)';
        previewContainer.style.padding = '5px 8px';
        previewContainer.style.borderRadius = '4px';
        previewContainer.style.alignItems = 'center';
        previewContainer.style.justifyContent = 'center';
        previewContainer.style.zIndex = '100';
        previewContainer.style.boxShadow = '0 0 10px rgba(55, 226, 177, 0.4)';

        inputArea.appendChild(previewContainer);

        // File selection event listener
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                processAndPreviewImage(file);
            }
        });

        // Paste event listener on the user input text box
        const userInput = document.getElementById('user-input');
        if (userInput) {
            userInput.addEventListener('paste', (e) => {
                const items = (e.clipboardData || e.originalEvent.clipboardData).items;
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') === 0) {
                        const file = items[i].getAsFile();
                        processAndPreviewImage(file);
                        e.preventDefault();
                        break;
                    }
                }
            });

            // Interrupt JARVIS when user starts typing
            userInput.addEventListener('input', () => {
                if (isJarvisSpeaking) {
                    stopSpeaking();
                    console.log("[JARVIS] Interrupted by typing.");
                }
            });
        }
    }
}

// [SYSTEM DIAGNOSTIC PROTOCOL] Detection and runtime adjustment script for iPhone 13 & iPad Air 6 Portrait Mode
function checkDeviceOrientationAndSize() {
    try {
        const width = window.innerWidth;
        const height = window.innerHeight;
        const isPortrait = window.matchMedia("(orientation: portrait)").matches;

        // Clear previous state classes to prevent collision
        document.body.classList.remove('iphone-13-portrait', 'ipad-air-6-portrait');

        // Detect iPhone 13 Portrait Viewport (390x844 layout)
        const isIPhone13 = (width === 390 && height === 844) ||
            (isPortrait && Math.abs(width - 390) < 5 && Math.abs(height - 844) < 15);

        // Detect iPad Air 6 Portrait Viewport (820x1180 or 1024x1366 layout)
        const isIPadAir6 = (isPortrait && (
            (width === 820 && height === 1180) ||
            (width === 1024 && height === 1366) ||
            (Math.abs(width - 820) < 10 && Math.abs(height - 1180) < 20) ||
            (Math.abs(width - 1024) < 10 && Math.abs(height - 1366) < 20)
        ));

        if (isIPhone13) {
            document.body.classList.add('iphone-13-portrait');
            console.log("[HUD RESPONSIVE DIAGNOSTIC] iPhone 13 Portrait detected. Scale factor aligned to 0.35.");
            const ambientTag = document.getElementById('current-ambiance');
            if (ambientTag && (ambientTag.innerText === 'SYSTEM IDLE' || ambientTag.innerText.includes('OPTIMIZED'))) {
                ambientTag.innerText = 'IPHONE 13 PORTRAIT OPTIMIZED';
            }
        } else if (isIPadAir6) {
            document.body.classList.add('ipad-air-6-portrait');
            console.log("[HUD RESPONSIVE DIAGNOSTIC] iPad Air 6 Portrait detected. Scale factor aligned to 0.68.");
            const ambientTag = document.getElementById('current-ambiance');
            if (ambientTag && (ambientTag.innerText === 'SYSTEM IDLE' || ambientTag.innerText.includes('OPTIMIZED'))) {
                ambientTag.innerText = 'IPAD AIR 6 PORTRAIT OPTIMIZED';
            }
        }

        // Dynamic Canvas Overlay Adjustment based on container dimensions
        const canvas = document.getElementById('vision-overlay');
        const video = document.getElementById('webcam');
        if (canvas && video && webcamStream && video.readyState === 4) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
        }
    } catch (error) {
        console.error("[SYSTEM DIAGNOSTIC] Exception in responsive detection routine:", error);
    }
}

// Attach event listeners safely
try {
    window.addEventListener('resize', checkDeviceOrientationAndSize);
    window.addEventListener('orientationchange', checkDeviceOrientationAndSize);
} catch (e) {
    console.error("[SYSTEM DIAGNOSTIC] Failed to attach responsive event listeners:", e);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        try {
            initImageUploadUI();
            checkDeviceOrientationAndSize();
        } catch (e) {
            console.error("[HUD DIAGNOSTIC] BOOT SEQUENCE FAILED:", e);
        }
    });
} else {
    try {
        initImageUploadUI();
        checkDeviceOrientationAndSize();
    } catch (e) {
        console.error("[HUD DIAGNOSTIC] BOOT SEQUENCE FAILED:", e);
    }
}

// --- Proactive Inquiry Watchdog (Activity Watchdog) ---
let lastUserActivityTime = Date.now();
let hasTriggeredProactive = false;
let proactiveTimerInterval = null;

function resetProactiveIdleTimer() {
    lastUserActivityTime = Date.now();
    hasTriggeredProactive = false;
}

// Reset idle timer on user actions
document.addEventListener('mousemove', resetProactiveIdleTimer);
document.addEventListener('keydown', resetProactiveIdleTimer);
document.addEventListener('click', resetProactiveIdleTimer);
document.addEventListener('input', resetProactiveIdleTimer);

function startProactiveWatchdog() {
    if (proactiveTimerInterval) clearInterval(proactiveTimerInterval);

    proactiveTimerInterval = setInterval(async () => {
        // If thinking or speaking, don't trigger
        if (isThinking || isJarvisSpeaking) {
            resetProactiveIdleTimer();
            return;
        }

        const inputEl = document.getElementById('user-input');
        const inputVal = inputEl ? inputEl.value : '';
        const isCameraActive = (isVisionActive === true || (typeof webcamStream !== 'undefined' && webcamStream !== null));

        const idleDuration = (Date.now() - lastUserActivityTime) / 1000;

        if (idleDuration >= 15 && !hasTriggeredProactive) {
            // Trigger if typing is stuck or camera is active with no commands
            if (inputVal.trim() !== '' || isCameraActive) {
                hasTriggeredProactive = true;
                try {
                    const response = await fetch('/api/proactive-trigger', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            current_input: inputVal,
                            camera_active: isCameraActive
                        })
                    });
                    if (response.ok) {
                        const data = await response.json();
                        if (data && data.response) {
                            speak(data.response);
                        }
                    }
                } catch (e) {
                    console.error("[PROACTIVE VISION WATCHDOG] Trigger failure:", e);
                }
            }
        }
    }, 1000);
}

// Start watchdog on boot
try {
    startProactiveWatchdog();
} catch (e) {
    console.error("[PROACTIVE WATCHDOG] Start failed:", e);
}

// --- Telemetry Monitoring and Warning Alerts ---
let lastTelemetryAlertTime = 0;

function startTelemetryPolling() {
    setInterval(async () => {
        try {
            const response = await fetch('/api/telemetry');
            if (response.ok) {
                const data = await response.json();

                const idleStates = [
                    '',
                    'SYSTEM ONLINE',
                    'SYSTEM READY',
                    'JARVIS IS ACTIVE',
                    'AWAITING DIRECTIVES...'
                ];
                const curText = statusBar.innerText.trim();

                if (curText === '' || idleStates.some(s => curText === s) || curText.includes('SYS RISK') || curText.includes('CPU:')) {
                    const tacticalStr = data.tactical_mode === "TACTICAL_FIELD_MODE" ? "[TACTICAL ACTIVE]" : "";
                    const hrAlert = data.biometrics && data.biometrics.hr > 120 ? "⚠️ HR HIGH" : "";
                    statusBar.innerText = `${tacticalStr} CPU: ${data.cpu}% | RAM: ${data.ram}% | SYS RISK: ${data.risk_percent}% ${hrAlert}`;
                }

                // [Cognitive Thought Stream HUD Integration] - Removed by user request
                const agentHud = document.getElementById('agent-status-hud');
                if (agentHud) {
                    agentHud.remove();
                }

                if (data.risk_percent > 70 && (Date.now() - lastTelemetryAlertTime > 300000)) {
                    lastTelemetryAlertTime = Date.now();

                    createHologramWindow(
                        "MAINFRAME OVERLOAD DETECTED",
                        `◆ SYNAPTIC RISK INDEX: ${data.risk_percent}%\n◆ CPU LOAD: ${data.cpu}%\n◆ RAM SATURATION: ${data.ram}%\n◆ DISK SPACE: ${data.disk}%\n◆ RECOMMENDATION: PURGE TEMPORARY CACHES IMMEDIATELY.`,
                        null,
                        "danger"
                    );

                    speak("แจ้งเตือนความปลอดภัยครับท่าน ความเสี่ยงของระบบวิเคราะห์ด้วยโครงข่ายประสาทสูงเกินเกณฑ์ปกติ กรุณาตรวจสอบสถานะโปรเซสครับ");
                }
            }
        } catch (e) {
            console.error("[TELEMETRY POLL] Fetch failed:", e);
        }
    }, 5000);
}

try {
    startTelemetryPolling();
} catch (e) {
    console.error("[TELEMETRY POLL] Start failed:", e);
}

// --- Groq API Quota Display System ---
function updateQuotaDisplay() {
    fetch('/api/quota')
        .then(response => response.json())
        .then(data => {
            const el = document.getElementById('quota-display');
            if (el) {
                const count = data.count || 0;
                const limit = data.limit || 20;
                el.innerText = `GROQ API: ${count}/${limit}`;

                if (count >= limit) {
                    el.style.color = '#ff4d4d';
                    el.style.borderColor = 'rgba(255, 77, 77, 0.6)';
                    el.style.boxShadow = '0 0 10px rgba(255, 77, 77, 0.4)';
                    el.style.textShadow = '0 0 6px rgba(255, 77, 77, 0.6)';
                    el.innerText = `GROQ API: EXCEEDED (${count}/${limit})`;
                } else if (count >= limit * 0.8) {
                    el.style.color = '#ff9933';
                    el.style.borderColor = 'rgba(255, 153, 51, 0.6)';
                    el.style.boxShadow = '0 0 10px rgba(255, 153, 51, 0.4)';
                    el.style.textShadow = '0 0 6px rgba(255, 153, 51, 0.6)';
                } else {
                    el.style.color = '#00c8ff';
                    el.style.borderColor = 'rgba(0, 200, 255, 0.4)';
                    el.style.boxShadow = '0 0 10px rgba(0, 200, 255, 0.25)';
                    el.style.textShadow = '0 0 6px rgba(0, 200, 255, 0.6)';
                }
            }
        })
        .catch(err => {
            console.error("Error fetching quota:", err);
            const el = document.getElementById('quota-display');
            if (el) {
                el.innerText = `GROQ API: OFFLINE (Backend Not Running)`;
                el.style.color = '#ff4d4d';
                el.style.borderColor = 'rgba(255, 77, 77, 0.6)';
                el.style.boxShadow = '0 0 10px rgba(255, 77, 77, 0.4)';
                el.style.textShadow = '0 0 6px rgba(255, 77, 77, 0.6)';
            }
        });
}

// --- Performance & Telemetry HUD System ---
let metricsPanelMinimized = false;

function toggleMetricsPanel() {
    const panel = document.getElementById('metrics-panel');
    const btn = document.getElementById('metrics-toggle-btn');
    if (!panel) return;
    metricsPanelMinimized = !metricsPanelMinimized;
    if (metricsPanelMinimized) {
        panel.classList.add('minimized');
        if (btn) btn.innerText = '+';
    } else {
        panel.classList.remove('minimized');
        if (btn) btn.innerText = '−';
    }
}

function updateMetricsDisplay() {
    fetch('/api/metrics')
        .then(res => res.json())
        .then(data => {
            if (!data || data.status === 'error') return;

            // Tokens
            const elTokens = document.getElementById('metric-tokens');
            const elTokensSub = document.getElementById('metric-tokens-sub');
            if (elTokens && data.tokens_today) {
                const total = data.tokens_today.total || 0;
                elTokens.innerText = total.toLocaleString();
                if (elTokensSub) {
                    const p = data.tokens_today.prompt || 0;
                    const c = data.tokens_today.completion || 0;
                    elTokensSub.innerText = `P: ${p.toLocaleString()} | C: ${c.toLocaleString()}`;
                }
            }

            // Latency
            const elLatency = document.getElementById('metric-latency');
            const elLatencySub = document.getElementById('metric-latency-sub');
            if (elLatency) {
                const s = data.avg_response_s !== undefined ? data.avg_response_s : 0.0;
                const ms = data.avg_response_ms || 0;
                elLatency.innerText = `${s}s`;
                if (elLatencySub) elLatencySub.innerText = `${ms} ms`;
            }

            // Success Rate
            const elSuccess = document.getElementById('metric-success');
            const elReqSub = document.getElementById('metric-requests-sub');
            if (elSuccess) {
                const rate = data.success_rate !== undefined ? data.success_rate : 100.0;
                elSuccess.innerText = `${rate}%`;
                if (rate < 90) {
                    elSuccess.style.color = '#ff4d4d';
                } else if (rate < 98) {
                    elSuccess.style.color = '#ffb300';
                } else {
                    elSuccess.style.color = '#00e5ff';
                }
                if (elReqSub) {
                    const reqs = data.requests_today || 0;
                    const errs = data.errors_today || 0;
                    elReqSub.innerText = `${reqs} reqs${errs > 0 ? ` (${errs} err)` : ''}`;
                }
            }

            // Model
            const elModel = document.getElementById('metric-model');
            const elStatusSub = document.getElementById('metric-status-sub');
            if (elModel && data.active_model) {
                elModel.innerText = data.active_model;
            }
            if (elStatusSub) {
                elStatusSub.innerText = data.status === 'online' ? 'STATUS: ONLINE' : 'STATUS: NOMINAL';
            }

            // Sparkline / Activity stream
            const sparkline = document.getElementById('metrics-sparkline');
            const rateBadge = document.getElementById('metric-rate-badge');
            if (sparkline) {
                const trend = data.recent_trend || [];
                if (trend.length === 0) {
                    sparkline.innerHTML = '<span style="font-size:7px; color:#546e7a; margin:auto;">AWAITING TRAFFIC</span>';
                    if (rateBadge) rateBadge.innerText = 'IDLE';
                } else {
                    let html = '';
                    const maxMs = Math.max(...trend.map(t => t.ms || 100), 1000);
                    trend.forEach(t => {
                        const hPercent = Math.max(15, Math.min(100, Math.round(((t.ms || 100) / maxMs) * 100)));
                        const isErr = t.ok === false;
                        const barClass = isErr ? 'spark-bar error-bar' : 'spark-bar';
                        const tip = `${t.ms || 0}ms (${t.tokens || 0} tok)`;
                        html += `<div class="${barClass}" style="height: ${hPercent}%;" title="${tip}"></div>`;
                    });
                    sparkline.innerHTML = html;
                    if (rateBadge) rateBadge.innerText = `${trend.length} RECENTS`;
                }
            }
        })
        .catch(err => {
            console.debug("[METRICS] Waiting for backend...", err);
        });
}

// Initialize quota and telemetry updates on boot
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        updateQuotaDisplay();
        updateMetricsDisplay();
        setInterval(updateQuotaDisplay, 5000);
        setInterval(updateMetricsDisplay, 5000);
    });
} else {
    updateQuotaDisplay();
    updateMetricsDisplay();
    setInterval(updateQuotaDisplay, 5000);
    setInterval(updateMetricsDisplay, 5000);
}

// --- Agent Office (2.5D Isometric Pixel Art) System ---
let isAgentOfficeMode = false;
let officeAnimId = null;
let officeCanvas = null;
let officeCtx = null;

function toggleAgentOffice() {
    isAgentOfficeMode = !isAgentOfficeMode;
    const btn = document.getElementById('office-toggle');
    if (isAgentOfficeMode) {
        if (btn) {
            btn.innerText = 'AGENT OFFICE: ON';
            btn.style.background = 'rgba(255, 153, 0, 0.2)';
            btn.style.borderColor = '#ff9900';
            btn.style.color = '#ff9900';
        }
        openAgentOfficeWindow();
    } else {
        if (btn) {
            btn.innerText = 'AGENT OFFICE: OFF';
            btn.style.background = '';
            btn.style.borderColor = '';
            btn.style.color = '';
        }
        closeAgentOfficeWindow();
    }
}

// Interactive 2.5D Agent System
const agentWaypoints = {
    web: { deskX: 30, deskY: 35 },
    cli: { deskX: 65, deskY: 35 },
    os: { deskX: 35, deskY: 65 },
    code: { deskX: 70, deskY: 60 },
    friday: { deskX: 20, deskY: 70 },
    veronica: { deskX: 80, deskY: 30 },
    edith: { deskX: 85, deskY: 70 },
    u: { deskX: 15, deskY: 35 },
    dume: { deskX: 50, deskY: 85 },
    roaming: [
        { x: 50, y: 50 }, { x: 40, y: 70 }, { x: 60, y: 40 },
        { x: 25, y: 55 }, { x: 75, y: 75 }, { x: 50, y: 30 },
        { x: 15, y: 65 }, { x: 85, y: 45 }
    ]
};

class JarvisAgentNode {
    constructor(id, name, color, initialRole) {
        this.id = id;
        this.name = name;
        this.color = color;
        this.role = initialRole; // 'web', 'cli', 'os', 'code'
        this.element = null;
        this.x = 50;
        this.y = 50;
        this.isBusy = false;
        this.roamInterval = null;
        
        // Base64 Pixel Art Character Map (RPG Style)
        const spriteMap = {
            web: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAAqElEQVR4nGNkQID/DMQDRhiDBVk0QEOEKN0bbryBs5kYKARMA24AC1rAgANy/ZJWrIoDY6qp7wImXBKMJulY2UQb8P/MTKxsDIsY0PThUwx1DYoeRmTNeHUSkxL/z8CjIwMhD2IPnoTENKgMYGQwmYkSQMgAFICMGRA1hMB/GP4/A8HGFc2M2AwwMjICM86dO8eIhY/TC2QBJvK0UdEArGGARR6bGHUAADzcLcNAwLPUAAAAAElFTkSuQmCC',
            cli: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAArUlEQVR4nGNkQID/DMQDRhiDBVlUQ0ODKN03btyAs5kYKARMA24AC1rAgAPy+pJCrIo1Y/qp7wImXBKMJulY2UQb8P/MTKxsDIsY0PThUwx1DYoeRmTNeHUSkxJfyiXj1CH+aC5cHsQePAmJaVAZwCi2zgwlgJABKADFH80FqyEE/sPwS7lkOBtXNDNiM8DIyAjMOHfuHCMWPk4vkAWYyNNGRQOwhgEWeWxi1AEA9TUyHe3kBYYAAAAASUVORK5CYII=',
            os: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAAr0lEQVR4nGNkQID/DMQDRhiDBVn0xIkTROm2sLCAs5kYKARMA24AC1rAgAPSnOUiVsUn/+hT3wVMuCQYTdKxsok24P+ZmVjZGBYxoOnDpxjqGhQ9jMia8eokJiUyPMVjhjQjQh7EHjQJiWlQGcD4//kslABCAaAAlGaEqCEA/sPx0/8INo5oZsEmaGRkBKbPSTOCMxicf+4cXi+QBZjI00ZFA7AFOXJgweSxiVEHAABSjy6s6lt5jgAAAABJRU5ErkJggg==',
            code: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAArElEQVR4nGNkQID/DMQDRhiDBVk0xciIKN1zzp2Ds5kYKARMA24AC1rAgANy9qx0rIpT02ZS3wVMuCQYTdKxsok24P+ZmVjZGBYxoOnDpxjqGhQ9jMia8eokJiX6rA/AqWNL4Aa4PIg9eBIS06AygHGzrCdKACEDUABuCdwAVkMI/Idhn/UBcDauaGbEZoARtGA5d+4cIxY+Ti+QBZjI00ZFA7CGARZ5bGLUAQB2AzJb7YoZGwAAAABJRU5ErkJggg==',
            friday: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAAsElEQVR4nGNkQID/DMQDRhiDBVn0/0F24nTb/4SzmRgoBEwDbgALWsBAApJ7EnbVX/Oo7wImXBKMJulY2UQb8P/MTKxsDIsY0PThUwx1DYoeRmTNeHUSlRJfW+PWIXoULg9iD56ExDSoDGBkeBiHEkDIABSAjKJHwWoIgf8w/P+1NZyNK5pZsAkaGRlBnASykYHhP4x/7tw5vF4gCzCRp42KBqBnJhBADiyYPDYx6gAAsBsvG7UOr6MAAAAASUVORK5CYII=',
            veronica: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAAq0lEQVR4nN1TAQrDIAw04ndEkP2pH9hesX2gfyoB6YNSKtpdnRZhhY4dFM8kFzVJSb0hqh+UiUHrs1P9AK7Vl9CXJzBFYWIh79NYDX7dhvNvoFsOgtOQdycQeAbyj4NUoTsKTrfZaQjFh8qeSZydaypsCJt/5b8zSPryBIQbmUZZh6ZVTBsCpZiy/TtI/mbnNt5qs6kZvfdxtczxB8t7Zv77LiRgsbK/ZjsHC3HKMrkrPsK3AAAAAElFTkSuQmCC',
            edith: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAAr0lEQVR4nGNkQID/DMQDRhiDBVn0xIkTROm2sLCAs5kYKARMA24AC1rAgAPSnOUiVsUn/+hT3wVMuCQYTdKxsok24P+ZmVjZGBYxoOnDpxjqGhQ9jMia8eokJiUyPMVjhjQjQh7EHjQJiWlQGcD4//kslABCAaAAlGaEqCEA/sPx0/8INo5oZsEmaGRkBKbPSTOCMxicf+4cXi+QBZjI00ZFA7AFOXJgweSxiVEHAABSjy6s6lt5jgAAAABJRU5ErkJggg==',
            u: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAArElEQVR4nGNkQID/DMQDRhiDBVk0xciIKN1zzp2Ds5kYKARMA24AC1rAgANy9qx0rIpT02ZS3wVMuCQYTdKxsok24P+ZmVjZGBYxoOnDpxjqGhQ9jMia8eokJiX6rA/AqWNL4Aa4PIg9eBIS06AygHGzrCdKACEDUABuCdwAVkMI/Idhn/UBcDauaGbEZoARtGA5d+4cIxY+Ti+QBZjI00ZFA7CGARZ5bGLUAQB2AzJb7YoZGwAAAABJRU5ErkJggg==',
            dume: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAAqElEQVR4nGNkQID/DMQDRhiDBVk0QEOEKN0bbryBs5kYKARMA24AC1rAgANy/ZJWrIoDY6qp7wImXBKMJulY2UQb8P/MTKxsDIsY0PThUwx1DYoeRmTNeHUSkxL/z8CjIwMhD2IPnoTENKgMYGQwmYkSQMgAFICMGRA1hMB/GP4/A8HGFc2M2AwwMjICM86dO8eIhY/TC2QBJvK0UdEArGGARR6bGHUAADzcLcNAwLPUAAAAAElFTkSuQmCC'
        };
        this.spriteUrl = spriteMap[this.id];
    }

    createDOM(container) {
        this.element = document.createElement('div');
        this.element.className = 'agent-node';
        this.element.id = `node-${this.id}`;
        
        // Premium Pixel Art Avatar Design
        this.element.innerHTML = `
            <img src="${this.spriteUrl}" class="drone-core" style="width: 24px; height: 36px; image-rendering: pixelated; border-radius: 0; background: transparent; box-shadow: none;">
            <div class="agent-ring" style="border-color: ${this.color}; box-shadow: 0 0 10px ${this.color}55;"></div>
            <div class="agent-label">${this.name}</div>
            <div class="agent-status-text">PATROLLING</div>
        `;

        this.element.style.left = `${this.x}%`;
        this.element.style.top = `${this.y}%`;

        // Click to Command
        this.element.onclick = (e) => {
            e.stopPropagation();
            openAgentCommandUI(this);
        };

        container.appendChild(this.element);
        this.startRoaming();
    }

    moveTo(px, py) {
        this.x = px;
        this.y = py;
        if(this.element) {
            this.element.style.left = `${px}%`;
            this.element.style.top = `${py}%`;
        }
    }

    startRoaming() {
        if(this.roamInterval) clearInterval(this.roamInterval);
        this.roamInterval = setInterval(() => {
            if(!this.isBusy) {
                // Pick random roam point
                const pt = agentWaypoints.roaming[Math.floor(Math.random() * agentWaypoints.roaming.length)];
                // Add some jitter
                const jx = pt.x + (Math.random() * 10 - 5);
                const jy = pt.y + (Math.random() * 10 - 5);
                this.moveTo(jx, jy);
            }
        }, 3000 + Math.random() * 2000);
    }

    setBusy(busy) {
        this.isBusy = busy;
        if(!this.element) return;
        const status = this.element.querySelector('.agent-status-text');
        
        if(busy) {
            this.element.classList.add('active');
            status.innerText = 'PROCESSING...';
            // Move to assigned desk
            const desk = agentWaypoints[this.role];
            this.moveTo(desk.deskX, desk.deskY);
        } else {
            this.element.classList.remove('active');
            status.innerText = 'PATROLLING';
            // Will resume roaming on next interval
        }
    }

    destroy() {
        if(this.roamInterval) clearInterval(this.roamInterval);
        if(this.element) this.element.remove();
    }
}

let activeAgents = [];

function openAgentOfficeWindow() {
    let existingWin = document.getElementById('agent-office-win');
    if (existingWin) return;

    const container = document.querySelector('.hud-container');
    const win = document.createElement('div');
    win.className = 'hologram-window';
    win.id = 'agent-office-win';
    
    // Position it in the center of the screen, much larger
    win.style.left = '50%';
    win.style.top = '50%';
    win.style.transform = 'translate(-50%, -50%)';
    win.style.width = '740px';
    win.style.height = '480px';
    win.style.zIndex = '9999';
    win.style.boxShadow = '0 0 30px rgba(0, 200, 255, 0.4), inset 0 0 20px rgba(0, 200, 255, 0.2)';
    win.style.border = '2px solid rgba(0, 200, 255, 0.6)';
    win.style.borderRadius = '8px';
    win.style.overflow = 'hidden';

    // Using the NEW empty office image
    win.innerHTML = `
        <div class="hologram-header" style="background: rgba(0,20,40,0.9); border-bottom: 1px solid #00c8ff;">
            <span class="hologram-title" style="font-size: 14px; letter-spacing: 2px;">◆ JARVIS NEURAL SYNC : AGENT OFFICE ◆</span>
            <div style="display: flex; gap: 10px; pointer-events: all;">
                <span class="hologram-btn" onclick="toggleAgentOffice()" style="color: #ff3333;">[CLOSE]</span>
            </div>
        </div>
        <div class="hologram-content" id="office-bg" style="
            height: calc(100% - 35px); 
            position: relative;
            background: url('/static/empty_office.jpg') no-repeat center center; 
            background-size: cover;
            box-shadow: inset 0 0 60px rgba(0,0,0,0.8);
            overflow: hidden;
        ">
            <!-- Dynamic Particles Overlay -->
            <canvas id="office-particles" width="740" height="445" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 5; mix-blend-mode: screen;"></canvas>
            <div id="agents-container" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10;"></div>
            
            <!-- Agent Command Popup UI (Hidden by default) -->
            <div id="agent-command-ui" style="
                display: none;
                position: absolute;
                bottom: 20px; left: 50%;
                transform: translateX(-50%);
                width: 80%;
                background: rgba(0, 15, 30, 0.9);
                border: 1px solid #00ffcc;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 0 20px rgba(0, 255, 204, 0.3);
                z-index: 100;
                pointer-events: all;
            ">
                <div style="color: #00ffcc; font-size: 10px; font-family: Orbitron; margin-bottom: 5px; display: flex; justify-content: space-between;">
                    <span id="cmd-ui-title">DIRECT COMMAND: AGENT</span>
                    <span style="cursor: pointer; color: #ff5555;" onclick="closeAgentCommandUI()">[X]</span>
                </div>
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="cmd-ui-input" placeholder="Enter task for this agent..." style="
                        flex: 1; background: rgba(0,0,0,0.5); border: 1px solid #00c8ff; color: #fff; padding: 5px 10px; font-family: monospace; border-radius: 4px;
                    " onkeypress="if(event.key === 'Enter') submitAgentCommand()">
                    <button onclick="submitAgentCommand()" style="
                        background: rgba(0, 200, 255, 0.2); border: 1px solid #00c8ff; color: #00c8ff; padding: 5px 15px; cursor: pointer; border-radius: 4px; font-family: Orbitron;
                    ">EXECUTE</button>
                </div>
            </div>
        </div>
        <style>
            .agent-node {
                position: absolute;
                transform: translate(-50%, -50%);
                display: flex;
                flex-direction: column;
                align-items: center;
                transition: left 2.5s cubic-bezier(0.25, 1, 0.5, 1), top 2.5s cubic-bezier(0.25, 1, 0.5, 1);
                cursor: pointer;
            }
            .agent-node:hover .agent-ring {
                border-color: #fff !important;
                box-shadow: 0 0 15px #fff !important;
            }
            .drone-core {
                width: 12px; height: 12px;
                border-radius: 50%;
                margin-bottom: 5px;
                animation: bobbing 2s infinite ease-in-out alternate;
            }
            .agent-ring {
                width: 30px; height: 15px;
                border-radius: 50%;
                border: 2px solid;
                transform: rotateX(60deg);
                position: absolute;
                top: 8px;
            }
            .agent-label {
                margin-top: 10px;
                font-family: 'Orbitron', monospace;
                font-size: 9px;
                color: #fff;
                background: rgba(0, 15, 30, 0.8);
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .agent-status-text {
                font-family: monospace;
                font-size: 8px;
                color: #aaa;
                margin-top: 2px;
            }
            .agent-node.active .drone-core {
                animation: bobbing-fast 0.5s infinite ease-in-out alternate;
            }
            .agent-node.active .agent-ring {
                animation: pulse-ring 1s infinite alternate;
            }
            .agent-node.active .agent-label {
                background: rgba(0, 255, 204, 0.3);
                border-color: #00ffcc;
                box-shadow: 0 0 10px #00ffcc;
            }
            .agent-node.active .agent-status-text {
                color: #00ffcc;
                animation: blink 0.5s infinite;
            }
            @keyframes bobbing {
                0% { transform: translateY(0px); }
                100% { transform: translateY(-8px); }
            }
            @keyframes bobbing-fast {
                0% { transform: translateY(0px); }
                100% { transform: translateY(-4px); }
            }
            @keyframes pulse-ring {
                0% { transform: rotateX(60deg) scale(1); }
                100% { transform: rotateX(60deg) scale(1.4); }
            }
        </style>
    `;
    container.appendChild(win);
    makeDraggable(win);

    // Initialize Agents
    activeAgents = [];
    setTimeout(() => {
        const agentContainer = document.getElementById('agents-container');
        activeAgents.push(new JarvisAgentNode('web', 'WEB CRAWLER', '#ff9800', 'web'));
        activeAgents.push(new JarvisAgentNode('cli', 'TERMINAL CORE', '#e91e63', 'cli'));
        activeAgents.push(new JarvisAgentNode('os', 'OS KERNEL', '#00e5ff', 'os'));
        activeAgents.push(new JarvisAgentNode('code', 'CODE ENGINE', '#4caf50', 'code'));
        activeAgents.push(new JarvisAgentNode('friday', 'F.R.I.D.A.Y.', '#00c8ff', 'friday'));
        activeAgents.push(new JarvisAgentNode('veronica', 'VERONICA', '#d32f2f', 'veronica'));
        activeAgents.push(new JarvisAgentNode('edith', 'E.D.I.T.H.', '#00e5ff', 'edith'));
        activeAgents.push(new JarvisAgentNode('u', 'U. (YOU)', '#00ff88', 'u'));
        activeAgents.push(new JarvisAgentNode('dume', 'D.U.M.-E.', '#ff9800', 'dume'));
        
        activeAgents.forEach(a => a.createDOM(agentContainer));

        officeCanvas = document.getElementById('office-particles');
        if (officeCanvas) {
            officeCtx = officeCanvas.getContext('2d');
            startOfficeAnimation();
        }
    }, 100);
}

// Click to Command UI Logic
let currentTargetAgent = null;

function openAgentCommandUI(agent) {
    currentTargetAgent = agent;
    const ui = document.getElementById('agent-command-ui');
    const title = document.getElementById('cmd-ui-title');
    const input = document.getElementById('cmd-ui-input');
    
    if(ui && title && input) {
        ui.style.display = 'block';
        title.innerText = `DIRECT COMMAND: [ ${agent.name} ]`;
        input.value = '';
        input.focus();
        // Highlight this agent, dim others slightly
        activeAgents.forEach(a => {
            if(a.element) {
                a.element.style.opacity = (a.id === agent.id) ? '1' : '0.4';
            }
        });
    }
}

function closeAgentCommandUI() {
    const ui = document.getElementById('agent-command-ui');
    if(ui) ui.style.display = 'none';
    currentTargetAgent = null;
    activeAgents.forEach(a => {
        if(a.element) a.element.style.opacity = '1';
    });
}

function submitAgentCommand() {
    const input = document.getElementById('cmd-ui-input');
    if(!input || !input.value.trim() || !currentTargetAgent) return;
    
    const cmd = input.value.trim();
    // Prepend agent target to the command
    const formattedCmd = `@${currentTargetAgent.id} ${cmd}`;
    
    // Inject into the main JARVIS chat input and send
    const mainInput = document.getElementById('user-input');
    if(mainInput) {
        mainInput.value = formattedCmd;
        sendMessage(); // Assumes sendMessage() exists in main scope
    }
    
    closeAgentCommandUI();
}

function closeAgentOfficeWindow() {
    const win = document.getElementById('agent-office-win');
    if (win) win.remove();
    stopOfficeAnimation();
    activeAgents.forEach(a => a.destroy());
    activeAgents = [];
    officeCanvas = null;
    officeCtx = null;
}

// 60FPS High-Res Particle Engine for Premium Aesthetics
let particles = [];
function initParticles() {
    particles = [];
    for(let i=0; i<50; i++) {
        particles.push({
            x: Math.random() * 740,
            y: Math.random() * 445,
            vx: (Math.random() - 0.5) * 0.5,
            vy: -Math.random() * 1.5,
            life: Math.random() * 100,
            maxLife: 100 + Math.random() * 100,
            size: Math.random() * 2 + 1
        });
    }
}

function startOfficeAnimation() {
    if (officeAnimId) return;
    initParticles();
    
    function loop() {
        if (!isAgentOfficeMode) return;
        officeAnimId = requestAnimationFrame(loop);
        renderOffice();
    }
    officeAnimId = requestAnimationFrame(loop);
}

function stopOfficeAnimation() {
    if (officeAnimId) {
        cancelAnimationFrame(officeAnimId);
        officeAnimId = null;
    }
}

function renderOffice() {
    if (!officeCtx || !officeCanvas) return;
    
    const ctx = officeCtx;
    ctx.clearRect(0, 0, officeCanvas.width, officeCanvas.height);

    // Update global agent busy state
    const sysIdleText = document.getElementById('current-ambiance') ? document.getElementById('current-ambiance').innerText : '';
    const isActive = !sysIdleText.includes('IDLE');

    activeAgents.forEach(a => a.setBusy(isActive));

    // Draw flowing particles
    ctx.fillStyle = isActive ? 'rgba(0, 255, 204, 0.8)' : 'rgba(0, 200, 255, 0.3)';
    particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.life++;
        
        if (p.life > p.maxLife || p.y < 0) {
            p.y = 445;
            p.x = Math.random() * 740;
            p.life = 0;
            p.vy = isActive ? -Math.random() * 3 - 1 : -Math.random() * 1.5;
        }

        const alpha = 1 - (p.life / p.maxLife);
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
    });
    ctx.globalAlpha = 1.0;
}

