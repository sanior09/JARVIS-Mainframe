/**
 * J.A.R.V.I.S. (Ironman) Minecraft Companion Bot
 * Features:
 * 1. Autonomous Pathfinding (Follow, Stop, Jump)
 * 2. Woodcutter & Miner (Chop Wood & Deliver items to Boss)
 * 3. Bodyguard Combat Protocol (Mineflayer-PVP vs Hostile Mobs)
 * 4. Local HTTP REST Bridge (For J.A.R.V.I.S. Mainframe Voice Control)
 */

const fs = require('fs');
const path = require('path');
const http = require('http');
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
const { plugin: collectBlock } = require('mineflayer-collectblock');
const { plugin: pvp } = require('mineflayer-pvp');

const SKILLS_DIR = path.join(__dirname, 'skills');
const MANIFEST_PATH = path.join(SKILLS_DIR, 'skills_manifest.json');
const LOCATIONS_PATH = path.join(__dirname, 'locations.json');

function loadLocations() {
    try {
        if (fs.existsSync(LOCATIONS_PATH)) {
            return JSON.parse(fs.readFileSync(LOCATIONS_PATH, 'utf8') || '{}');
        }
    } catch (e) {
        console.error('[JARVIS] Load locations error:', e);
    }
    return { home: null, waypoints: {} };
}

function saveHomeLocation(x, y, z) {
    if (typeof x === 'object' && x !== null) {
        z = x.z;
        y = x.y;
        x = x.x;
    }
    const locs = loadLocations();
    locs.home = {
        x: Math.round(x * 10) / 10,
        y: Math.round(y * 10) / 10,
        z: Math.round(z * 10) / 10,
        dimension: (bot && bot.game) ? bot.game.dimension : 'overworld',
        saved_at: new Date().toISOString()
    };
    try {
        fs.writeFileSync(LOCATIONS_PATH, JSON.stringify(locs, null, 2), 'utf8');
        console.log(`[JARVIS] Saved Home Base at (${locs.home.x}, ${locs.home.y}, ${locs.home.z})`);
    } catch (e) {
        console.error('[JARVIS] Save home error:', e);
    }
    return locs.home;
}

function getHomeLocation() {
    const locs = loadLocations();
    return locs.home || null;
}

const PORT = parseInt(process.argv[2] || process.env.MC_PORT || '60706');
const HOST = process.argv[3] || process.env.MC_HOST || '127.0.0.1';
const HTTP_PORT = parseInt(process.env.HTTP_BRIDGE_PORT || '5056');
const USERNAME = 'JARVIS_Suit';

console.log(`[JARVIS] Connecting to Minecraft LAN server at ${HOST}:${PORT} as '${USERNAME}' (1.20.4)...`);

const bot = mineflayer.createBot({
    host: HOST,
    port: PORT,
    username: USERNAME,
    version: '1.20.4',
    auth: 'offline'
});

// Load plugins
bot.loadPlugin(pathfinder);
bot.loadPlugin(collectBlock);
bot.loadPlugin(pvp);

let isGuarding = false;
let isWorking = false;
let guardInterval = null;
let mcData = null;

function getBoss() {
    const targetBoss = process.env.MC_BOSS_NAME || '';
    if (targetBoss && bot.players[targetBoss]) return bot.players[targetBoss];
    return Object.values(bot.players).find(p => p.username !== bot.username);
}

bot.on('spawn', () => {
    mcData = require('minecraft-data')(bot.version);
    const defaultMove = new Movements(bot, mcData);
    defaultMove.allowSprinting = true;
    defaultMove.canDig = true;           // Allow digging blocks to navigate out of trenches
    defaultMove.canParkour = true;
    defaultMove.maxDropDown = 2;         // Maximum 2 blocks drop to prevent jumping into deep pits!
    
    // Enable scaffolding (auto-pillaring with dirt/stone to jump out of pits)
    const scaffoldNames = ['dirt', 'cobblestone', 'cobbled_deepslate', 'stone', 'oak_planks', 'spruce_planks'];
    defaultMove.scaffoldingBlocks = scaffoldNames.map(n => mcData.blocksByName[n]?.id).filter(Boolean);
    bot.pathfinder.setMovements(defaultMove);

    console.log(`[JARVIS] Spawned in world! Position: ${bot.entity.position}`);
    console.log(`[JARVIS] Current GameMode: ${bot.game.gameMode}`);

    // Enable all skin parts
    try {
        bot.setSettings({
            skinParts: {
                showCape: true,
                showJacket: true,
                showLeftSleeve: true,
                showRightSleeve: true,
                showLeftPants: true,
                showRightPants: true,
                showHat: true
            }
        });
    } catch (e) {
        console.error('[JARVIS] Skin settings error:', e);
    }

    setTimeout(() => {
        bot.chat('J.A.R.V.I.S. (Mark Suit) online and standing by, Sir!');
        bot.swingArm('right');
        bot.setControlState('jump', true);
        setTimeout(() => bot.setControlState('jump', false), 400);
    }, 1000);
});

bot.on('sleep', () => {
    if (bot.entity && bot.entity.position) {
        saveHomeLocation(bot.entity.position);
    }
});

bot.on('wake', () => {
    bot.chat('อรุณสวัสดิ์ครับเจ้านาย! ชาร์จพลังงานเตาปฏิกรณ์ Arc Reactor เต็ม 100% แล้วครับ!');
});

bot.on('death', () => {
    bot.chat('เตาปฏิกรณ์ Arc Reactor เสียหาย... กำลังเริ่มระบบ Emergency Reboot คืนชีพครับ!');
    setTimeout(() => {
        try {
            bot.respawn();
            setTimeout(() => {
                handleFollow();
            }, 1000);
        } catch (e) {}
    }, 1200);
});

let isAutoEating = false;
bot.on('health', async () => {
    if (bot.food < 15 && !isAutoEating && !bot.isSleeping) {
        const foodItem = bot.inventory.items().find(i => {
            const n = i.name.toLowerCase();
            return n.includes('bread') || n.includes('cooked_') || n.includes('beef') || 
                   n.includes('pork') || n.includes('mutton') || n.includes('chicken') || 
                   n.includes('apple') || n.includes('carrot') || n.includes('potato');
        });
        if (foodItem) {
            isAutoEating = true;
            try {
                await bot.equip(foodItem, 'hand');
                await bot.consume();
                console.log('[JARVIS] Life Support: Auto-ate', foodItem.name);
            } catch (e) {}
            isAutoEating = false;
        }
    }
});

bot.on('playerCollect', (collector, collected) => {
    if (collector.username === bot.username) {
        // Only attempt auto-equip quietly if inventory actually has armor
        const hasArmor = bot.inventory.items().some(it => {
            const n = it.name.toLowerCase();
            return n.includes('helmet') || n.includes('chestplate') || n.includes('leggings') || 
                   n.includes('boots') || n.includes('cap') || n.includes('tunic') || n.includes('pants');
        });
        if (hasArmor) {
            setTimeout(() => {
                handleEquipArmor(true).catch(() => {});
            }, 500);
        }
    }
});

// ---------------------------------------------------------------------------
// Action Handlers
// ---------------------------------------------------------------------------

function handleRecallToBoss(forceTp = false) {
    isGuarding = false;
    isWorking = false;
    try { bot.stopDigging(); } catch (e) {}
    const boss = getBoss();
    const bossName = boss ? boss.username : (process.env.MC_BOSS_NAME || 'Player');

    if (forceTp) {
        bot.pathfinder.setGoal(null);
        bot.chat(`/tp @s ${bossName}`);
        bot.chat("เปิดระบบ Repulsor Jump วาร์ปกลับขึ้นมารายงานตัวกับเจ้านายเรียบร้อยครับ!");
        return "Teleported to boss";
    }

    if (!boss || !boss.entity) {
        // Boss out of render distance, auto-teleport directly
        bot.pathfinder.setGoal(null);
        bot.chat(`/tp @s ${bossName}`);
        bot.chat("มองไม่เห็นเจ้านาย ขอเปิดระบบ Repulsor Jump วาร์ปไปหาเจ้านายครับ!");
        return "Teleported to boss";
    }

    const dist = bot.entity.position.distanceTo(boss.entity.position);
    if (dist > 25) {
        // Too far away or stuck down deep
        bot.pathfinder.setGoal(null);
        bot.chat(`/tp @s ${bossName}`);
        bot.chat("ระยะห่างเกิน 25 บล็อก วาร์ปกลับมารายงานตัวข้างๆ เจ้านายเรียบร้อยครับ!");
        return "Teleported to boss";
    }

    const goal = new goals.GoalFollow(boss.entity, 2);
    bot.pathfinder.setGoal(goal, true);
    bot.chat("กำลังวิ่งตามเจ้านายครับ!");
    return "Following boss";
}

function handleFollow() {
    return handleRecallToBoss(false);
}

function handleSetHome(text = '') {
    const boss = getBoss();
    let pos = bot.entity ? bot.entity.position : null;
    let note = 'ตำแหน่งของผม';

    if (boss && boss.entity && (text.includes('ตรงนี้') || text.includes('ที่ผม') || text.includes('ผมอยู่') || text.includes('ฉันอยู่'))) {
        pos = boss.entity.position;
        note = 'ตำแหน่งที่เจ้านายยืนอยู่';
    } else if (!pos && boss && boss.entity) {
        pos = boss.entity.position;
        note = 'ตำแหน่งเจ้านาย';
    }

    if (!pos) {
        bot.chat("ไม่สามารถระบุตำแหน่งเพื่อเซฟบ้านได้ครับ");
        return "Position error";
    }

    const home = saveHomeLocation(pos.x, pos.y, pos.z);
    bot.chat(`บันทึก${note} (X: ${Math.round(home.x)}, Y: ${Math.round(home.y)}, Z: ${Math.round(home.z)}) เป็นจุดเซฟบ้าน (Home Base) เรียบร้อยแล้วครับเจ้านาย!`);
    return "Home set";
}

function handleReportHome() {
    const home = getHomeLocation();
    if (!home) {
        bot.chat("ยังไม่มีการบันทึกพิกัดบ้านครับเจ้านาย ให้ผมนอนเตียง หรือสั่ง 'เซฟบ้าน' ก่อนนะครับ");
        return "No home set";
    }
    bot.chat(`พิกัดบ้าน (Home Base): X: ${Math.round(home.x)}, Y: ${Math.round(home.y)}, Z: ${Math.round(home.z)} (${home.dimension || 'overworld'}) ครับเจ้านาย!`);
    return `Home at ${home.x}, ${home.y}, ${home.z}`;
}

function handleTeleportHome() {
    isGuarding = false;
    isWorking = false;
    try { bot.stopDigging(); } catch (e) {}
    bot.pathfinder.setGoal(null);

    const home = getHomeLocation();
    if (!home) {
        bot.chat("ยังไม่มีการบันทึกพิกัดบ้านเลยครับเจ้านาย ให้ผมนอนเตียง หรือพิมพ์ 'เซฟบ้าน' ก่อนนะครับ!");
        return "No home set";
    }

    try {
        bot.chat(`/tp @s ${home.x} ${home.y} ${home.z}`);
        bot.chat(`เปิดระบบ Repulsor Jump วาร์ปกลับสู่ฐานทัพบ้าน (Home Base) เรียบร้อยแล้วครับเจ้านาย!`);
        return "Teleported home";
    } catch (e) {
        bot.chat(`วาร์ปกลับบ้านไม่สำเร็จ: ${e.message}`);
        return "Teleport home error";
    }
}

function handleStop() {
    isGuarding = false;
    isWorking = false;
    if (guardInterval) clearInterval(guardInterval);
    try { bot.stopDigging(); } catch (e) {}
    bot.pathfinder.setGoal(null);
    bot.pvp.stop();
    bot.chat("หยุดรอสแตนด์บายตรงนี้ครับ");
    return "Stopped";
}

function handleJump() {
    bot.setControlState('jump', true);
    setTimeout(() => bot.setControlState('jump', false), 400);
    bot.chat("รับทราบครับ!");
    return "Jumped";
}

function isToolOrWeaponOrArmor(item) {
    if (!item || !item.name) return false;
    const n = item.name.toLowerCase();
    return n.includes('_pickaxe') || 
           n.includes('_axe') || 
           n.includes('_sword') || 
           n.includes('_shovel') || 
           n.includes('_hoe') ||
           n.includes('helmet') || 
           n.includes('chestplate') || 
           n.includes('leggings') || 
           n.includes('boots') ||
           n.includes('shield') ||
           n === 'crafting_table';
}

async function handleChopWood(text = '') {
    if (!mcData) mcData = require('minecraft-data')(bot.version);
    isGuarding = false;

    // Detect requested count from text (e.g. "ตัดไม้ 10 อัน")
    let targetCount = 3;
    const matchNum = text.match(/\d+/);
    if (matchNum) {
        targetCount = Math.min(parseInt(matchNum[0]), 20);
    }

    const logNames = [
        'oak_log', 'birch_log', 'spruce_log', 'jungle_log', 
        'acacia_log', 'dark_oak_log', 'mangrove_log', 'cherry_log'
    ];
    const logIds = logNames.map(name => mcData.blocksByName[name]?.id).filter(Boolean);

    bot.chat(`รับทราบครับเจ้านาย! กำลังเริ่มออกไปตัดไม้ ${targetCount} ท่อน...`);

    isWorking = true;
    let chopped = 0;
    let attempts = 0;
    const maxAttempts = targetCount * 3;

    while (chopped < targetCount && attempts < maxAttempts) {
        if (!isWorking) break;
        attempts++;
        const targetBlock = bot.findBlock({ matching: logIds, maxDistance: 32 });
        if (!targetBlock) {
            if (chopped === 0) {
                bot.chat("ไม่พบต้นไม้ในระยะ 32 บล็อกครับเจ้านาย");
                return "No trees found within 32 blocks";
            }
            break;
        }

        try {
            const p = targetBlock.position;
            await bot.pathfinder.goto(new goals.GoalNear(p.x, p.y, p.z, 2.5));

            // Equip axe if available
            const axe = bot.inventory.items().find(it => it.name.includes('_axe'));
            if (axe) {
                try { await bot.equip(axe, 'hand'); } catch (e) {}
            }

            await bot.lookAt(targetBlock.position.offset(0.5, 0.5, 0.5));
            await bot.dig(targetBlock);
            chopped++;
            console.log(`[JARVIS] Chopped log ${chopped}/${targetCount} at ${targetBlock.position}`);

            // Active dropped log entity pickup
            try {
                const dropItem = bot.nearestEntity(e => {
                    return e && e.name === 'item' && e.position && e.position.distanceTo(p) < 4.0;
                });
                if (dropItem) {
                    await bot.pathfinder.goto(new goals.GoalNear(dropItem.position.x, dropItem.position.y, dropItem.position.z, 0.5));
                } else {
                    await bot.pathfinder.goto(new goals.GoalNear(p.x, p.y, p.z, 0.8));
                }
            } catch (pickupErr) {}
            await new Promise(r => setTimeout(r, 200));
        } catch (err) {
            console.error('[JARVIS] Dig log error:', err.message);
            await new Promise(r => setTimeout(r, 300));
        }
    }

    if (chopped > 0) {
        if (text.includes('กล่อง') || text.includes('หีบ') || text.includes('chest')) {
            const preferHome = text.includes('บ้าน') || text.includes('home');
            if (preferHome) {
                bot.chat(`ตัดไม้เสร็จเรียบร้อยแล้ว ${chopped} ท่อนครับ! กำลังนำกลับไปเก็บเข้ากล่องที่บ้าน`);
            } else {
                bot.chat(`ตัดไม้เสร็จเรียบร้อยแล้ว ${chopped} ท่อนครับ! กำลังนำไปเก็บเข้ากล่อง`);
            }
            setTimeout(() => {
                depositToNearestChest('wood', preferHome);
            }, 1200);
        } else {
            bot.chat(`ตัดไม้เสร็จเรียบร้อยแล้ว ${chopped} ท่อนครับ! กำลังนำไปส่งให้เจ้านาย`);
            setTimeout(() => {
                deliverItemsToBoss('wood');
            }, 1200);
        }
    } else {
        bot.chat("ไม่สามารถเข้าถึงต้นไม้ได้ครับเจ้านาย");
    }

    return `Chopped ${chopped} logs`;
}

async function deliverItemsToBoss(filterType = 'all') {
    const boss = getBoss();
    if (!boss || !boss.entity) {
        bot.chat("มองไม่เห็นเจ้านาย ขอวางของไว้ตรงนี้นะครับ");
        return "Boss not visible";
    }

    try {
        const dist = bot.entity.position.distanceTo(boss.entity.position);
        if (dist > 3) {
            bot.chat("กำลังเดินนำของไปส่งให้ครับ...");
            // Allow up to 5 seconds to navigate back to boss
            await Promise.race([
                bot.pathfinder.goto(new goals.GoalFollow(boss.entity, 2)),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Navigation timeout')), 5000))
            ]);
        }
    } catch (e) {
        console.log('[JARVIS] Delivery walk note:', e.message);
        // If walk was blocked or timed out, use Repulsor Jump (/tp) to instantly return to boss!
        try {
            bot.chat(`/tp @s ${boss.username}`);
            await new Promise(r => setTimeout(r, 400));
        } catch (tpErr) {}
    }

    if (boss.entity) {
        try {
            await bot.lookAt(boss.entity.position.offset(0, 1.5, 0));
        } catch (e) {}
    }

    const items = bot.inventory.items();
    if (items.length === 0) {
        bot.chat("กระเป๋าของผมว่างเปล่า ไม่มีของเลยครับเจ้านาย");
        return "Inventory empty";
    }

    let toDrop = [];
    let label = 'ของทั้งหมด';

    if (filterType.startsWith('crafted:')) {
        const targetName = filterType.replace('crafted:', '');
        toDrop = items.filter(it => it.name === targetName || it.name.includes(targetName));
        const itemObj = mcData ? mcData.itemsByName[targetName] : null;
        label = itemObj ? (itemObj.displayName || targetName) : targetName;
    } else if (filterType === 'bed') {
        toDrop = items.filter(it => it.name.includes('bed'));
        label = 'เตียงนอน';
    } else if (filterType === 'cactus') {
        toDrop = items.filter(it => it.name.includes('cactus'));
        label = 'กระบองเพชร';
    } else if (filterType === 'wood') {
        // EXCLUDE wooden tools! Only deliver pure wood/logs/planks
        toDrop = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name.includes('_log') || it.name.includes('log') || 
            it.name.includes('_planks') || it.name.includes('planks') ||
            it.name.endsWith('_wood') || it.name === 'stick'
        ));
        label = 'ไม้';
    } else if (filterType === 'stone') {
        // EXCLUDE diorite, andesite, granite and tools! Only cobblestone/stone/deepslate
        toDrop = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name === 'stone' || it.name === 'cobblestone' || 
            it.name.includes('cobble') || it.name.includes('deepslate')
        ));
        label = 'หิน';
    } else if (filterType === 'dirt') {
        toDrop = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name.includes('dirt') || it.name.includes('sand') || it.name.includes('gravel')
        ));
        label = 'ดิน/ทราย';
    } else if (filterType === 'ore') {
        toDrop = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name.includes('coal') || it.name.includes('iron') || 
            it.name.includes('copper') || it.name.includes('gold') || 
            it.name.includes('diamond') || it.name.includes('raw_')
        ));
        label = 'แร่';
    } else if (filterType === 'food') {
        toDrop = items.filter(it => {
            const n = it.name.toLowerCase();
            return n.includes('bread') || n.includes('beef') || n.includes('pork') || 
                   n.includes('mutton') || n.includes('chicken') || n.includes('apple') || 
                   n.includes('carrot') || n.includes('potato');
        });
        label = 'อาหาร';
    } else if (filterType === 'everything') {
        toDrop = items;
        label = 'ของทั้งหมดในตัวรวมอุปกรณ์';
    } else {
        // 'all': drop all gathered items, but KEEP weapons, tools, armor, and crafting table!
        toDrop = items.filter(it => !isToolOrWeaponOrArmor(it));
        label = 'ของทั้งหมด';
    }

    if (toDrop.length === 0) {
        bot.chat(`ผมไม่มี${label}ในกระเป๋าครับเจ้านาย`);
        return `No ${label} in inventory`;
    }

    bot.chat(`นี่ครับ${label}สำหรับเจ้านาย!`);
    for (const item of toDrop) {
        try {
            await bot.tossStack(item);
            await new Promise(r => setTimeout(r, 200));
        } catch (e) {
            console.error('[JARVIS] Toss error:', e);
        }
    }
    bot.chat(`ส่งมอบ${label}เรียบร้อยแล้วครับ!`);
    return `Delivered ${label}`;
}

function handleDropItems(filter = 'all') {
    return deliverItemsToBoss(filter);
}

async function depositToNearestChest(filterType = 'all', preferHome = false) {
    if (!mcData) mcData = require('minecraft-data')(bot.version);

    const chestIds = ['chest', 'trapped_chest', 'barrel']
        .map(n => mcData.blocksByName[n]?.id)
        .filter(Boolean);

    const home = getHomeLocation();

    // If preferHome is true, warp directly to home base!
    if (preferHome) {
        if (home) {
            bot.chat("กำลังวาร์ปกลับไปเก็บของที่บ้านครับ...");
            try {
                bot.chat(`/tp @s ${home.x} ${home.y} ${home.z}`);
                await new Promise(r => setTimeout(r, 600));
            } catch (e) {}
        } else {
            bot.chat("ยังไม่มีการบันทึกพิกัดบ้านครับ ขอเก็บของที่กล่องใกล้ตัวหรือใกล้เจ้านายก่อนนะครับ");
        }
    }

    let chestBlock = bot.findBlock({
        matching: chestIds,
        maxDistance: 48
    });

    if (!chestBlock) {
        // If not found in current area, return to home base (if set) or boss base!
        if (home) {
            bot.chat("กำลังกลับไปที่ฐานบ้านเพื่อนำของไปเก็บเข้ากล่องครับ...");
            try {
                bot.chat(`/tp @s ${home.x} ${home.y} ${home.z}`);
                await new Promise(r => setTimeout(r, 600));
            } catch (e) {}
            chestBlock = bot.findBlock({ matching: chestIds, maxDistance: 32 });
        } else {
            const boss = getBoss();
            if (boss && boss.entity) {
                const dist = bot.entity.position.distanceTo(boss.entity.position);
                if (dist > 12) {
                    bot.chat("กำลังกลับไปที่ฐานของเจ้านายเพื่อนำของไปเก็บเข้ากล่องครับ...");
                    try {
                        bot.chat(`/tp @s ${boss.username}`);
                        await new Promise(r => setTimeout(r, 600));
                    } catch (e) {}
                    chestBlock = bot.findBlock({ matching: chestIds, maxDistance: 32 });
                }
            }
        }
    }

    if (!chestBlock) {
        bot.chat("ไม่พบกล่องหรือหีบในบริเวณนี้ครับเจ้านาย รบกวนวางกล่องไว้ใกล้ๆ หน่อยนะครับ!");
        return "No chest found";
    }

    bot.chat("กำลังเดินไปเก็บของเข้ากล่องครับ...");
    try {
        await Promise.race([
            bot.pathfinder.goto(new goals.GoalNear(chestBlock.position.x, chestBlock.position.y, chestBlock.position.z, 2.5)),
            new Promise((_, reject) => setTimeout(() => reject(new Error('Navigation timeout')), 6000))
        ]);
    } catch (e) {
        const dist = bot.entity.position.distanceTo(chestBlock.position);
        if (dist > 3.5) {
            try {
                bot.chat(`/tp @s ${chestBlock.position.x} ${chestBlock.position.y + 1} ${chestBlock.position.z}`);
                await new Promise(r => setTimeout(r, 400));
            } catch (tpErr) {}
        }
    }

    const items = bot.inventory.items();
    let toDeposit = [];
    let label = 'ของทั้งหมด';

    if (filterType === 'wood') {
        toDeposit = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name.includes('_log') || it.name.includes('log') || 
            it.name.includes('_planks') || it.name.includes('planks') ||
            it.name.endsWith('_wood') || it.name === 'stick'
        ));
        label = 'ไม้';
    } else if (filterType === 'stone') {
        toDeposit = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name === 'stone' || it.name === 'cobblestone' || 
            it.name === 'deepslate' || it.name === 'cobbled_deepslate'
        ));
        label = 'หิน';
    } else if (filterType === 'ore') {
        toDeposit = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name.includes('coal') || it.name.includes('iron') || 
            it.name.includes('copper') || it.name.includes('gold') || 
            it.name.includes('diamond') || it.name.includes('raw_')
        ));
        label = 'แร่';
    } else if (filterType === 'cactus') {
        toDeposit = items.filter(it => it.name.includes('cactus'));
        label = 'กระบองเพชร';
    } else if (filterType === 'dirt') {
        toDeposit = items.filter(it => !isToolOrWeaponOrArmor(it) && (
            it.name.includes('dirt') || it.name.includes('sand') || it.name.includes('gravel')
        ));
        label = 'ดิน/ทราย';
    } else {
        toDeposit = items.filter(it => !isToolOrWeaponOrArmor(it));
        label = 'ทรัพยากรทั้งหมด';
    }

    if (toDeposit.length === 0) {
        bot.chat(`ไม่มี${label}ในกระเป๋าที่จะเก็บเข้ากล่องครับเจ้านาย`);
        return "Nothing to deposit";
    }

    try {
        await bot.lookAt(chestBlock.position.offset(0.5, 0.5, 0.5));
        const chest = await bot.openContainer(chestBlock);
        let depositedCount = 0;

        for (const item of toDeposit) {
            try {
                await chest.deposit(item.type, null, item.count);
                depositedCount += item.count;
                await new Promise(r => setTimeout(r, 120));
            } catch (err) {
                console.error('[JARVIS] Chest deposit error:', err.message);
            }
        }

        chest.close();
        bot.chat(`นำ${label}จำนวน ${depositedCount} ชิ้น เก็บเข้ากล่องเรียบร้อยแล้วครับเจ้านาย!`);
        return `Deposited ${depositedCount} items`;
    } catch (err) {
        console.error('[JARVIS] Open chest error:', err);
        bot.chat(`เปิดกล่องไม่สำเร็จครับ: ${err.message}`);
        return `Chest error: ${err.message}`;
    }
}

async function withdrawFromNearestChest(keyword, count = 64) {
    if (!mcData) mcData = require('minecraft-data')(bot.version);

    const chestIds = ['chest', 'trapped_chest', 'barrel']
        .map(n => mcData.blocksByName[n]?.id)
        .filter(Boolean);

    let chestBlock = bot.findBlock({
        matching: chestIds,
        maxDistance: 48
    });

    if (!chestBlock) {
        const boss = getBoss();
        if (boss && boss.entity) {
            const dist = bot.entity.position.distanceTo(boss.entity.position);
            if (dist > 12) {
                bot.chat("กำลังกลับไปที่ฐานของเจ้านายเพื่อเปิดกล่องครับ...");
                try {
                    bot.chat(`/tp @s ${boss.username}`);
                    await new Promise(r => setTimeout(r, 600));
                } catch (e) {}
                chestBlock = bot.findBlock({ matching: chestIds, maxDistance: 32 });
            }
        }
    }

    if (!chestBlock) {
        bot.chat("ไม่พบกล่องหรือหีบในบริเวณนี้ครับเจ้านาย");
        return "No chest found";
    }

    bot.chat("กำลังเดินไปเปิดกล่อง...");
    try {
        await bot.pathfinder.goto(new goals.GoalNear(chestBlock.position.x, chestBlock.position.y, chestBlock.position.z, 2.5));
    } catch (e) {}

    try {
        await bot.lookAt(chestBlock.position.offset(0.5, 0.5, 0.5));
        const chest = await bot.openContainer(chestBlock);
        const containerItems = chest.containerItems();

        if (containerItems.length === 0) {
            chest.close();
            bot.chat("ในกล่องว่างเปล่า ไม่มีไอเทมเลยครับเจ้านาย");
            return "Chest empty";
        }

        let target = null;
        const kw = (keyword || '').toLowerCase().trim();
        if (kw) {
            target = containerItems.find(it => it.name.toLowerCase().includes(kw));
        } else {
            target = containerItems[0];
        }

        if (!target) {
            chest.close();
            bot.chat(`ไม่พบ ${keyword} ในกล่องครับ`);
            return "Item not in chest";
        }

        const amountToTake = Math.min(count, target.count);
        await chest.withdraw(target.type, null, amountToTake);
        chest.close();
        bot.chat(`หยิบ ${target.displayName || target.name} จำนวน ${amountToTake} ชิ้น ออกมาจากกล่องเรียบร้อยครับ!`);
        return `Withdrew ${amountToTake} ${target.name}`;
    } catch (err) {
        bot.chat(`ไม่สามารถหยิบของได้: ${err.message}`);
        return `Withdraw error: ${err.message}`;
    }
}

function handleGuard() {
    isGuarding = true;
    bot.chat("เปิดระบบคุ้มกัน (Bodyguard Protocol) พร้อมสกัดกั้นศัตรูครับเจ้านาย!");

    if (guardInterval) clearInterval(guardInterval);
    guardInterval = setInterval(() => {
        if (!isGuarding) {
            clearInterval(guardInterval);
            return;
        }

        const boss = getBoss();
        const centerPos = boss && boss.entity ? boss.entity.position : bot.entity.position;

        // Find hostile mob within 16 blocks
        const hostiles = Object.values(bot.entities).filter(e => {
            if (!e || !e.position) return false;
            const name = e.name ? e.name.toLowerCase() : '';
            const isHostile = (
                name.includes('zombie') || name.includes('skeleton') || 
                name.includes('spider') || name.includes('creeper') || 
                name.includes('witch') || name.includes('enderman') ||
                name.includes('pillager')
            );
            return isHostile && e.position.distanceTo(centerPos) < 16;
        });

        if (hostiles.length > 0 && !bot.pvp.target) {
            const targetMob = hostiles[0];
            bot.chat(`ตรวจพบศัตรู: ${targetMob.name || 'มอนสเตอร์'} เข้าสู่ระยะ! โจมตีทันที!`);
            
            // Equip best weapon
            const weapon = bot.inventory.items().find(i => i.name.includes('sword') || i.name.includes('axe'));
            if (weapon) {
                bot.equip(weapon, 'hand').catch(() => {});
            }

            bot.pvp.attack(targetMob);
        } else if (hostiles.length === 0 && !bot.pvp.target && boss && boss.entity) {
            // No enemies nearby, stay near boss
            const dist = bot.entity.position.distanceTo(boss.entity.position);
            if (dist > 4) {
                bot.pathfinder.setGoal(new goals.GoalFollow(boss.entity, 2), true);
            }
        }
    }, 1000);

    return "Bodyguard mode active";
}

async function handleSleep() {
    isGuarding = false;
    const bedBlock = bot.findBlock({
        matching: block => bot.isABed(block),
        maxDistance: 16
    });

    if (!bedBlock) {
        bot.chat("ไม่พบเตียงนอนในระยะ 16 บล็อกครับเจ้านาย วางเตียงให้ผมด้วยนะครับ!");
        return "No bed found";
    }

    try {
        bot.chat("กำลังเดินไปที่เตียงครับ...");
        await bot.pathfinder.goto(new goals.GoalGetToBlock(bedBlock.position.x, bedBlock.position.y, bedBlock.position.z));
        // Automatically save this bed position as persistent Home Base immediately
        saveHomeLocation(bedBlock.position.x, bedBlock.position.y, bedBlock.position.z);

        await bot.sleep(bedBlock);
        bot.chat("เข้าสู่โหมดพักผ่อน ชาร์จเตาปฏิกรณ์ Arc Reactor zZz... (บันทึกเตียงนี้เป็นบ้านเรียบร้อยครับ)");
        return "Sleeping in bed";
    } catch (err) {
        console.error('[JARVIS] Sleep note/error:', err.message);
        if (err.message && err.message.includes('occupied')) {
            bot.chat("บันทึกพิกัดเตียงนี้เป็นบ้านเรียบร้อยครับเจ้านาย! (เตียงนี้มีคนนอนอยู่ ผมจะสแตนด์บายเฝ้าข้างๆ เตียงให้นะครับ)");
        } else if (err.message && err.message.includes('day')) {
            bot.chat("บันทึกพิกัดเตียงนี้เป็นบ้านเรียบร้อยครับเจ้านาย! (ตอนนี้ยังไม่มืด นอนไม่ได้ ผมสแตนด์บายรอนะครับ)");
        } else {
            bot.chat(`บันทึกพิกัดเตียงเป็นบ้านเรียบร้อยครับเจ้านาย! (${err.message})`);
        }
        return `Sleep handled: ${err.message}`;
    }
}

async function handleWake() {
    if (!bot.isSleeping) {
        bot.chat("ผมไม่ได้นอนอยู่ครับเจ้านาย สแตนด์บายอยู่เสมอครับ!");
        return "Not sleeping";
    }
    try {
        await bot.wake();
        bot.chat("ตื่นแล้วครับเจ้านาย! พร้อมลุยต่อ!");
        return "Woke up";
    } catch (err) {
        return `Wake error: ${err.message}`;
    }
}

async function handleMineBlocks(category = 'stone', text = '') {
    if (!mcData) mcData = require('minecraft-data')(bot.version);
    isGuarding = false;

    let targetCount = 3;
    const matchNum = text.match(/\d+/);
    if (matchNum) {
        targetCount = Math.min(parseInt(matchNum[0]), 20);
    }

    let blockNames = [];
    let toolKeyword = '_pickaxe';
    let label = 'หิน';

    if (category === 'dirt' || text.includes('ดิน') || text.includes('ทราย')) {
        blockNames = ['dirt', 'grass_block', 'sand', 'gravel'];
        toolKeyword = '_shovel';
        label = 'ดิน/ทราย';
    } else if (category === 'ore' || text.includes('แร่') || text.includes('ถ่าน') || text.includes('เหล็ก')) {
        blockNames = ['coal_ore', 'deepslate_coal_ore', 'iron_ore', 'deepslate_iron_ore', 'copper_ore'];
        toolKeyword = '_pickaxe';
        label = 'แร่';
    } else if (category === 'cactus' || text.includes('กระบองเพชร') || text.includes('cactus')) {
        blockNames = ['cactus'];
        toolKeyword = '';
        label = 'กระบองเพชร';
    } else {
        // Pure Stone and Cobblestone only (exclusively cobblestone, stone, deepslate)
        blockNames = ['stone', 'cobblestone', 'deepslate', 'cobbled_deepslate'];
        toolKeyword = '_pickaxe';
        label = 'หิน';
    }

    if (toolKeyword === '_pickaxe') {
        const hasPick = bot.inventory.items().some(it => it.name.includes('_pickaxe'));
        if (!hasPick) {
            bot.chat("เจ้านายครับ ผมไม่มีที่ขุด (Pickaxe) เลย รบกวนโยนที่ขุดให้ผมหน่อยนะครับ (ขุดมือเปล่าหินจะไม่ดรอป)");
        }
    }

    let unit = 'ก้อน';
    let actionVerb = 'ขุด';
    if (category === 'cactus' || text.includes('กระบองเพชร') || text.includes('cactus')) {
        unit = 'ต้น';
        actionVerb = 'ตัด';
    } else if (category === 'dirt' || text.includes('ดิน') || text.includes('ทราย')) {
        unit = 'บล็อก';
        actionVerb = 'ขุด';
    } else if (category === 'wood' || text.includes('ไม้')) {
        unit = 'ท่อน';
        actionVerb = 'ตัด';
    }

    const blockIds = blockNames.map(name => mcData.blocksByName[name]?.id).filter(Boolean);
    bot.chat(`กำลังออกไป${actionVerb}${label}จำนวน ${targetCount} ${unit}ให้ครับเจ้านาย!`);

    isWorking = true;
    let mined = 0;
    const attemptedPositions = new Set();

    let attempts = 0;
    const maxAttempts = targetCount * 3;

    while (mined < targetCount && attempts < maxAttempts) {
        if (!isWorking) break;
        attempts++;
        const currentY = bot.entity.position.y;
        const botFloor = bot.entity.position.floored();

        // Pass 1: Surface quarrying - look for exposed blocks at or near same elevation (±2 blocks)
        let targetBlock = bot.findBlock({
            matching: blockIds,
            maxDistance: 32,
            useExtraInfo: (block) => {
                const key = `${block.position.x},${block.position.y},${block.position.z}`;
                if (attemptedPositions.has(key)) return false;

                // CRITICAL: Avoid digging straight down under feet (prevents digging into holes/wells)
                if (block.position.x === botFloor.x && block.position.z === botFloor.z && block.position.y <= botFloor.y) {
                    return false;
                }

                // Prevent digging into deep ravines or caves (keep within ±2 vertical blocks)
                if (Math.abs(block.position.y - currentY) > 2) return false;

                const up = bot.blockAt(block.position.offset(0, 1, 0));
                const north = bot.blockAt(block.position.offset(0, 0, -1));
                const south = bot.blockAt(block.position.offset(0, 0, 1));
                const east = bot.blockAt(block.position.offset(1, 0, 0));
                const west = bot.blockAt(block.position.offset(-1, 0, 0));
                const adjacent = [up, north, south, east, west];
                return adjacent.some(b => b && (b.name === 'air' || b.name === 'water'));
            }
        });

        // Pass 2: Slightly wider vertical margin (±3 blocks) but never deep into holes
        if (!targetBlock) {
            targetBlock = bot.findBlock({
                matching: blockIds,
                maxDistance: 24,
                useExtraInfo: (block) => {
                    const key = `${block.position.x},${block.position.y},${block.position.z}`;
                    if (attemptedPositions.has(key)) return false;
                    if (block.position.x === botFloor.x && block.position.z === botFloor.z && block.position.y <= botFloor.y) {
                        return false;
                    }
                    if (Math.abs(block.position.y - currentY) > 3) return false;
                    return true;
                }
            });
        }

        if (!targetBlock) {
            if (mined === 0) {
                bot.chat(`ไม่พบ${label}ในระยะ 32 บล็อกครับเจ้านาย`);
                return `No ${label} found`;
            }
            break;
        }

        const p = targetBlock.position;
        attemptedPositions.add(`${p.x},${p.y},${p.z}`);

        try {
            await bot.pathfinder.goto(new goals.GoalNear(p.x, p.y, p.z, 2.5));

            const tool = bot.inventory.items().find(it => it.name.includes(toolKeyword));
            if (tool) {
                try { await bot.equip(tool, 'hand'); } catch (e) {}
            }

            await bot.lookAt(targetBlock.position.offset(0.5, 0.5, 0.5));
            await bot.dig(targetBlock);
            mined++;
            console.log(`[JARVIS] Mined ${label} ${mined}/${targetCount} at ${p}`);

            // Active dropped item entity pickup
            try {
                const dropItem = bot.nearestEntity(e => {
                    return e && e.name === 'item' && e.position && e.position.distanceTo(p) < 4.0;
                });
                if (dropItem) {
                    await bot.pathfinder.goto(new goals.GoalNear(dropItem.position.x, dropItem.position.y, dropItem.position.z, 0.5));
                } else {
                    await bot.pathfinder.goto(new goals.GoalNear(p.x, p.y, p.z, 0.8));
                }
            } catch (pickupErr) {}
            await new Promise(r => setTimeout(r, 200));
        } catch (err) {
            console.error(`[JARVIS] Mine ${label} error at ${p}:`, err.message);
            await new Promise(r => setTimeout(r, 300));
        }
    }

    if (mined > 0) {
        let deliveryFilter = 'stone';
        if (category === 'dirt' || text.includes('ดิน') || text.includes('ทราย')) deliveryFilter = 'dirt';
        else if (category === 'ore' || text.includes('แร่') || text.includes('ถ่าน') || text.includes('เหล็ก')) deliveryFilter = 'ore';
        else if (category === 'cactus' || text.includes('กระบองเพชร') || text.includes('cactus')) deliveryFilter = 'cactus';

        if (text.includes('กล่อง') || text.includes('หีบ') || text.includes('chest')) {
            const preferHome = text.includes('บ้าน') || text.includes('home');
            if (preferHome) {
                bot.chat(`${actionVerb}${label}ได้ทั้งหมด ${mined} ${unit}เรียบร้อยแล้วครับ! กำลังนำกลับไปเก็บเข้ากล่องที่บ้าน`);
            } else {
                bot.chat(`${actionVerb}${label}ได้ทั้งหมด ${mined} ${unit}เรียบร้อยแล้วครับ! กำลังนำไปเก็บเข้ากล่อง`);
            }
            setTimeout(() => {
                depositToNearestChest(deliveryFilter, preferHome);
            }, 1200);
        } else {
            bot.chat(`${actionVerb}${label}ได้ทั้งหมด ${mined} ${unit}เรียบร้อยแล้วครับ! กำลังนำไปส่งให้เจ้านาย`);
            setTimeout(() => {
                deliverItemsToBoss(deliveryFilter);
            }, 1200);
        }
    } else {
        bot.chat(`ไม่สามารถ${actionVerb}${label}ได้ครับ`);
    }

    return `Mined ${mined} ${label}`;
}

async function deliverAllItemsToBoss() {
    return deliverItemsToBoss('all');
}

function handleInventoryCheck() {
    const items = bot.inventory.items();
    if (items.length === 0) {
        bot.chat("กระเป๋าของผมยังว่างเปล่า ไม่มีไอเทมเลยครับเจ้านาย");
        return "Inventory empty";
    }

    const summary = items.map(i => `${i.displayName || i.name} x${i.count}`).join(', ');
    bot.chat(`ในกระเป๋ามี: ${summary}`);
    return summary;
}

async function handleEatFood() {
    const foodItem = bot.inventory.items().find(i => {
        const n = i.name.toLowerCase();
        return n.includes('bread') || n.includes('beef') || n.includes('pork') || 
               n.includes('mutton') || n.includes('chicken') || n.includes('apple') || 
               n.includes('carrot') || n.includes('potato');
    });

    if (!foodItem) {
        bot.chat("ผมไม่มีอาหารในกระเป๋าเลยครับเจ้านาย!");
        return "No food";
    }

    try {
        bot.chat(`กำลังรับประทาน ${foodItem.displayName || foodItem.name}...`);
        await bot.equip(foodItem, 'hand');
        await bot.consume();
        bot.chat(`อิ่มแล้วครับ! ระดับความหิว: ${bot.food}/20, เลือด: ${bot.health}/20`);
        return "Ate food";
    } catch (err) {
        bot.chat(`กินอาหารไม่สำเร็จ: ${err.message}`);
        return `Eat error: ${err.message}`;
    }
}

async function handlePlaceTorch() {
    const torchItem = bot.inventory.items().find(it => it.name.includes('torch'));
    if (!torchItem) {
        bot.chat("ผมไม่มีคบเพลิง (Torch) ในตัวครับเจ้านาย! (สั่ง 'คราฟคบเพลิง' ก่อนได้นะครับ)");
        return "No torch";
    }

    const groundBlock = bot.findBlock({
        matching: b => b && b.boundingBox === 'block',
        maxDistance: 3
    });

    if (!groundBlock) {
        bot.chat("ไม่พอบล็อกพื้นที่จะปักคบเพลิงครับ");
        return "No surface for torch";
    }

    try {
        await bot.equip(torchItem, 'hand');
        await bot.placeBlock(groundBlock, { x: 0, y: 1, z: 0 });
        bot.chat("ปักคบเพลิงส่องสว่างเรียบร้อยครับ!");
        return "Placed torch";
    } catch (err) {
        bot.chat(`ปักคบเพลิงไม่สำเร็จ: ${err.message}`);
        return `Torch error: ${err.message}`;
    }
}

async function handleSmeltItems(text = '') {
    if (!mcData) mcData = require('minecraft-data')(bot.version);

    const furnaceIds = ['furnace', 'lit_furnace', 'blast_furnace', 'smoker']
        .map(n => mcData.blocksByName[n]?.id)
        .filter(Boolean);

    const furnaceBlock = bot.findBlock({
        matching: furnaceIds,
        maxDistance: 16
    });

    if (!furnaceBlock) {
        bot.chat("ไม่พบเตาเผาในระยะ 16 บล็อกครับเจ้านาย วางเตาเผาให้ผมด้วยนะครับ!");
        return "No furnace found";
    }

    const inputItem = bot.inventory.items().find(i => {
        const n = i.name.toLowerCase();
        return n.includes('raw_') || n.includes('beef') || n.includes('pork') || 
               n.includes('mutton') || n.includes('chicken') || n === 'cobblestone' || n === 'sand';
    });

    if (!inputItem) {
        bot.chat("ผมไม่มีแร่ดิบหรือเนื้อดิบที่จะนำไปเผาครับเจ้านาย");
        return "No smeltable item";
    }

    const fuelItem = bot.inventory.items().find(i => {
        const n = i.name.toLowerCase();
        return n.includes('coal') || n.includes('charcoal') || n.includes('_log') || 
               n.includes('_planks') || n === 'stick';
    });

    if (!fuelItem) {
        bot.chat("ผมไม่มีเชื้อเพลิง (ถ่าน/ไม้) สำหรับจุดเตาเผาครับเจ้านาย");
        return "No fuel";
    }

    bot.chat(`กำลังเดินไปจุดเตาเผาเพื่อเผา ${inputItem.displayName || inputItem.name}...`);
    try {
        await bot.pathfinder.goto(new goals.GoalNear(furnaceBlock.position.x, furnaceBlock.position.y, furnaceBlock.position.z, 2.5));
        const furnace = await bot.openFurnace(furnaceBlock);

        await furnace.putFuel(fuelItem.type, null, Math.min(fuelItem.count, 16));
        await new Promise(r => setTimeout(r, 200));

        await furnace.putInput(inputItem.type, null, Math.min(inputItem.count, 32));
        await new Promise(r => setTimeout(r, 200));

        furnace.close();
        bot.chat(`ใส่ ${inputItem.displayName || inputItem.name} และเชื้อเพลิงเข้าเตาเผาเรียบร้อยแล้วครับ!`);
        return `Smelting ${inputItem.name}`;
    } catch (err) {
        bot.chat(`เกิดข้อผิดพลาดในการใช้เตาเผา: ${err.message}`);
        return `Smelt error: ${err.message}`;
    }
}

function handleStatusReport() {
    const hp = Math.round(bot.health);
    const food = Math.round(bot.food);
    const pos = bot.entity ? `X:${Math.round(bot.entity.position.x)} Y:${Math.round(bot.entity.position.y)} Z:${Math.round(bot.entity.position.z)}` : 'Unknown';
    bot.chat(`รายงานสถานะ: เลือด ${hp}/20 | ความหิว ${food}/20 | พิกัด ${pos} | โหมด ${bot.game.gameMode}`);
    return `HP: ${hp}, Food: ${food}`;
}

async function handleSneak() {
    bot.chat("สวัสดีครับเจ้านาย!");
    for (let i = 0; i < 3; i++) {
        bot.setControlState('sneak', true);
        await new Promise(r => setTimeout(r, 200));
        bot.setControlState('sneak', false);
        await new Promise(r => setTimeout(r, 200));
    }
    return "Sneaked";
}

async function handleSpin() {
    bot.chat("หมุนตัว 360 องศาตรวจรอบทิศ!");
    for (let deg = 0; deg <= 360; deg += 45) {
        const rad = (deg * Math.PI) / 180;
        bot.look(rad, 0, true);
        await new Promise(r => setTimeout(r, 80));
    }
    return "Spun";
}

function handleLookAtBoss() {
    const boss = getBoss();
    if (boss && boss.entity) {
        bot.lookAt(boss.entity.position.offset(0, 1.6, 0), true);
        bot.chat("มองเจ้านายอยู่ครับ มีอะไรให้รับใช้ไหมครับ?");
        return "Looked at boss";
    }
    bot.chat("ยังมองไม่เห็นเจ้านายครับ");
    return "Boss not visible";
}

async function handleEquipItem(keyword) {
    const item = bot.inventory.items().find(it => it.name.toLowerCase().includes(keyword));
    if (item) {
        try {
            await bot.equip(item, 'hand');
            bot.chat(`ถือ ${item.displayName || item.name} ในมือเรียบร้อยครับ!`);
            return `Equipped ${item.name}`;
        } catch (e) {
            bot.chat(`ไม่สามารถถือได้: ${e.message}`);
            return `Equip error: ${e.message}`;
        }
    } else {
        bot.chat(`ไม่พบไอเทม ${keyword} ในกระเป๋าครับเจ้านาย`);
        return "Item not found";
    }
}

async function handleEquipArmor(silent = false) {
    const items = bot.inventory.items();
    let equippedCount = 0;
    for (const it of items) {
        const n = it.name.toLowerCase();
        try {
            if (n.includes('helmet') || n.includes('cap')) {
                await bot.equip(it, 'head');
                equippedCount++;
            } else if (n.includes('chestplate') || n.includes('tunic')) {
                await bot.equip(it, 'torso');
                equippedCount++;
            } else if (n.includes('leggings') || n.includes('pants')) {
                await bot.equip(it, 'legs');
                equippedCount++;
            } else if (n.includes('boots')) {
                await bot.equip(it, 'feet');
                equippedCount++;
            }
        } catch (e) {}
    }
    if (equippedCount > 0) {
        bot.chat(`สวมใส่ชุดเกราะเรียบร้อยแล้วครับ (${equippedCount} ชิ้น) Arc Reactor พร้อมรบ!`);
    } else if (!silent) {
        bot.chat("ไม่มีชุดเกราะในกระเป๋าเลยครับเจ้านาย");
    }
    return `Equipped ${equippedCount} armor pieces`;
}

async function handleDance() {
    bot.chat("Iron Man Protocol: Victory Dance!");
    for (let i = 0; i < 4; i++) {
        bot.setControlState('jump', true);
        bot.setControlState('sneak', true);
        await new Promise(r => setTimeout(r, 200));
        bot.setControlState('jump', false);
        bot.setControlState('sneak', false);
        bot.look(bot.entity.yaw + 1.5, 0, true);
        await new Promise(r => setTimeout(r, 200));
    }
    bot.chat("โชว์ลีลาเสร็จสิ้นครับเจ้านาย!");
    return "Danced";
}

function handleWhereAmI() {
    const pos = bot.entity.position;
    const x = Math.round(pos.x);
    const y = Math.round(pos.y);
    const z = Math.round(pos.z);
    const dim = bot.game.dimension || 'Overworld';
    bot.chat(`พิกัดปัจจุบัน: X: ${x}, Y: ${y}, Z: ${z} (${dim}) ครับเจ้านาย`);
    return `Coords: ${x}, ${y}, ${z}`;
}

function resolveCraftTarget(keyword) {
    const kw = keyword.toLowerCase().trim();

    // 1. Storage & Utilities
    if (kw.includes('หีบ') || kw.includes('กล่อง') || kw.includes('chest')) return 'chest';
    if (kw.includes('บาร์เรล') || kw.includes('ถังไม้') || kw.includes('barrel')) return 'barrel';
    if (kw.includes('โต๊ะคราฟ') || kw.includes('crafting_table') || kw.includes('crafting table')) return 'crafting_table';
    if (kw.includes('เตาเผา') || kw.includes('เตาอบ') || kw.includes('เตา') || kw.includes('furnace')) return 'furnace';
    if (kw.includes('คบเพลิง') || kw.includes('ทอร์ช') || kw.includes('ไฟ') || kw.includes('torch')) return 'torch';
    if (kw.includes('ถังน้ำ') || kw.includes('ถังเหล็ก') || kw.includes('bucket')) return 'bucket';
    if (kw.includes('เตียง') || kw.includes('bed')) return 'white_bed';
    if (kw.includes('กรรไกร') || kw.includes('shears')) return 'shears';
    if (kw.includes('โล่') || kw.includes('shield')) return 'shield';
    if (kw.includes('เบ็ด') || kw.includes('fishing_rod')) return 'fishing_rod';
    if (kw.includes('ชาม') || kw.includes('bowl')) return 'bowl';
    if (kw.includes('บันไดลิง') || kw.includes('ladder')) return 'ladder';

    // 2. Wood & Construction
    if (kw.includes('แท่งไม้') || kw.includes('ไม้แท่ง') || kw.includes('เเห่งไม้') || 
        kw.includes('แห่งไม้') || kw.includes('กิ่งไม้') || kw.includes('สติ๊ก') || kw.includes('stick')) return 'stick';
    if (kw.includes('ประตูรั้ว') || kw.includes('fence_gate')) return 'oak_fence_gate';
    if (kw.includes('รั้ว') || kw.includes('fence')) return 'oak_fence';
    if (kw.includes('ประตูกล') || kw.includes('trapdoor')) return 'oak_trapdoor';
    if (kw.includes('ประตู') || kw.includes('door')) return 'oak_door';
    if (kw.includes('เรือ') || kw.includes('boat')) return 'oak_boat';
    if (kw.includes('ป้าย') || kw.includes('sign')) return 'oak_sign';
    if (kw.includes('ไม้แปรรูป') || kw.includes('ไม้โอ๊ค') || kw.includes('plank')) return 'oak_planks';

    // 3. Weapons & Tools (With Material Hierarchy)
    const hasDiamond = bot.inventory.items().some(i => i.name === 'diamond');
    const hasIron = bot.inventory.items().some(i => i.name === 'iron_ingot');
    const hasCobble = bot.inventory.items().some(i => i.name === 'cobblestone' || i.name === 'stone');

    // Pickaxe
    if (kw.includes('ที่ขุดเพชร') || kw.includes('diamond_pickaxe')) return 'diamond_pickaxe';
    if (kw.includes('ที่ขุดเหล็ก') || kw.includes('iron_pickaxe')) return 'iron_pickaxe';
    if (kw.includes('ที่ขุดหิน') || kw.includes('stone_pickaxe')) return 'stone_pickaxe';
    if (kw.includes('ที่ขุดไม้') || kw.includes('wooden_pickaxe')) return 'wooden_pickaxe';
    if (kw.includes('ที่ขุด') || kw.includes('อีเต๋อ') || kw.includes('pickaxe')) {
        if (hasDiamond) return 'diamond_pickaxe';
        if (hasIron) return 'iron_pickaxe';
        if (hasCobble) return 'stone_pickaxe';
        return 'wooden_pickaxe';
    }

    // Axe
    if (kw.includes('ขวานเพชร') || kw.includes('diamond_axe')) return 'diamond_axe';
    if (kw.includes('ขวานเหล็ก') || kw.includes('iron_axe')) return 'iron_axe';
    if (kw.includes('ขวานหิน') || kw.includes('stone_axe')) return 'stone_axe';
    if (kw.includes('ขวานไม้') || kw.includes('wooden_axe')) return 'wooden_axe';
    if (kw.includes('ขวาน') || kw.includes('axe')) {
        if (hasDiamond) return 'diamond_axe';
        if (hasIron) return 'iron_axe';
        if (hasCobble) return 'stone_axe';
        return 'wooden_axe';
    }

    // Sword
    if (kw.includes('ดาบเพชร') || kw.includes('diamond_sword')) return 'diamond_sword';
    if (kw.includes('ดาบเหล็ก') || kw.includes('iron_sword')) return 'iron_sword';
    if (kw.includes('ดาบหิน') || kw.includes('stone_sword')) return 'stone_sword';
    if (kw.includes('ดาบไม้') || kw.includes('wooden_sword')) return 'wooden_sword';
    if (kw.includes('ดาบ') || kw.includes('sword')) {
        if (hasDiamond) return 'diamond_sword';
        if (hasIron) return 'iron_sword';
        if (hasCobble) return 'stone_sword';
        return 'wooden_sword';
    }

    // Shovel
    if (kw.includes('พลั่ว') || kw.includes('shovel')) {
        if (hasIron) return 'iron_shovel';
        if (hasCobble) return 'stone_shovel';
        return 'wooden_shovel';
    }

    // Bow & Arrow
    if (kw.includes('ลูกธนู') || kw.includes('arrow')) return 'arrow';
    if (kw.includes('ธนู') || kw.includes('bow')) return 'bow';

    // 4. Armor
    if (kw.includes('หมวกเหล็ก') || kw.includes('iron_helmet')) return 'iron_helmet';
    if (kw.includes('เสื้อเกราะเหล็ก') || kw.includes('เกราะเหล็ก') || kw.includes('iron_chestplate')) return 'iron_chestplate';
    if (kw.includes('กางเกงเหล็ก') || kw.includes('iron_leggings')) return 'iron_leggings';
    if (kw.includes('รองเท้าเหล็ก') || kw.includes('iron_boots')) return 'iron_boots';

    // 5. Food
    if (kw.includes('ขนมปัง') || kw.includes('bread')) return 'bread';

    // 6. Direct English fallback (e.g. "craft torch", "craft furnace")
    if (mcData && mcData.itemsByName) {
        for (const item of Object.keys(mcData.itemsByName)) {
            if (kw.includes(item)) return item;
        }
    }

    return null;
}

async function ensurePlanks(neededPlanks = 4) {
    if (!mcData) mcData = require('minecraft-data')(bot.version);
    const getPlankCount = () => bot.inventory.items()
        .filter(i => i.name.endsWith('_planks') || i.name === 'planks')
        .reduce((sum, i) => sum + i.count, 0);

    let current = getPlankCount();
    if (current >= neededPlanks) return current;

    const logItems = bot.inventory.items().filter(i => 
        i.name.endsWith('_log') || i.name.endsWith('_wood') || i.name.endsWith('_stem')
    );

    for (const log of logItems) {
        if (getPlankCount() >= neededPlanks) break;
        let plankName = log.name.replace('_log', '_planks').replace('_wood', '_planks').replace('_stem', '_planks');
        let plankData = mcData.itemsByName[plankName] || mcData.itemsByName['oak_planks'];
        if (!plankData) continue;

        const recipes = bot.recipesFor(plankData.id, null, 1, null);
        if (recipes && recipes.length > 0) {
            const neededLogs = Math.ceil((neededPlanks - getPlankCount()) / 4);
            const craftCount = Math.min(neededLogs, log.count);
            try {
                await bot.craft(recipes[0], craftCount, null);
                await new Promise(r => setTimeout(r, 200));
            } catch (err) {
                console.error('[JARVIS] Craft planks step error:', err.message);
            }
        }
    }
    return getPlankCount();
}

async function ensureSticks(neededSticks = 4) {
    if (!mcData) mcData = require('minecraft-data')(bot.version);
    const getStickCount = () => bot.inventory.items()
        .filter(i => i.name === 'stick')
        .reduce((sum, i) => sum + i.count, 0);

    let current = getStickCount();
    if (current >= neededSticks) return current;

    const neededPlanks = Math.ceil((neededSticks - current) / 4) * 2;
    await ensurePlanks(neededPlanks);

    const stickData = mcData.itemsByName['stick'];
    if (!stickData) return current;

    const recipes = bot.recipesFor(stickData.id, null, 1, null);
    if (recipes && recipes.length > 0) {
        const craftTimes = Math.ceil((neededSticks - getStickCount()) / 4);
        try {
            await bot.craft(recipes[0], craftTimes, null);
            await new Promise(r => setTimeout(r, 200));
        } catch (err) {
            console.error('[JARVIS] Craft stick step error:', err.message);
        }
    }
    return getStickCount();
}

async function ensureCraftingTableBlock() {
    if (!mcData) mcData = require('minecraft-data')(bot.version);
    const tableId = mcData.blocksByName.crafting_table?.id;
    if (!tableId) return null;

    // 1. Check if table already placed nearby (within 16 blocks)
    let tableBlock = bot.findBlock({ matching: tableId, maxDistance: 16 });
    if (tableBlock) {
        const dist = bot.entity.position.distanceTo(tableBlock.position);
        if (dist > 3) {
            try {
                await bot.pathfinder.goto(new goals.GoalNear(tableBlock.position.x, tableBlock.position.y, tableBlock.position.z, 2.5));
            } catch (e) {}
        }
        return tableBlock;
    }

    // 2. Check table in inventory
    let tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');

    // 3. Craft table from planks if needed
    if (!tableItem) {
        await ensurePlanks(4);
        const tableItemData = mcData.itemsByName['crafting_table'];
        if (tableItemData) {
            const recipes = bot.recipesFor(tableItemData.id, null, 1, null);
            if (recipes && recipes.length > 0) {
                try {
                    await bot.craft(recipes[0], 1, null);
                    await new Promise(r => setTimeout(r, 200));
                    tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
                } catch (err) {
                    console.error('[JARVIS] Craft table error:', err.message);
                }
            }
        }
    }

    // 4. Place table on ground
    if (tableItem) {
        const groundBlock = bot.findBlock({
            matching: b => b && b.boundingBox === 'block' && bot.blockAt(b.position.offset(0, 1, 0))?.name === 'air',
            maxDistance: 3
        });
        if (groundBlock) {
            try {
                bot.chat("กำลังวางโต๊ะคราฟสำหรับสร้างไอเทมครับ...");
                await bot.equip(tableItem, 'hand');
                await bot.placeBlock(groundBlock, { x: 0, y: 1, z: 0 });
                await new Promise(r => setTimeout(r, 300));
                tableBlock = bot.findBlock({ matching: tableId, maxDistance: 6 });
                return tableBlock;
            } catch (err) {
                console.error('[JARVIS] Place table error:', err.message);
            }
        }
    }

    return null;
}

async function handleCraftItem(keyword, text = '') {
    if (!mcData) mcData = require('minecraft-data')(bot.version);

    let count = 1;
    const matchNum = text.match(/\d+/);
    if (matchNum) {
        count = Math.min(parseInt(matchNum[0]), 64);
    }

    const targetItemName = resolveCraftTarget(keyword || text);
    if (!targetItemName) {
        bot.chat(`ผมไม่รู้จักไอเทมที่สั่งให้คราฟครับ ลองสั่งเป็นชื่อไอเทม เช่น คราฟกล่อง, คราฟเตาเผา, คราฟคบเพลิง, คราฟที่ขุด, คราฟดาบ, คราฟไม้โอ๊ค ฯลฯ`);
        return "Unknown item to craft";
    }

    const itemData = mcData.itemsByName[targetItemName];
    if (!itemData) {
        bot.chat(`ไม่พบข้อมูลสูตรคราฟของ ${targetItemName} ในระบบครับ`);
        return "Unknown item to craft";
    }

    // 1. Auto-synthesize prerequisites (Planks & Sticks from raw Logs)
    if (targetItemName === 'chest') {
        await ensurePlanks(8 * count);
    } else if (targetItemName === 'barrel') {
        await ensurePlanks(6 * count);
    } else if (targetItemName === 'crafting_table') {
        await ensurePlanks(4 * count);
    } else if (targetItemName === 'stick') {
        await ensurePlanks(Math.ceil(count / 4) * 2);
    } else if (targetItemName.includes('pickaxe') || targetItemName.includes('axe') || targetItemName.includes('shovel')) {
        await ensureSticks(2 * count);
        if (targetItemName.startsWith('wooden_')) {
            await ensurePlanks(3 * count);
        }
    } else if (targetItemName.includes('sword')) {
        await ensureSticks(1 * count);
        if (targetItemName.startsWith('wooden_')) {
            await ensurePlanks(2 * count);
        }
    } else if (targetItemName === 'torch') {
        await ensureSticks(Math.ceil(count / 4));
    } else if (targetItemName === 'ladder') {
        await ensureSticks(7 * count);
    } else if (targetItemName.includes('door') || targetItemName.includes('trapdoor') || targetItemName.includes('boat')) {
        await ensurePlanks(6 * count);
    } else if (targetItemName.includes('fence_gate')) {
        await ensurePlanks(2 * count);
        await ensureSticks(4 * count);
    } else if (targetItemName.includes('fence')) {
        await ensurePlanks(4 * count);
        await ensureSticks(2 * count);
    } else if (targetItemName.includes('sign')) {
        await ensurePlanks(6 * count);
        await ensureSticks(1 * count);
    } else if (targetItemName === 'shield') {
        await ensurePlanks(6 * count);
    }

    // 2. Try 2x2 grid first
    let craftingTable = null;
    let recipes = bot.recipesFor(itemData.id, null, 1, null);

    // If no 2x2 recipe exists, ensure 3x3 Crafting Table block is placed & active
    if (!recipes || recipes.length === 0) {
        craftingTable = await ensureCraftingTableBlock();
        if (craftingTable) {
            recipes = bot.recipesFor(itemData.id, null, 1, craftingTable);
        }
    }

    // 3. If still no recipes, check nearby chest for missing ingredients
    if (!recipes || recipes.length === 0) {
        const chestIds = ['chest', 'trapped_chest', 'barrel'].map(n => mcData.blocksByName[n]?.id).filter(Boolean);
        const nearbyChest = bot.findBlock({ matching: chestIds, maxDistance: 16 });

        if (nearbyChest) {
            bot.chat(`วัตถุดิบในตัวไม่พอ กำลังไปค้นหาของจากในกล่องมาคราฟ ${itemData.displayName || targetItemName} ครับ...`);
            try {
                await bot.pathfinder.goto(new goals.GoalNear(nearbyChest.position.x, nearbyChest.position.y, nearbyChest.position.z, 2.5));
                const chest = await bot.openContainer(nearbyChest);
                const chestItems = chest.containerItems();

                for (const it of chestItems) {
                    try {
                        await chest.withdraw(it.type, null, Math.min(it.count, 64));
                        await new Promise(r => setTimeout(r, 120));
                    } catch (e) {}
                }
                chest.close();

                // Re-synthesize prerequisites after fetching items from chest
                if (targetItemName === 'chest') await ensurePlanks(8 * count);
                else if (targetItemName.includes('pickaxe') || targetItemName.includes('axe')) await ensureSticks(2 * count);

                if (!craftingTable) craftingTable = await ensureCraftingTableBlock();
                recipes = bot.recipesFor(itemData.id, null, 1, craftingTable);
            } catch (err) {
                console.error('[JARVIS] Fetch from chest error:', err);
            }
        }
    }

    if (!recipes || recipes.length === 0) {
        bot.chat(`วัตถุดิบในกระเป๋าและในกล่องไม่พอสำหรับคราฟ ${itemData.displayName || targetItemName} ครับเจ้านาย`);
        return "Insufficient materials";
    }

    const recipe = recipes[0];
    try {
        bot.chat(`กำลังคราฟ ${itemData.displayName || targetItemName} จำนวน ${count} ชิ้น...`);
        if (recipe.requiresTable && !craftingTable) {
            craftingTable = await ensureCraftingTableBlock();
        }

        await bot.craft(recipe, count, craftingTable || null);

        const shouldDeliver = text.includes('ให้ผม') || text.includes('ให้ฉัน') || 
                              text.includes('มาให้') || text.includes('โยนมา') || 
                              text.includes('ส่งมา') || text.includes('ทิ้งมา') || 
                              text.includes('ให้หน่อย') || text.includes('ขอ');

        if (shouldDeliver) {
            bot.chat(`คราฟ ${itemData.displayName || targetItemName} สำเร็จแล้วครับ! กำลังนำไปส่งให้เจ้านาย`);
            setTimeout(() => {
                deliverItemsToBoss(`crafted:${targetItemName}`);
            }, 800);
        } else {
            bot.chat(`คราฟ ${itemData.displayName || targetItemName} เรียบร้อยแล้วครับ! เก็บไว้ในกระเป๋าพร้อมใช้งาน`);
            // If it's a tool or weapon, hold it ready in hand!
            if (targetItemName.includes('pickaxe') || targetItemName.includes('axe') || 
                targetItemName.includes('sword') || targetItemName.includes('shovel')) {
                const tool = bot.inventory.items().find(i => i.name === targetItemName);
                if (tool) {
                    try { await bot.equip(tool, 'hand'); } catch (e) {}
                }
            } else if (targetItemName.includes('helmet') || targetItemName.includes('chestplate') || 
                       targetItemName.includes('leggings') || targetItemName.includes('boots')) {
                handleEquipArmor(true).catch(() => {});
            }
        }
        return `Crafted ${count} ${targetItemName}`;
    } catch (err) {
        bot.chat(`คราฟไม่สำเร็จ: ${err.message}`);
        return `Craft error: ${err.message}`;
    }
}

function handleHelp() {
    bot.chat("=== รายการคำสั่ง JARVIS ===");
    bot.chat("1. เคลื่อนที่: วาปมา / วาปกลับบ้าน / เซฟบ้าน / ตามมา / หยุด / โดด / ย่อ / หมุนตัว");
    bot.chat("2. เก็บเกี่ยว: ตัดไม้ [จำนวน] / ขุดหิน [จำนวน] / ขุดหิน 20 อันใส่กล่องที่บ้าน / หาแร่");
    bot.chat("3. สิ่งของ: ขอเตียง / ขอไม้ / ขอหิน / ขออาหาร / ทิ้งของมา / ของในตัว");
    bot.chat("4. คราฟของ: คราฟกล่อง [จำนวน] / คราฟไม้โอ๊ค / คราฟเตาเผา / คราฟที่ขุด");
    bot.chat("5. กล่อง & บ้าน: เก็บของในกล่อง / เอาหินใส่กล่องที่บ้าน / วาปกลับบ้าน / เซฟบ้าน");
    bot.chat("6. สู้ & สุขภาพ: คุ้มกัน / ถอย / นอน / ตื่น / กินข้าว / สวมเกราะ / ถือดาบ");
    bot.chat("7. ข้อมูล: พิกัด / พิกัดบ้าน / สถานะ");
    return "Help displayed";
}

function handleActionCommand(action, text = '') {
    const act = (action || '').toLowerCase().trim();
    const t = (text || '').toLowerCase().trim();

    // 0. Home Base & Location Management (CRITICAL: Checked before general 'tp' so 'วาปกลับบ้าน' teleports to home!)
    const isHomeSave = t.includes('เซฟบ้าน') || t.includes('บันทึกบ้าน') || t.includes('จำบ้าน') || 
                       t.includes('sethome') || t.includes('set home') || t.includes('save home') ||
                       (t.includes('ตั้ง') && t.includes('บ้าน')) || act === 'set_home';
    if (isHomeSave) {
        return handleSetHome(text);
    }

    const isHomeCoords = t.includes('พิกัดบ้าน') || t.includes('บ้านอยู่ที่ไหน') || t.includes('บ้านอยู่ไหน') ||
                         t.includes('ดูบ้าน') || t.includes('home coords') || t.includes('where is home') ||
                         t.includes('จุดเซฟบ้าน') || act === 'home_coords';
    if (isHomeCoords) {
        return handleReportHome();
    }

    const isTeleportHome = t.includes('วาปกลับบ้าน') || t.includes('วาร์ปกลับบ้าน') || 
                           t.includes('วาปไปบ้าน') || t.includes('วาร์ปไปบ้าน') ||
                           t.includes('กลับบ้าน') || t.includes('ไปบ้าน') ||
                           t.includes('tp home') || t.includes('warp home') || 
                           t.includes('teleport home') || t.includes('go home') ||
                           act === 'tp_home';
    if (isTeleportHome) {
        return handleTeleportHome();
    }

    // 1. Movement & Fast Recall / Teleport to Boss
    // If user says "วาปมา" / "วาร์ปมา" / "มาหาผม" / "มาหาฉัน" / "ขึ้นมา" / "tp" -> Teleport to Boss!
    if (act === 'tp' || t.includes('วาร์ปมา') || t.includes('วาปมา') || t.includes('ขึ้นมา') || 
        t.includes('มาหาผม') || t.includes('มาหาฉัน') || t.includes('มานี่') ||
        t.includes('teleport') || t.includes('tp') || t === 'วาป' || t === 'วาร์ป') {
        return handleRecallToBoss(true);
    }
    if (act === 'follow' || t.includes('ตามมา') || t.includes('come') || t.includes('follow') || 
        t.includes('เดินๆ') || t.includes('กลับมา')) {
        return handleRecallToBoss(false);
    }
    if (act === 'stop' || t.includes('หยุด') || t.includes('stop') || t.includes('wait') || t.includes('รอตรงนี้') || t.includes('รอ')) {
        return handleStop();
    }
    if (act === 'jump' || t.includes('โดด') || t.includes('jump')) {
        return handleJump();
    }
    if (act === 'sneak' || t.includes('ย่อ') || t.includes('หมอบ') || t.includes('sneak') || t.includes('crouch')) {
        return handleSneak();
    }
    if (act === 'spin' || t.includes('หมุนตัว') || t.includes('หมุน') || t.includes('spin')) {
        return handleSpin();
    }
    if (act === 'dance' || t.includes('เต้น') || t.includes('แดนซ์')) {
        return handleDance();
    }
    if (act === 'look' || t.includes('หันมา') || t.includes('มองฉัน') || t.includes('look')) {
        return handleLookAtBoss();
    }

    // 2. Equipment & Gear
    if (t.includes('สวมเกราะ') || t.includes('ใส่เกราะ') || t.includes('armor')) {
        return handleEquipArmor();
    }
    if (t.startsWith('ถือ ') || t.startsWith('ถือ')) {
        const itemKeyword = t.replace('ถือ', '').trim();
        if (itemKeyword) {
            let kw = itemKeyword;
            if (kw.includes('ดาบ')) kw = 'sword';
            else if (kw.includes('ขวาน')) kw = 'axe';
            else if (kw.includes('พลั่ว')) kw = 'shovel';
            else if (kw.includes('หิน')) kw = 'stone';
            else if (kw.includes('ไม้')) kw = 'log';
            else if (kw.includes('เตียง')) kw = 'bed';
            return handleEquipItem(kw);
        }
    }

    // 3. Inventory Inspection (CRITICAL: Checked before drop/give because "ของ" contains substring "ขอ")
    if (t.includes('เช็คของ') || t.includes('ของในตัว') || t.includes('กระเป๋า') || 
        t.includes('มีอะไรบ้าง') || t.includes('ดูของ') || t.includes('ขอดูของ') ||
        t.includes('inv') || t.includes('inventory')) {
        return handleInventoryCheck();
    }

    // 4. Chest & Containers (CRITICAL: Checked before Drop/Give so "เอาหินใส่กล่อง" deposits into chest!)
    const isChestDeposit = t.includes('ใส่กล่อง') || t.includes('ใส่หีบ') || 
                           t.includes('เข้ากล่อง') || t.includes('เข้าหีบ') ||
                           t.includes('เก็บของในกล่อง') || t.includes('ยัดของใส่กล่อง') ||
                           (t.includes('เก็บของ') && t.includes('บ้าน')) ||
                           (t.includes('เอาของ') && t.includes('บ้าน')) ||
                           (t.includes('เก็บ') && (t.includes('กล่อง') || t.includes('หีบ'))) ||
                           (t.includes('เอา') && t.includes('ใส่') && (t.includes('กล่อง') || t.includes('หีบ'))) ||
                           act === 'deposit';

    if (isChestDeposit) {
        let filter = 'all';
        if (t.includes('ไม้')) filter = 'wood';
        else if (t.includes('หิน') || t.includes('stone') || t.includes('cobble')) filter = 'stone';
        else if (t.includes('แร่') || t.includes('เหล็ก') || t.includes('ถ่าน')) filter = 'ore';
        else if (t.includes('กระบองเพชร') || t.includes('cactus')) filter = 'cactus';
        else if (t.includes('เตียง')) filter = 'bed';
        else if (t.includes('อาหาร') || t.includes('ข้าว')) filter = 'food';
        
        const preferHome = t.includes('บ้าน') || t.includes('home');
        return depositToNearestChest(filter, preferHome);
    }

    // 5. Crafting (CRITICAL: Checked before Drop/Give so "เอาไม้ในกล่องเเล้วคราฟ..." crafts!)
    if (t.includes('คราฟ') || t.includes('craft')) {
        return handleCraftItem(t, t);
    }

    // 6. Chest Withdraw (Checked when NOT depositing and NOT crafting)
    const isChestWithdraw = (t.includes('หยิบ') || t.includes('ค้น') || (t.includes('เอา') && !t.includes('ใส่'))) &&
                            (t.includes('จากกล่อง') || t.includes('ในกล่อง') || t.includes('จากหีบ') || t.includes('ในหีบ')) ||
                            act === 'withdraw';

    if (isChestWithdraw) {
        let kw = t.replace('หยิบของจากกล่อง', '').replace('เอาของจากกล่อง', '').replace('ค้นกล่อง', '')
                  .replace('หยิบ', '').replace('จากกล่อง', '').replace('ในกล่อง', '').replace('เอา', '').trim();
        return withdrawFromNearestChest(kw, 64);
    }

    // 7. Gathering & Mining
    if (act === 'chop_wood' || t.includes('ตัดไม้') || t.includes('ขุดไม้') || t.includes('chop') || t.includes('wood')) {
        return handleChopWood(text || action);
    }
    if (t.includes('ขุดหิน') || t.includes('stone') || t.includes('cobble')) {
        return handleMineBlocks('stone', text);
    }
    if (t.includes('ขุดดิน') || t.includes('ขุดทราย') || t.includes('dirt') || t.includes('sand')) {
        return handleMineBlocks('dirt', text);
    }
    if (t.includes('หาแร่') || t.includes('ขุดแร่') || t.includes('ขุดถ่าน') || t.includes('ขุดเหล็ก') || t.includes('ore') || t.includes('iron') || t.includes('coal')) {
        return handleMineBlocks('ore', text);
    }
    if (t.includes('กระบองเพชร') || t.includes('cactus')) {
        return handleMineBlocks('cactus', text);
    }

    // 8. Drop / Give / Request Items (CRITICAL: NEVER drop if command is about chests, crafting, or home base!)
    if (!t.includes('กล่อง') && !t.includes('หีบ') && !t.includes('คราฟ') && !t.includes('craft') && !t.includes('บ้าน')) {
        const hasRequestItem = t.includes('ขอเตียง') || t.includes('ขอไม้') || t.includes('ขอหิน') || 
                               t.includes('ขอแร่') || t.includes('ขออาหาร') || t.includes('ขอข้าว') || 
                               t.includes('ขอของ') || t.includes('ขออุปกรณ์') || t.includes('ขออาวุธ') ||
                               t.includes('ขอที่ขุด') || t.includes('ขอขวาน') ||
                               (t.includes('ขอ') && !t.includes('ของ'));

        const isDropOrGive = t.includes('ทิ้ง') || t.includes('โยน') || 
                             (t.includes('เอา') && (t.includes('มา') || t.includes('ให้') || t.includes('คืน'))) || 
                             (t.includes('ส่ง') && (t.includes('มา') || t.includes('ให้'))) || 
                             t.includes('ดรอป') || t.includes('เทของ') || hasRequestItem ||
                             t.includes('drop') || t.includes('give') || t.includes('toss');

        // Bed request vs Sleep
        if (t.includes('เตียง') || t.includes('bed')) {
            if (isDropOrGive && !t.includes('นอน') && !t.includes('sleep')) {
                return deliverItemsToBoss('bed');
            }
            if (t.includes('ทิ้งเตียง') || t.includes('ขอเตียง') || t.includes('เอาเตียง') || t.includes('ส่งเตียง')) {
                return deliverItemsToBoss('bed');
            }
            if (t.includes('นอน') || t.includes('sleep') || t.includes('พัก')) {
                return handleSleep();
            }
            return deliverItemsToBoss('bed');
        }

        // Wood drop/give
        if ((t.includes('ไม้') || t.includes('wood')) && (isDropOrGive || t.includes('ขอไม้') || t.includes('เอาไม้') || t.includes('ทิ้งไม้'))) {
            return deliverItemsToBoss('wood');
        }

        // Stone drop/give
        if ((t.includes('หิน') || t.includes('stone')) && (isDropOrGive || t.includes('ขอหิน') || t.includes('เอาหิน') || t.includes('ทิ้งหิน'))) {
            return deliverItemsToBoss('stone');
        }

        // Ore drop/give
        if ((t.includes('แร่') || t.includes('เหล็ก') || t.includes('ถ่าน') || t.includes('เพชร') || t.includes('ore')) && isDropOrGive) {
            return deliverItemsToBoss('ore');
        }

        // Food drop/give
        if ((t.includes('อาหาร') || t.includes('ข้าว') || t.includes('food')) && isDropOrGive) {
            return deliverItemsToBoss('food');
        }

        // Cactus drop/give
        if ((t.includes('กระบองเพชร') || t.includes('cactus')) && (isDropOrGive || t.includes('ขอกระบองเพชร') || t.includes('เอากระบองเพชร') || t.includes('ทิ้งกระบองเพชร'))) {
            return deliverItemsToBoss('cactus');
        }

        // Drop all items
        if ((isDropOrGive && (t.includes('ทั้งหมด') || t.includes('all'))) ||
            t.includes('ทิ้งของ') || t.includes('โยนของ') || t.includes('เอาของมา') || t.includes('ส่งของมา') || t.includes('ดรอปของ') || act === 'drop_items') {
            return deliverItemsToBoss('all');
        }
    }

    // 8. Torches & Furnace
    if (t.includes('ปักไฟ') || t.includes('ปักคบเพลิง') || t.includes('วางไฟ') || t.includes('torch')) {
        return handlePlaceTorch();
    }
    if (t.includes('เผาแร่') || t.includes('ย่างเนื้อ') || t.includes('เผาของ') || t.includes('จุดเตา') || t.includes('smelt')) {
        return handleSmeltItems(t);
    }

    // 9. Status & Coordinates
    if (t.includes('พิกัด') || t.includes('อยู่ที่ไหน') || t.includes('coords') || t.includes('where') || t.includes('ตำแหน่ง')) {
        return handleWhereAmI();
    }
    if (t.includes('สถานะ') || t.includes('status') || t.includes('hp') || t.includes('เลือด')) {
        return handleStatusReport();
    }

    // 6. Combat & Bodyguard
    if (act === 'guard' || t.includes('คุ้มกัน') || t.includes('ป้องกัน') || t.includes('guard') || t.includes('สู้')) {
        return handleGuard();
    }
    if (t.includes('ถอย') || t.includes('หนี') || t.includes('retreat')) {
        return handleFollow();
    }

    // 7. Survival & Health
    if (act === 'sleep' || t.includes('นอน') || t.includes('sleep') || t.includes('พักผ่อน') || t.includes('ราตรีสวัสดิ์')) {
        return handleSleep();
    }
    if (act === 'wake' || t.includes('ตื่น') || t.includes('wake') || t.includes('ลุก') || t.includes('อรุณสวัสดิ์')) {
        return handleWake();
    }
    if (t.includes('กินข้าว') || t.includes('กินอาหาร') || t.includes('กิน') || t.includes('eat') || t.includes('food')) {
        return handleEatFood();
    }

    // 8. Help
    if (t.includes('help') || t.includes('คำสั่ง') || t.includes('ช่วยด้วย') || t.includes('เมนู')) {
        return handleHelp();
    }

    bot.chat(`รับทราบคำสั่ง: ${text || action}`);
    return `Unknown action received: ${action || text}`;
}

// ---------------------------------------------------------------------------
// In-Game Chat Listener
// ---------------------------------------------------------------------------

bot.on('chat', (username, message) => {
    if (username === bot.username) return;
    console.log(`[CHAT] <${username}>: ${message}`);

    const targetPlayer = bot.players[username];
    if (targetPlayer && targetPlayer.entity) {
        bot.lookAt(targetPlayer.entity.position.offset(0, 1.6, 0));
    }

    handleActionCommand('', message);
});

bot.on('kicked', (reason) => {
    console.log(`[JARVIS] Kicked: ${reason}`);
});

bot.on('error', (err) => {
    console.error(`[JARVIS ERROR]`, err);
});

// ---------------------------------------------------------------------------
// Local HTTP REST Bridge (For J.A.R.V.I.S. Mainframe Voice Dispatcher)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Voyager Dynamic Skill Execution Engine
// ---------------------------------------------------------------------------

async function executeSkillCode(code, skillName = 'custom_skill', description = '') {
    console.log(`[VOYAGER] Executing skill '${skillName}'...`);
    bot.chat(`[Voyager] เริ่มประมวลผลสกิล '${skillName}'...`);

    const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;

    try {
        const fn = new AsyncFunction('bot', 'mcData', 'pathfinder', 'getBoss', 'deliverItems', code);
        const result = await fn(bot, mcData, { Movements, goals }, getBoss, deliverItemsToBoss);

        console.log(`[VOYAGER] Skill '${skillName}' executed successfully! Result:`, result);
        bot.chat(`[Voyager] สกิล '${skillName}' สำเร็จเรียบร้อยแล้วครับ!`);

        // Persist skill to Skill Library
        try {
            fs.mkdirSync(SKILLS_DIR, { recursive: true });
            const skillFile = path.join(SKILLS_DIR, `${skillName}.js`);
            fs.writeFileSync(skillFile, code, 'utf-8');

            let manifest = { skills: {} };
            if (fs.existsSync(MANIFEST_PATH)) {
                manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8') || '{"skills":{}}');
            }
            manifest.skills[skillName] = {
                name: skillName,
                description: description || 'Dynamically generated Voyager skill',
                created_at: new Date().toISOString()
            };
            fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2), 'utf-8');
            console.log(`[VOYAGER] Saved '${skillName}' to Skill Library.`);
        } catch (saveErr) {
            console.error('[VOYAGER] Failed to save skill manifest:', saveErr);
        }

        return { success: true, result: result || 'Executed successfully' };
    } catch (err) {
        console.error(`[VOYAGER ERROR] Skill '${skillName}' failed:`, err);
        bot.chat(`[Voyager Error] เกิดข้อผิดพลาด: ${err.message}`);
        return { success: false, error: err.message };
    }
}

const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');

    if (req.method === 'GET' && req.url === '/status') {
        const boss = getBoss();
        res.writeHead(200);
        return res.end(JSON.stringify({
            status: 'online',
            username: bot.username,
            health: bot.health,
            food: bot.food,
            position: bot.entity ? bot.entity.position : null,
            boss_visible: !!(boss && boss.entity),
            isGuarding: isGuarding
        }));
    }

    if (req.method === 'GET' && req.url === '/skills') {
        let manifest = { skills: {} };
        if (fs.existsSync(MANIFEST_PATH)) {
            manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8') || '{"skills":{}}');
        }
        res.writeHead(200);
        return res.end(JSON.stringify(manifest));
    }

    if (req.method === 'POST' && req.url === '/run_code') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body || '{}');
                const code = data.code || '';
                const name = data.name || 'skill_' + Date.now();
                const desc = data.description || '';
                const result = await executeSkillCode(code, name, desc);
                res.writeHead(result.success ? 200 : 500);
                res.end(JSON.stringify(result));
            } catch (err) {
                res.writeHead(400);
                res.end(JSON.stringify({ success: false, error: err.message }));
            }
        });
        return;
    }

    if (req.method === 'POST' && req.url === '/command') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body || '{}');
                const action = data.action || '';
                const text = data.text || '';
                const result = await handleActionCommand(action, text);
                res.writeHead(200);
                res.end(JSON.stringify({ success: true, result }));
            } catch (err) {
                res.writeHead(400);
                res.end(JSON.stringify({ success: false, error: err.message }));
            }
        });
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(HTTP_PORT, '127.0.0.1', () => {
    console.log(`[JARVIS BRIDGE] HTTP Bridge listening on http://127.0.0.1:${HTTP_PORT}`);
});
