// S H A D O W  B R O K E R - Client Logic

let world;
let cctvData = [];

// Initialize Globe
function initMap() {
    const container = document.getElementById('map');
    
    // Ensure container has dimensions before initializing
    const w = container.clientWidth || window.innerWidth / 2;
    const h = container.clientHeight || window.innerHeight / 2;

    world = Globe()(container)
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
        .backgroundColor('rgba(0,0,0,0)')
        .width(w)
        .height(h)
        .pointOfView({ lat: 20, lng: 0, altitude: 2.5 })
        .pointRadius(0.8)
        .pointColor(d => d.isAlert ? '#ff003c' : '#00ff41')
        .pointAltitude(d => d.isAlert ? 0.05 : 0.01)
        .pointResolution(32)
        .pointLabel(d => `
            <div style="text-align: center;">
                <b>${d.location}</b><br>
                <i>คลิกเพื่อดักจับสัญญาณภาพ</i>
            </div>
        `)
        .onPointClick(d => playStream(d));

    // Fetch and draw country borders
    fetch('https://raw.githubusercontent.com/vasturiano/globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson')
        .then(res => res.json())
        .then(countries => {
            world.polygonsData(countries.features)
                .polygonCapColor(() => 'rgba(0,0,0,0)') // Transparent fill
                .polygonSideColor(() => 'rgba(0, 255, 255, 0.05)') // Faint side
                .polygonStrokeColor(() => '#008888'); // Cyan borders
        });

    // Optional: Add auto-rotate
    world.controls().autoRotate = true;
    world.controls().autoRotateSpeed = 0.5;

    // Track mouse coordinates safely
    world.controls().addEventListener('change', () => {
        try {
            const pov = world.pointOfView();
            if (pov && pov.lat !== undefined && pov.lng !== undefined) {
                document.getElementById('current-coords').innerText = 
                    `${pov.lat.toFixed(4)}, ${pov.lng.toFixed(4)}`;
            }
        } catch (e) {
            // ignore initial errors if pointOfView is not ready
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', () => {
        if (container.clientWidth && container.clientHeight) {
            world.width(container.clientWidth);
            world.height(container.clientHeight);
        }
    });
}

// Fetch CCTV data from Backend
async function fetchCCTVData() {
    try {
        const response = await fetch('/api/cctv_list');
        const data = await response.json();
        
        document.getElementById('cctv-count').innerText = data.length.toLocaleString();
        
        plotMarkers(data);
    } catch (error) {
        console.error("Failed to fetch CCTV data:", error);
    }
}

// Plot markers on the globe
function plotMarkers(cameras) {
    cctvData = cameras.map(cam => {
        const isAlert = Math.random() > 0.95;
        return {
            ...cam,
            isAlert: isAlert
        };
    });

    world.pointsData(cctvData);
}

// Play CCTV Stream
function playStream(cam) {
    // Update location UI
    document.getElementById('current-loc').innerText = cam.location.toUpperCase();
    
    const videoPlaceholder = document.getElementById('video-placeholder');
    const imgEl = document.getElementById('cctv-stream');
    const iframeEl = document.getElementById('cctv-iframe');
    const nameEl = document.getElementById('cctv-name');

    videoPlaceholder.style.display = 'none';

    if (cam.type === 'video') {
        imgEl.style.display = 'none';
        iframeEl.style.display = 'block';
        iframeEl.src = cam.url + "&autoplay=1&mute=1";
    } else {
        iframeEl.style.display = 'none';
        imgEl.style.display = 'block';
        imgEl.src = cam.url;
    }
    
    nameEl.innerText = "เป้าหมาย: " + cam.location;

    // Pan map to location
    world.pointOfView({ lat: cam.lat, lng: cam.lng, altitude: 0.8 }, 1500);

    // Stop auto-rotate when examining a target
    world.controls().autoRotate = false;
    setTimeout(() => { world.controls().autoRotate = true; }, 10000);

    // Add intercept log
    addAlert(`กำลังดักจับสัญญาณ: ${cam.location}`, 'threat-high');
}

// Mock Threat Alert Generator
function addAlert(text, type='threat-medium') {
    const feed = document.getElementById('alert-feed');
    const now = new Date();
    const timeStr = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
    
    const title = type === 'threat-high' ? 'ดักจับสัญญาณสด' : 'บันทึกระบบ';
    
    const html = `
        <div class="alert-item ${type}">
            <div class="alert-header">
                <span class="alert-time">${timeStr}</span>
                <span class="alert-title">${title}</span>
            </div>
            <div class="alert-body">${text}</div>
        </div>
    `;
    
    feed.insertAdjacentHTML('afterbegin', html);
    
    // Keep max 5
    if (feed.children.length > 5) {
        feed.removeChild(feed.lastElementChild);
    }
}

// Clock logic
setInterval(() => {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('en-US', { hour12: false });
}, 1000);

// Random alerts to simulate activity
setInterval(() => {
    if(Math.random() > 0.7) {
        const events = [
            "ดักจับแพ็กเกจข้อมูลเข้ารหัสได้ที่ Node-7",
            "ตรวจพบความหน่วงผิดปกติในสายเคเบิลใต้น้ำ",
            "บล็อกการพยายามเข้าถึงระบบโดยไม่ได้รับอนุญาต",
            "การซิงโครไนซ์ข้อมูลดาวเทียมเสร็จสมบูรณ์"
        ];
        addAlert(events[Math.floor(Math.random()*events.length)]);
    }
}, 5000);

// Init
window.onload = () => {
    initMap();
    fetchCCTVData();
};
