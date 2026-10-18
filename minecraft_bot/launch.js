/**
 * J.A.R.V.I.S. Minecraft Companion Launcher
 * Automatically detects Minecraft LAN worlds via UDP multicast or TCP scan
 * and launches the bot seamlessly without requiring manual port input!
 */

const dgram = require('dgram');
const { spawn, execSync } = require('child_process');
const path = require('path');

function detectPortFromPowerShell() {
    try {
        const cmd = 'powershell -NoProfile -Command "$proc = Get-Process javaw, java -ErrorAction SilentlyContinue; if ($proc) { Get-NetTCPConnection -OwningProcess $proc.Id -ErrorAction SilentlyContinue | Where-Object State -eq \'Listen\' | Select-Object -ExpandProperty LocalPort }"';
        const out = execSync(cmd, { encoding: 'utf8', timeout: 4000, stdio: ['pipe', 'pipe', 'ignore'] }).trim();
        const ports = out.split(/\r?\n/).map(p => parseInt(p.trim())).filter(p => !isNaN(p) && p > 1024);
        if (ports.length > 0) return ports[0];
    } catch (e) {}
    return null;
}

function listenForLAN(timeoutMs = 10000) {
    return new Promise((resolve) => {
        let socket;
        let done = false;
        const timer = setTimeout(() => {
            if (!done) {
                done = true;
                if (socket) try { socket.close(); } catch(e) {}
                resolve(null);
            }
        }, timeoutMs);

        try {
            socket = dgram.createSocket({ type: 'udp4', reuseAddr: true });
            socket.on('error', () => {
                if (!done) {
                    done = true;
                    clearTimeout(timer);
                    resolve(null);
                }
            });
            socket.on('message', (msg) => {
                const text = msg.toString('utf8');
                const match = text.match(/\[AD\](\d+)\[\/AD\]/);
                if (match && !done) {
                    done = true;
                    clearTimeout(timer);
                    try { socket.close(); } catch(e) {}
                    resolve(parseInt(match[1]));
                }
            });
            socket.bind(4445, () => {
                try {
                    socket.addMembership('224.0.2.60');
                } catch(e) {}
            });
        } catch (e) {
            clearTimeout(timer);
            resolve(null);
        }
    });
}

async function main() {
    console.log("=================================================");
    console.log("   J.A.R.V.I.S. Minecraft Companion Launcher     ");
    console.log("=================================================");
    
    // 1. Check if user provided port as argument
    let port = parseInt(process.argv[2]);
    if (port && !isNaN(port)) {
        console.log(`[JARVIS] ใช้พอร์ตจากคำสั่ง: ${port}`);
        return startBot(port);
    }

    console.log("[JARVIS] กำลังค้นหาเซิร์ฟเวอร์ Minecraft LAN อัตโนมัติ...");
    console.log("[คำแนะนำ] หากยังไม่ได้เปิด LAN ในเกม ให้กด Esc -> 'Open to LAN' -> 'Start LAN World'");

    // Loop until detected or user cancels
    let attempts = 0;
    while (true) {
        attempts++;
        // Try UDP first (fastest and accurate)
        port = await listenForLAN(3000);
        if (port) {
            console.log(`\n>>> ตรวจพบ Minecraft LAN พอร์ต: ${port} ผ่าน UDP Ping! <<<`);
            return startBot(port);
        }

        // Try PowerShell TCP fallback
        port = detectPortFromPowerShell();
        if (port) {
            console.log(`\n>>> ตรวจพบ Minecraft LAN พอร์ต: ${port} ผ่าน Network Scan! <<<`);
            return startBot(port);
        }

        process.stdout.write(`\r[JARVIS] กำลังรอสัญญาณ LAN จาก Minecraft (รอบที่ ${attempts})... `);
    }
}

function startBot(port) {
    console.log(`[JARVIS] กำลังเชื่อมต่อเข้าสู่เซิร์ฟเวอร์พอร์ต ${port} ในฐานะ 'JARVIS_Suit' (1.20.4)...`);
    const botProcess = spawn('node', ['bot.js', port.toString()], {
        cwd: __dirname,
        stdio: 'inherit'
    });

    botProcess.on('exit', (code) => {
        console.log(`\n[JARVIS] บอทออกจากเกมแล้ว (Exit Code: ${code})`);
    });
}

main().catch(console.error);
