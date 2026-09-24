const canvas = document.getElementById('brain-canvas');
const ctx = canvas.getContext('2d');

let particles = [];
const PARTICLE_COUNT = 150;
const CORE_RADIUS = 80;

let width, height, cx, cy;

function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    width = canvas.width;
    height = canvas.height;
    cx = width / 2;
    cy = height / 2;
}

window.addEventListener('resize', resize);
resize();

// Utility for colors based on Jarvis Theme
const COLORS = [
    'rgba(0, 200, 255, 0.8)', // Primary Blue
    'rgba(0, 200, 255, 0.5)', // Dim Blue
    'rgba(55, 226, 177, 0.8)', // Green
    'rgba(255, 179, 0, 0.8)', // Yellow/Gold
    'rgba(255, 80, 80, 0.8)'  // Red
];

const THOUGHTS = [
    "ROUTING PROTOCOLS", "ANALYZING SPEECH", "DEEP THOUGHT ACTIVE", 
    "SENSOR SCAN", "CALCULATING TENSION", "SYSTEM IDLE", "MEMORY FETCH", "NEURAL SYNC"
];

class Particle {
    constructor() {
        this.angle = Math.random() * Math.PI * 2;
        this.radius = CORE_RADIUS + Math.random() * 300;
        this.x = cx + Math.cos(this.angle) * this.radius;
        this.y = cy + Math.sin(this.angle) * this.radius;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.size = Math.random() * 2 + 1;
        this.baseColor = COLORS[Math.floor(Math.random() * (Math.random() > 0.8 ? COLORS.length : 2))]; // Mostly blue
        
        // Sometimes assign a thought label
        this.thought = Math.random() > 0.95 ? THOUGHTS[Math.floor(Math.random() * THOUGHTS.length)] : null;
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;

        // Keep them orbiting loosely around center
        const dx = this.x - cx;
        const dy = this.y - cy;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist > 400 || dist < CORE_RADIUS) {
            this.vx *= -1;
            this.vy *= -1;
        }

        // Add slight drift
        this.vx += (Math.random() - 0.5) * 0.05;
        this.vy += (Math.random() - 0.5) * 0.05;
        
        // Clamp speed
        const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
        if (speed > 1) {
            this.vx = (this.vx / speed) * 1;
            this.vy = (this.vy / speed) * 1;
        }
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.baseColor;
        ctx.shadowBlur = 10;
        ctx.shadowColor = this.baseColor;
        ctx.fill();
        ctx.shadowBlur = 0; // reset
        
        if (this.thought) {
            ctx.fillStyle = "rgba(0, 200, 255, 0.9)";
            ctx.font = "9px 'Orbitron', monospace";
            ctx.fillText(this.thought, this.x + 8, this.y + 3);
            
            // Draw a cool bracket around text
            ctx.strokeStyle = "rgba(0, 200, 255, 0.4)";
            ctx.beginPath();
            ctx.moveTo(this.x + 5, this.y - 5);
            ctx.lineTo(this.x + 5, this.y + 5);
            ctx.stroke();
        }
    }
}

for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
}

function animate() {
    ctx.clearRect(0, 0, width, height);

    // Draw Core
    ctx.beginPath();
    ctx.arc(cx, cy, CORE_RADIUS, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(0, 200, 255, 0.2)';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Core Glow
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, CORE_RADIUS);
    gradient.addColorStop(0, 'rgba(0, 200, 255, 0.4)');
    gradient.addColorStop(0.8, 'rgba(0, 200, 255, 0.1)');
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.fill();

    // Core Text
    ctx.fillStyle = "rgba(0, 200, 255, 0.9)";
    ctx.font = "14px 'Orbitron', monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowBlur = 15;
    ctx.shadowColor = "#00c8ff";
    ctx.fillText("N E U R A L   C O R E", cx, cy);
    ctx.shadowBlur = 0;
    ctx.textAlign = "left"; // reset

    for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();

        // Connect to core
        const dxCore = particles[i].x - cx;
        const dyCore = particles[i].y - cy;
        const distCore = Math.sqrt(dxCore * dxCore + dyCore * dyCore);
        
        if (distCore < CORE_RADIUS + 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(cx + (dxCore/distCore)*CORE_RADIUS, cy + (dyCore/distCore)*CORE_RADIUS);
            ctx.strokeStyle = `rgba(0, 200, 255, ${0.3 * (1 - (distCore - CORE_RADIUS) / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
        }

        // Connect to other particles
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < 80) {
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                // Inherit color from i
                const alpha = 0.4 * (1 - dist / 80);
                const color = particles[i].baseColor.replace('0.8)', `${alpha})`);
                ctx.strokeStyle = color;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }
        }
    }

    requestAnimationFrame(animate);
}

animate();

// Polling for actual state updates (Optional future integration)
setInterval(() => {
    // Randomize some thought nodes to make it look alive
    particles.forEach(p => {
        if (p.thought && Math.random() > 0.8) {
            p.thought = THOUGHTS[Math.floor(Math.random() * THOUGHTS.length)];
        }
    });

    // Fetch Neuro Status from Backend
    fetch('/api/neuro_status')
        .then(response => response.json())
        .then(data => {
            if(data.prefrontal) document.getElementById('n-pref').innerText = data.prefrontal;
            if(data.motor) document.getElementById('n-moto').innerText = data.motor;
            if(data.sensory) document.getElementById('n-sens').innerText = data.sensory;
            if(data.language) document.getElementById('n-lang').innerText = data.language;
            if(data.memory) document.getElementById('n-memo').innerText = data.memory;
            
            // Dopamine color logic
            if(data.dopamine) {
                const el = document.getElementById('n-dopa');
                el.innerText = data.dopamine;
                el.style.color = data.dopamine.includes("HIGH") ? "#00c8ff" : (data.dopamine.includes("LOW") ? "#ff5050" : "");
            }
            // Cortisol color logic
            if(data.cortisol) {
                const el = document.getElementById('n-cort');
                el.innerText = data.cortisol;
                el.style.color = data.cortisol.includes("HIGH") ? "#ff5050" : (data.cortisol.includes("LOW") ? "#00c8ff" : "");
            }
        })
        .catch(err => console.log("Neuro API offline or error", err));

}, 3000);

// Live Data Terminal Simulation
const terminalContent = document.getElementById('terminal-content');
const terminalLogs = [
    "SYS_ROUTING: UPLINK ESTABLISHED",
    "MEM_ALLOC: 0xFA4B9... SECURE",
    "NET_SCAN: PORT 5050 NOMINAL",
    "AI_CORE: LATENCY < 15ms",
    "SYS_THREAD: DAEMON ONLINE",
    "NEURAL_NET: WEIGHTS UPDATED",
    "VISUAL_CTX: AWAITING FRAMES",
    "AUDIO_PROC: NOISE FLOOR -40dB"
];

function generateRandomHex() {
    return '0x' + Math.floor(Math.random()*16777215).toString(16).toUpperCase();
}

function appendTerminalLine() {
    if (!terminalContent) return;
    const isAlert = Math.random() > 0.95;
    let text = "";
    
    if (isAlert) {
        text = `[WARNING] PKT_DROP DETECTED AT ${generateRandomHex()}`;
    } else if (Math.random() > 0.5) {
        text = terminalLogs[Math.floor(Math.random() * terminalLogs.length)];
    } else {
        text = `DATA_STREAM: ${generateRandomHex()} -> ${generateRandomHex()}`;
    }
    
    const div = document.createElement('div');
    div.className = 'term-line' + (isAlert ? ' term-alert' : '');
    div.innerHTML = `<span class="term-prefix">Sys&gt;</span>${text}`;
    
    terminalContent.appendChild(div);
    
    // Keep max 10 lines
    while (terminalContent.children.length > 12) {
        terminalContent.removeChild(terminalContent.firstChild);
    }
}

// Append new line randomly every 200 - 800ms
function runTerminal() {
    appendTerminalLine();
    setTimeout(runTerminal, 200 + Math.random() * 600);
}

// Start terminal
setTimeout(runTerminal, 1000);
