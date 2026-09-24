// TACTICAL COMMAND - Frontend Logic

// --- System Clock ---
setInterval(() => {
    document.getElementById('system-time').innerText = new Date().toUTCString();
}, 1000);

// ==========================================
// PROJECT VALKYRIE (3D Cyber Threat Globe)
// ==========================================
const globeContainer = document.getElementById('globeViz');
let arcsData = [];

// Initialize Globe.gl
const world = Globe()(globeContainer)
    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
    .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
    .backgroundColor('rgba(0,0,0,0)')
    .arcColor(() => ['rgba(0, 255, 255, 0.2)', 'rgba(255, 0, 50, 0.8)'])
    .arcDashLength(0.4)
    .arcDashGap(0.2)
    .arcDashAnimateTime(1500)
    .arcsTransitionDuration(0)
    .pointColor(() => 'red')
    .pointAltitude(0.01)
    .pointRadius(0.2);

// Auto-rotate globe
world.controls().autoRotate = true;
world.controls().autoRotateSpeed = 0.5;

// Handle Resize
window.addEventListener('resize', () => {
    world.width(globeContainer.clientWidth);
    world.height(globeContainer.clientHeight);
});

// Connect to SSE for Valkyrie
const threatSource = new EventSource('/tactical/valkyrie/stream');
const threatLog = document.getElementById('threat-log-container');
const socStatus = document.getElementById('soc-status');

threatSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if(data.error) return;

    // Update SOC Status
    if(data.soc_status === "ALERT_CRITICAL") {
        socStatus.className = "px-2 py-1 text-xs bg-red-900/50 text-red-400 rounded animate-pulse";
        socStatus.innerText = `SOC: CRITICAL (${data.threat_rate} THRT/s)`;
    } else if (data.soc_status === "ALERT_HIGH") {
        socStatus.className = "px-2 py-1 text-xs bg-orange-900/50 text-orange-400 rounded";
        socStatus.innerText = `SOC: HIGH (${data.threat_rate} THRT/s)`;
    } else {
        socStatus.className = "px-2 py-1 text-xs bg-green-900/50 text-green-400 rounded";
        socStatus.innerText = `SOC: NORMAL (${data.threat_rate} THRT/s)`;
    }

    const t = data.threat;
    
    // Add Arc to Globe
    const arc = {
        startLat: t.source.lat,
        startLng: t.source.lon,
        endLat: t.target.lat,
        endLng: t.target.lon
    };
    arcsData.push(arc);
    // Keep only last 20 arcs to prevent memory leak
    if(arcsData.length > 20) arcsData.shift();
    world.arcsData(arcsData);

    // Add to Log
    const entry = document.createElement('div');
    entry.className = `threat-entry flex justify-between ${t.severity === 'CRITICAL' ? 'text-red-400' : 'text-cyan-400'}`;
    entry.innerHTML = `<span>[${t.type}] ${t.source.ip} &#8594; ${t.target.ip}</span> <span>${t.port}</span>`;
    threatLog.prepend(entry);
    
    if(threatLog.children.length > 15) {
        threatLog.removeChild(threatLog.lastChild);
    }
};


// ==========================================
// PROJECT AEGIS (Space Situational Awareness)
// ==========================================
const satContainer = document.getElementById('sat-container');
const weatherStatus = document.getElementById('weather-status');

async function fetchAegisData() {
    try {
        const res = await fetch('/tactical/aegis/space');
        const data = await res.json();

        // Update Weather
        const w = data.space_weather;
        if(w.status === "STORM") {
            weatherStatus.className = "text-xs text-red-400 animate-pulse font-bold";
            weatherStatus.innerText = `SWx: STORM (Kp ${w.kp_index})`;
        } else {
            weatherStatus.className = "text-xs text-blue-300";
            weatherStatus.innerText = `SWx: NORMAL (Kp ${w.kp_index})`;
        }

        // Update Satellite List
        satContainer.innerHTML = '';
        data.satellites.forEach(sat => {
            const el = document.createElement('div');
            el.className = "flex justify-between border-b border-blue-900/30 pb-1";
            el.innerHTML = `<span class="text-blue-200 truncate w-32">${sat.name}</span> 
                            <span class="text-right">Alt: ${Math.round(sat.alt)}km<br>Vel: ${sat.velocity_km_s.toFixed(2)}km/s</span>`;
            satContainer.appendChild(el);
        });

    } catch (e) {
        console.error("Aegis Fetch Error:", e);
    }
}
setInterval(fetchAegisData, 5000);
fetchAegisData();


// ==========================================
// PROJECT HEIMDALL (Geo Disasters)
// ==========================================
const map = L.map('mapViz', {
    zoomControl: false,
    attributionControl: false
}).setView([20, 0], 2);

// Use a dark map tile layer
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
}).addTo(map);

let geojsonLayer;

function getMarkerColor(severity) {
    if (severity === 'CRITICAL') return '#ef4444'; // Red
    if (severity === 'HIGH') return '#f97316'; // Orange
    if (severity === 'MEDIUM') return '#eab308'; // Yellow
    return '#3b82f6'; // Blue
}

async function fetchHeimdallData() {
    try {
        const res = await fetch('/tactical/heimdall/disasters');
        const data = await res.json();

        if (geojsonLayer) {
            map.removeLayer(geojsonLayer);
        }

        geojsonLayer = L.geoJSON(data, {
            pointToLayer: function (feature, latlng) {
                const color = getMarkerColor(feature.properties.severity);
                const radius = feature.properties.mag ? feature.properties.mag * 2 : 4;
                
                return L.circleMarker(latlng, {
                    radius: radius,
                    fillColor: color,
                    color: color,
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.6
                });
            },
            onEachFeature: function (feature, layer) {
                if (feature.properties && feature.properties.place) {
                    layer.bindPopup(`<b>${feature.properties.place}</b><br>Mag: ${feature.properties.mag}<br>Severity: ${feature.properties.severity}`);
                }
            }
        }).addTo(map);

    } catch (e) {
        console.error("Heimdall Fetch Error:", e);
    }
}
setInterval(fetchHeimdallData, 30000); // Earthquakes don't update every second
fetchHeimdallData();
