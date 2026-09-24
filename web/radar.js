document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('mac-table-body');
    const totalDevicesSpan = document.getElementById('total-devices');
    const lastScanSpan = document.getElementById('last-scan');
    const radarContainer = document.getElementById('radar-blips-container');

    // Modal elements
    const renameModal = document.getElementById('rename-modal');
    const modalMacDisplay = document.getElementById('modal-mac-display');
    const aliasInput = document.getElementById('alias-input');
    const cancelBtn = document.getElementById('cancel-btn');
    const saveBtn = document.getElementById('save-btn');

    let currentEditingMac = null;

    // Store assigned angles and distances for MACs so they don't jump around
    const macPositions = {};

    function getPositionForMac(mac) {
        if (!macPositions[mac]) {
            // Assign a random angle (0-360) and distance (10% to 90% of radius)
            const angle = Math.random() * 360;
            const distance = 10 + Math.random() * 80;
            macPositions[mac] = { angle, distance };
        }
        return macPositions[mac];
    }

    function createBlip(mac) {
        const { angle, distance } = getPositionForMac(mac);
        
        // Calculate X and Y based on angle and distance
        const rad = angle * (Math.PI / 180);
        const radius = 150; // Half of 300px radar
        const d = (distance / 100) * radius;
        
        const x = radius + d * Math.cos(rad);
        const y = radius + d * Math.sin(rad);

        const blip = document.createElement('div');
        blip.className = 'blip';
        blip.style.left = `${x}px`;
        blip.style.top = `${y}px`;
        
        // Add random animation delay so they don't all blink together
        blip.style.animationDelay = `${(angle / 360) * 4}s`; // Sync roughly with the sweep
        
        return blip;
    }

    async function fetchRadarData() {
        try {
            const response = await fetch('/api/radar/data');
            const data = await response.json();
            
            updateDashboard(data);
        } catch (error) {
            console.error("Error fetching radar data:", error);
        }
    }

    function updateDashboard(data) {
        const devices = data.devices || [];
        
        totalDevicesSpan.textContent = devices.length;
        
        const date = new Date(data.timestamp * 1000);
        lastScanSpan.textContent = date.toLocaleTimeString();

        // Update Table
        tableBody.innerHTML = '';
        radarContainer.innerHTML = '';

        devices.forEach((device, index) => {
            const mac = device.mac;
            const alias = device.alias;
            
            const displayName = alias ? alias : 'UNKNOWN DEVICE';
            const displayMac = mac.toUpperCase();

            // Add Table Row
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <div style="font-weight: bold; font-size: 1.1rem; text-shadow: 0 0 5px var(--neon-blue);">${displayName}</div>
                    <div style="font-size: 0.8rem; opacity: 0.7; font-family: 'Share Tech Mono';">${displayMac}</div>
                </td>
                <td><span class="status-badge ${alias ? 'status-safe' : 'status-warning'}">${alias ? 'IDENTIFIED' : 'UNKNOWN'}</span></td>
                <td><button class="action-btn rename-btn" data-mac="${mac}" data-alias="${alias || ''}">RENAME</button></td>
            `;
            tableBody.appendChild(tr);

            // Add Radar Blip
            const blip = createBlip(mac);
            radarContainer.appendChild(blip);
        });

        // Add event listeners to the new buttons
        document.querySelectorAll('.rename-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                currentEditingMac = e.target.getAttribute('data-mac');
                const currentAlias = e.target.getAttribute('data-alias');
                
                modalMacDisplay.textContent = currentEditingMac.toUpperCase();
                aliasInput.value = currentAlias;
                renameModal.classList.add('show');
                aliasInput.focus();
            });
        });
    }

    // Modal close handlers
    cancelBtn.addEventListener('click', () => {
        renameModal.classList.remove('show');
        currentEditingMac = null;
    });

    // Save alias handler
    saveBtn.addEventListener('click', async () => {
        if (!currentEditingMac) return;
        
        const newAlias = aliasInput.value.trim();
        if (!newAlias) {
            alert("Alias cannot be empty.");
            return;
        }

        try {
            const response = await fetch('/api/radar/alias', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mac: currentEditingMac, alias: newAlias })
            });
            
            if (response.ok) {
                renameModal.classList.remove('show');
                fetchRadarData(); // Refresh immediately
            } else {
                alert("Failed to save alias.");
            }
        } catch (error) {
            console.error("Error saving alias:", error);
            alert("Error saving alias.");
        }
    });

    // Initial fetch
    fetchRadarData();
    
    // Poll every 5 seconds
    setInterval(fetchRadarData, 5000);
});
