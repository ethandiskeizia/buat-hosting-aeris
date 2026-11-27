/**
 * AERIS - Frontend Prototype Logic
 */

// 1. Mock Data Structure
const spaces = [
    { 
        id: 'lib2', name: 'Library — Floor 2', building: 'Library', floor: 2, match: 98, comfortScore: 98, 
        temperature: 23.1, humidity: 48, co2: 620, occupancy: 42, tablesAvailable: 14, 
        tags: ['Quiet', 'Fresh Air', 'Cool'], status: 'Optimal', statusLevel: 'optimal',
        walkTime: '3 min walk', baseValues: { temp: 23.1, hum: 48, co2: 620, occ: 42, tbl: 14 }
    },
    { 
        id: 'lounge', name: 'Student Lounge', building: 'Student Center', floor: 1, match: 91, comfortScore: 91, 
        temperature: 24.0, humidity: 50, co2: 680, occupancy: 58, tablesAvailable: 8, 
        tags: ['Casual', 'Power Outlets Nearby'], status: 'Optimal', statusLevel: 'optimal',
        walkTime: '5 min walk', baseValues: { temp: 24.0, hum: 50, co2: 680, occ: 58, tbl: 8 }
    },
    { 
        id: 'gedungD', name: 'Gedung D — Lounge', building: 'Gedung D', floor: 1, match: 52, comfortScore: 52, 
        temperature: 27.0, humidity: 74, co2: 1180, occupancy: 87, tablesAvailable: 2, 
        tags: ['Crowded', 'Stuffy', 'Warm'], status: 'Poor', statusLevel: 'poor',
        walkTime: '2 min walk', baseValues: { temp: 27.0, hum: 74, co2: 1180, occ: 87, tbl: 2 }
    },
    { 
        id: 'studyHall', name: 'Study Hall', building: 'Academic', floor: 3, match: 94, comfortScore: 94, 
        temperature: 22.8, humidity: 52, co2: 650, occupancy: 35, tablesAvailable: 18, 
        tags: ['Quiet', 'Cool'], status: 'Optimal', statusLevel: 'optimal',
        walkTime: '8 min walk', baseValues: { temp: 22.8, hum: 52, co2: 650, occ: 35, tbl: 18 }
    },
    { 
        id: 'corridor', name: 'Gedung B Corridor', building: 'Gedung B', floor: 1, match: 72, comfortScore: 72, 
        temperature: 25.1, humidity: 60, co2: 800, occupancy: 65, tablesAvailable: 4, 
        tags: ['Transit', 'Moderate'], status: 'Moderate', statusLevel: 'moderate',
        walkTime: '2 min walk', baseValues: { temp: 25.1, hum: 60, co2: 800, occ: 65, tbl: 4 }
    }
];

let reports = JSON.parse(localStorage.getItem('aeris_reports')) || [];

function saveReports() {
    localStorage.setItem('aeris_reports', JSON.stringify(reports));
    window.dispatchEvent(new Event('reports_updated'));
}

// Compact, cute gumdrop mascot matching the new reference
const mascotSVG = `
<svg width="100%" height="100%" viewBox="0 0 100 110" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 4px 12px rgba(120, 185, 232, 0.4)); animation: floatMascot 4s ease-in-out infinite;">
  <defs>
    <linearGradient id="mascotGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#E1F0FF" />
      <stop offset="45%" stop-color="#90C8FA" />
      <stop offset="100%" stop-color="#1472D4" />
    </linearGradient>
  </defs>
  <!-- Gumdrop body: wider round bottom, narrower round top -->
  <path d="M 25 50 C 25 15, 75 15, 75 50 C 95 90, 80 100, 50 100 C 20 100, 5 90, 25 50 Z" fill="url(#mascotGrad)" />
  <!-- Eyes -->
  <circle cx="36" cy="48" r="5" fill="#1A1C29" />
  <circle cx="64" cy="48" r="5" fill="#1A1C29" />
  <!-- Smile -->
  <path d="M 46 56 Q 50 63 54 56" fill="none" stroke="#1A1C29" stroke-width="2.5" stroke-linecap="round" />
  <!-- Blush -->
  <circle cx="26" cy="56" r="6" fill="#67B1EE" opacity="0.7"/>
  <circle cx="74" cy="56" r="6" fill="#67B1EE" opacity="0.7"/>
</svg>
<style>
@keyframes floatMascot {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-6px); }
    100% { transform: translateY(0px); }
}
</style>
`;

// 2. Routing & View Management
const appContainer = document.getElementById('app-container');
let currentView = 'home';
let currentAdminView = 'dashboard';
let charts = {};

function navigateTo(route, data = null) {
    currentView = route;
    
    // Update nav active states
    document.querySelectorAll('.mob-link').forEach(link => {
        link.classList.remove('active');
        if(link.getAttribute('data-route') === route) link.classList.add('active');
    });

    const mobileNav = document.getElementById('mobile-nav');
    const mainNav = document.getElementById('main-nav');
    const mainFooter = document.getElementById('main-footer');
    const fabEmergency = document.getElementById('fab-emergency');
    
    if (route === 'admin') {
        mobileNav.style.display = 'none';
        mainNav.style.display = 'none';
        mainFooter.style.display = 'none';
        if(fabEmergency) fabEmergency.style.display = 'none';
        document.body.style.paddingBottom = '0';
        document.body.style.backgroundColor = '#FFFFFF'; // Admin bg
    } else {
        if(window.innerWidth <= 600) {
            mobileNav.style.display = 'flex';
            if(fabEmergency) fabEmergency.style.display = 'block';
        }
        mainNav.style.display = 'block';
        mainFooter.style.display = 'block';
        document.body.style.paddingBottom = window.innerWidth <= 600 ? '80px' : '0';
        document.body.style.backgroundColor = 'var(--bg-color)';
    }

    const template = document.getElementById(`tpl-${route}`);
    if (template) {
        appContainer.innerHTML = template.innerHTML;
        
        if (route === 'home') renderHome();
        if (route === 'detail') renderDetail(data);
        if (route === 'myreports') renderMyReports();
        if (route === 'admin') initAdmin();
        window.scrollTo(0,0);
    }
}

// 3. User Views
function createSpaceCard(space) {
    let badgeClass = space.statusLevel === 'optimal' ? 'status-optimal' : (space.statusLevel === 'poor' ? 'status-poor' : 'status-moderate');
    return `
        <div class="space-card" onclick="navigateTo('detail', '${space.id}')">
            <div class="sc-thumb">
                <div class="cube-wireframe" style="width:40px; height:40px; animation:none; opacity:0.1; border-color:var(--text-main);"></div>
                <div class="status-badge ${badgeClass} sc-badge-img">IEQ ${space.comfortScore}%</div>
            </div>
            <div class="sc-content">
                <div class="sc-title">Zone: ${space.name}</div>
                <div class="sc-metrics">
                    <span id="val-co2-${space.id}">${space.co2} ppm</span> · 
                    <span id="val-temp-${space.id}">${space.temperature.toFixed(1)}°C</span> · 
                    <span id="val-occ-${space.id}">${space.occupancy}% full</span>
                </div>
                <div class="sc-tags">${space.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
            </div>
        </div>
    `;
}

function renderHome() {
    const topSpaces = [...spaces].sort((a,b) => b.match - a.match);
    document.getElementById('home-spaces').innerHTML = topSpaces.map(createSpaceCard).join('');
    
    // Inject Mascot
    document.getElementById('map-mascot').innerHTML = mascotSVG;
    document.getElementById('cta-mascot').innerHTML = mascotSVG;
    
    // Render default 2D map
    renderMap(2);
}

function toggleChip(btn) { btn.classList.toggle('selected'); }

// MAP LOGIC
function renderMap(floor = 2) {
    const dColor = floor === 1 ? 'var(--status-poor)' : 'var(--status-moderate)';
    
    // Check if zone has reports
    const gedungDReports = reports.filter(r => r.location.building === 'Gedung D' && r.status !== 'Resolved').length;
    let badgeHtml = '';
    if(gedungDReports > 0) {
        const hasCrit = reports.some(r => r.location.building === 'Gedung D' && r.priority === 'CRITICAL' && r.status !== 'Resolved');
        const rColor = hasCrit ? 'var(--status-poor)' : 'var(--status-high)';
        badgeHtml = `<circle cx="470" cy="210" r="14" fill="${rColor}" /><text x="470" y="214" fill="white" font-size="11" font-weight="bold" text-anchor="middle">${gedungDReports}</text>`;
    }

    const svg = `
    <svg width="100%" height="100%" viewBox="0 0 800 400" preserveAspectRatio="xMidYMid meet">
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E2E8F0" stroke-width="0.5"/></pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <g>
            <path class="zone-path" d="M 100 50 L 300 50 L 300 200 L 200 200 L 200 250 L 100 250 Z" fill="var(--status-optimal)" fill-opacity="0.9" onclick="showMapPopover('lib2', event)" />
            <text x="150" y="100" fill="white" font-weight="bold" font-size="14">Library</text>
            
            <path class="zone-path" d="M 320 50 L 600 50 L 600 150 L 320 150 Z" fill="var(--status-moderate)" fill-opacity="0.9" onclick="showMapPopover('lounge', event)"/>
            <text x="400" y="90" fill="white" font-weight="bold" font-size="14">Lounge</text>
            
            <path class="zone-path" d="M 320 170 L 500 170 L 500 350 L 650 350 L 650 380 L 320 380 Z" fill="${dColor}" fill-opacity="0.9" onclick="showMapPopover('gedungD', event)"/>
            <text x="360" y="250" fill="white" font-weight="bold" font-size="14">Zone D</text>
            ${badgeHtml}
        </g>
    </svg>`;
    document.getElementById('map-2d-view').innerHTML = svg;
}

function switchFloor(f) {
    document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    renderMap(f);
}

function switchMapMode(mode) {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(mode === '2D' ? 'mode-2d' : 'mode-3d').classList.add('active');
    
    if(mode === '2D') {
        document.getElementById('map-2d-view').classList.remove('hidden');
        document.getElementById('map-3d-view').classList.add('hidden');
    } else {
        document.getElementById('map-2d-view').classList.add('hidden');
        document.getElementById('map-3d-view').classList.remove('hidden');
    }
}

function showMapPopover(spaceId, event) {
    const popover = document.getElementById('map-popover');
    const space = spaces.find(s => s.id === spaceId);
    if(!space) return;

    let badgeClass = space.statusLevel === 'optimal' ? 'status-optimal' : (space.statusLevel === 'poor' ? 'status-poor' : 'status-moderate');
    
    popover.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 8px;">${space.name}</div>
        <div class="status-badge ${badgeClass}" style="display:inline-block; margin-bottom: 12px;">IEQ ${space.comfortScore}%</div>
        <div style="font-size: 0.875rem; margin-bottom: 4px;">🌡️ ${space.temperature.toFixed(1)}°C &nbsp; 💧 ${space.humidity}%</div>
        <div style="font-size: 0.875rem; margin-bottom: 12px;">🌬️ ${space.co2} ppm &nbsp; 👥 ${space.occupancy}%</div>
        <button class="btn btn-primary full-width btn-sm" style="margin-bottom:8px;" onclick="navigateTo('detail', '${space.id}')">View Space</button>
        <button class="btn btn-outline full-width btn-sm" onclick="openReportModalFromMap('${space.building}', ${space.floor})">Report Issue Here</button>
    `;

    let x = event.clientX; let y = event.clientY - 200;
    if(y < 50) y = event.clientY + 20;
    
    popover.style.left = `${x}px`;
    popover.style.top = `${y}px`;
    popover.classList.remove('hidden');

    setTimeout(() => {
        const closePopover = (e) => {
            if(!popover.contains(e.target)) {
                popover.classList.add('hidden');
                document.removeEventListener('click', closePopover);
            }
        };
        document.addEventListener('click', closePopover);
    }, 10);
}

function renderDetail(spaceId) {
    const space = spaces.find(s => s.id === spaceId);
    if(!space) return navigateTo('home');
    let badgeClass = space.statusLevel === 'optimal' ? 'status-optimal' : (space.statusLevel === 'poor' ? 'status-poor' : 'status-moderate');

    document.getElementById('detail-header').innerHTML = `
        <div class="flex-between"><h2>${space.name}</h2><div class="status-badge ${badgeClass}">${space.status}</div></div>
        <div class="score-display">
            <span class="score-num ${space.statusLevel}-text" id="det-score">${space.comfortScore}%</span>
            <span style="color: var(--text-muted); font-weight: 500;">Comfort Score</span>
        </div>
    `;

    document.getElementById('detail-metrics').innerHTML = `
        <div class="metric-card"><div class="m-icon">🌡️</div><div class="m-val" id="det-temp">${space.temperature.toFixed(1)}°C</div><div class="m-lbl">Temp</div></div>
        <div class="metric-card"><div class="m-icon">💧</div><div class="m-val" id="det-hum">${space.humidity}%</div><div class="m-lbl">Humidity</div></div>
        <div class="metric-card"><div class="m-icon">🌬️</div><div class="m-val" id="det-co2">${space.co2}</div><div class="m-lbl">CO₂ ppm</div></div>
        <div class="metric-card"><div class="m-icon">👥</div><div class="m-val" id="det-occ">${space.occupancy}%</div><div class="m-lbl">Occupancy</div></div>
    `;

    document.getElementById('detail-tags').innerHTML = space.tags.map(t => `<span class="tag">${t}</span>`).join('');
    document.getElementById('detail-tables').innerHTML = `<strong><span id="det-tbl">${space.tablesAvailable}</span> tables available</strong> • ${space.walkTime}`;

    renderDetailChart(space);
    document.getElementById('pulse-modal').dataset.spaceId = spaceId;
}

// 4. Modals & Forms Logic
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// Pulse
function openPulse() { openModal('pulse-modal'); }
function submitPulse(value) {
    closeModal('pulse-modal');
    document.getElementById('success-mascot').innerHTML = mascotSVG;
    document.getElementById('succ-title').innerText = "Feedback Sent!";
    document.getElementById('succ-sub').innerText = "Thanks! Your feedback helps AERIS improve.";
    document.getElementById('succ-details').innerHTML = '';
    document.getElementById('succ-action-btn').classList.add('hidden');
    openModal('success-modal');
    setTimeout(() => closeModal('success-modal'), 2500);
}

// Facility Report
function getPriority(cat, issue = '') {
    if(['Fire', 'Explosion'].includes(issue)) return 'CRITICAL';
    if(['Electrical Hazard', 'Severe Flooding', 'Structural Danger'].includes(issue)) return 'CRITICAL'; 
    if(cat === 'Safety') return 'CRITICAL';
    if(['Plumbing', 'Building / Structure'].includes(cat) || issue.includes('Leak')) return 'HIGH';
    if(['Air Conditioning', 'Electrical'].includes(cat)) return 'MEDIUM';
    return 'LOW'; 
}

function openReportModal() {
    document.getElementById('rep-bldg').value = 'Library';
    document.getElementById('rep-room').value = '';
    document.getElementById('rep-desc').value = '';
    openModal('report-modal');
}

function openReportModalFromMap(bldg, floor) {
    document.getElementById('rep-bldg').value = bldg;
    document.getElementById('rep-floor').value = floor;
    openModal('report-modal');
}

function submitFacilityReport() {
    const bldg = document.getElementById('rep-bldg').value;
    const floor = document.getElementById('rep-floor').value;
    const room = document.getElementById('rep-room').value || 'Unknown Zone';
    const cat = document.getElementById('rep-cat').value;
    const desc = document.getElementById('rep-desc').value;
    
    const priority = getPriority(cat, desc);
    const id = '#R-' + Math.floor(Math.random()*1000).toString().padStart(3, '0');
    
    const report = {
        id, category: cat, issue: cat + ' Issue', description: desc, priority,
        location: { building: bldg, floor, room }, status: 'Submitted', timestamp: new Date().toISOString()
    };
    
    reports.unshift(report);
    saveReports();
    
    closeModal('report-modal');
    showReportSuccess(report);
}

function showReportSuccess(report) {
    document.getElementById('success-mascot').innerHTML = mascotSVG;
    document.getElementById('succ-title').innerText = "Report Submitted!";
    document.getElementById('succ-sub').innerText = "Your facility report has been sent to the Admin.";
    
    document.getElementById('succ-details').innerHTML = `
        <div class="sd-row"><span>Location:</span> <strong>${report.location.building} — Fl ${report.location.floor} — ${report.location.room}</strong></div>
        <div class="sd-row"><span>Category:</span> <strong>${report.category}</strong></div>
    `;
    document.getElementById('succ-action-btn').classList.remove('hidden');
    openModal('success-modal');
}

// Emergency Alert
function openEmergencyModal() {
    document.querySelectorAll('.em-chip').forEach(c => c.classList.remove('selected'));
    document.getElementById('em-cat').value = '';
    document.getElementById('em-confirm-area').classList.add('hidden');
    document.getElementById('em-pre-submit').classList.remove('hidden');
    openModal('emergency-modal');
}

function selectEmType(btn, type) {
    document.querySelectorAll('.em-chip').forEach(c => c.classList.remove('selected'));
    btn.classList.add('selected');
    document.getElementById('em-cat').value = type;
}

function showEmergencyConfirm() {
    if(!document.getElementById('em-cat').value) return alert("Please select what is happening.");
    document.getElementById('em-pre-submit').classList.add('hidden');
    document.getElementById('em-confirm-area').classList.remove('hidden');
}

function cancelEmergency() {
    document.getElementById('em-confirm-area').classList.add('hidden');
    document.getElementById('em-pre-submit').classList.remove('hidden');
}

function submitEmergency() {
    const bldg = document.getElementById('em-bldg').value;
    const floor = document.getElementById('em-floor').value;
    const room = document.getElementById('em-room').value || 'Unknown Zone';
    const type = document.getElementById('em-cat').value;
    
    const id = '#E-' + Math.floor(Math.random()*1000).toString().padStart(3, '0');
    
    const report = {
        id, category: 'Safety', issue: type, description: 'Emergency Alert Triggered', priority: 'CRITICAL',
        location: { building: bldg, floor, room }, status: 'Critical', timestamp: new Date().toISOString()
    };
    
    reports.unshift(report);
    saveReports();
    
    closeModal('emergency-modal');
    showReportSuccess(report);
}

// 5. My Reports (User)
function renderMyReports() {
    const container = document.getElementById('user-reports-list');
    if(reports.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-muted);">You haven\'t submitted any reports yet.</div>';
        return;
    }
    
    container.innerHTML = reports.map(r => `
        <div class="report-card">
            <div class="report-info">
                <div class="report-id">${r.id}</div>
                <div class="report-issue">${r.issue}</div>
                <div class="report-meta">
                    <span>📍 ${r.location.building} - ${r.location.room}</span>
                    <span>🕒 Just now</span>
                </div>
            </div>
            <div class="report-status">
                <span style="font-size:0.875rem; font-weight:600; color:var(--primary-blue);">${r.status}</span>
            </div>
        </div>
    `).join('');
}


// 6. ADMIN SYSTEM
function initAdmin() {
    document.getElementById('footer-mascot').innerHTML = mascotSVG; // Inject footer mascot globally
    switchAdminView('dashboard');
    updateAdminBadges();
}

function switchAdminView(view) {
    currentAdminView = view;
    document.querySelectorAll('.admin-nav-item').forEach(el => {
        el.classList.remove('active');
        if(el.dataset.view === view) el.classList.add('active');
    });

    // Update Breadcrumb
    const bcText = document.querySelector(`.admin-nav-item[data-view="${view}"]`).textContent.replace(/[0-9]/g, '').trim();
    document.getElementById('admin-bc').textContent = bcText;

    const content = document.getElementById('admin-view-content');
    const tpl = document.getElementById(`tpl-admin-${view}`);
    
    if(tpl) {
        content.innerHTML = tpl.innerHTML;
        if(view === 'dashboard') renderAdminDashboard();
        if(view === 'reports') renderAdminReports();
    } else {
        content.innerHTML = `<div class="admin-panel" style="min-height: 400px; justify-content:center; align-items:center; color:var(--text-muted);"><h3>${bcText} View</h3><p>Content for this module is under development.</p></div>`;
    }
}

function updateAdminBadges() {
    const criticalCount = reports.filter(r => r.priority === 'CRITICAL' && r.status !== 'Resolved').length;
    const pendingCount = reports.filter(r => r.status === 'Submitted' || r.status === 'Critical').length;
    
    const alertBadge = document.getElementById('nav-badge-alerts');
    if(alertBadge) { alertBadge.textContent = criticalCount; alertBadge.style.display = criticalCount > 0 ? 'inline-block' : 'none'; }
    
    const reportsBadge = document.getElementById('nav-badge-reports');
    if(reportsBadge) { reportsBadge.textContent = pendingCount; reportsBadge.style.display = pendingCount > 0 ? 'inline-block' : 'none'; }
}

function renderAdminDashboard() {
    const active = reports.filter(r => r.status !== 'Resolved');
    const crits = active.filter(r => r.priority === 'CRITICAL');
    const warns = active.filter(r => r.priority === 'HIGH' || r.priority === 'MEDIUM');
    const infos = active.filter(r => r.priority === 'LOW');

    document.getElementById('dash-critical').textContent = crits.length.toString().padStart(2, '0');
    document.getElementById('dash-warning').textContent = warns.length.toString().padStart(2, '0');
    document.getElementById('dash-info').textContent = infos.length.toString().padStart(2, '0');
    
    // Anomaly Feed
    const feed = document.getElementById('admin-anomaly-feed');
    if(active.length === 0) {
        feed.innerHTML = '<div style="color:var(--text-muted); font-size:0.875rem;">No active anomalies.</div>';
    } else {
        // Sort Critical first, then by date
        active.sort((a,b) => {
            const map = {'CRITICAL':3, 'HIGH':2, 'MEDIUM':2, 'LOW':1};
            return map[b.priority] - map[a.priority];
        });
        
        feed.innerHTML = active.map(r => {
            let cls = 'info';
            let label = 'INFO';
            if(r.priority === 'CRITICAL') { cls = 'critical'; label = 'CRITICAL'; }
            if(r.priority === 'HIGH' || r.priority === 'MEDIUM') { cls = 'warning'; label = 'WARNING'; }
            
            return `
            <div class="alert-card-mini ${cls}" onclick="openAdminReportDetail('${r.id}')">
                <div class="acm-pri">${label}</div>
                <div><strong>${r.location.building} ${r.location.room}:</strong> ${r.issue}</div>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">${r.description || 'No additional details'}</div>
            </div>`;
        }).join('');
    }

    renderAdminEnergyChart();
}

function renderAdminReports() {
    const filterPri = document.getElementById('filter-priority')?.value || 'All';
    const filterStat = document.getElementById('filter-status')?.value || 'All';
    
    let filtered = reports.filter(r => {
        if(filterPri !== 'All' && r.priority !== filterPri) return false;
        if(filterStat !== 'All' && r.status !== filterStat) return false;
        return true;
    });

    const priMap = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
    filtered.sort((a,b) => priMap[b.priority] - priMap[a.priority]);

    const tbody = document.getElementById('admin-reports-tbody');
    if(!tbody) return;
    
    tbody.innerHTML = filtered.map(r => {
        const cls = {'LOW':'pri-low', 'MEDIUM':'pri-medium', 'HIGH':'pri-high', 'CRITICAL':'pri-critical'}[r.priority];
        return `
        <tr>
            <td style="font-family:monospace; color:var(--text-muted);">${r.id}</td>
            <td><strong>${r.issue}</strong></td>
            <td>${r.location.building} - ${r.location.room}</td>
            <td>${r.category}</td>
            <td><span class="priority-badge ${cls}">${r.priority}</span></td>
            <td><span style="font-weight:600;">${r.status}</span></td>
            <td><button class="btn btn-secondary btn-sm" onclick="openAdminReportDetail('${r.id}')">View</button></td>
        </tr>
    `;
    }).join('');
}

function openAdminReportDetail(id) {
    const r = reports.find(x => x.id === id);
    if(!r) return;
    
    const cls = {'LOW':'pri-low', 'MEDIUM':'pri-medium', 'HIGH':'pri-high', 'CRITICAL':'pri-critical'}[r.priority];
    document.getElementById('admin-rd-content').innerHTML = `
        <h3 style="margin-bottom:24px;">Report Details ${r.id}</h3>
        <div style="text-align:left; font-size:0.875rem; margin-bottom:24px;">
            <div class="sd-row"><span>Priority:</span> <span class="priority-badge ${cls}">${r.priority}</span></div>
            <div class="sd-row"><span>Issue:</span> <strong>${r.issue}</strong></div>
            <div class="sd-row"><span>Location:</span> <strong>${r.location.building} - ${r.location.room}</strong></div>
            <div class="sd-row"><span>Category:</span> ${r.category}</div>
            <div class="sd-row"><span>Status:</span> <strong style="color:var(--primary-blue)">${r.status}</strong></div>
            <div style="margin-top:16px;"><strong>Description:</strong><p style="background:var(--bg-color); padding:12px; border-radius:8px; margin-top:8px;">${r.description || 'No description provided.'}</p></div>
        </div>
        <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center;">
            <button class="btn btn-outline btn-sm" onclick="updateReportStatus('${r.id}', 'In Progress')">Mark In Progress</button>
            <button class="btn btn-primary btn-sm" onclick="updateReportStatus('${r.id}', 'Resolved')">Mark Resolved</button>
        </div>
    `;
    openModal('admin-report-detail-modal');
}

function updateReportStatus(id, newStatus) {
    const r = reports.find(x => x.id === id);
    if(r) {
        r.status = newStatus;
        saveReports();
        closeModal('admin-report-detail-modal');
    }
}

// 7. Global Admin Banner Logic
function checkGlobalAlerts() {
    const latestCrit = reports.find(r => r.priority === 'CRITICAL' && r.status !== 'Resolved');
    const banner = document.getElementById('admin-global-banner');
    
    if(latestCrit && currentView === 'admin') {
        document.getElementById('banner-issue-text').textContent = `${latestCrit.issue} reported at ${latestCrit.location.building} — ${latestCrit.location.room}`;
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}

function dismissBanner() { document.getElementById('admin-global-banner').classList.add('hidden'); }
function openAdminAlerts() {
    dismissBanner();
    if(currentView !== 'admin') navigateTo('admin');
    setTimeout(() => switchAdminView('reports'), 100); // Route to reports since alerts feed is in dashboard now
}

// Listen to storage events (simulates real-time updates across tabs)
window.addEventListener('storage', (e) => {
    if(e.key === 'aeris_reports') {
        reports = JSON.parse(e.newValue || '[]');
        refreshCurrentViews();
    }
});
window.addEventListener('reports_updated', () => { refreshCurrentViews(); });

function refreshCurrentViews() {
    if(currentView === 'myreports') renderMyReports();
    if(currentView === 'admin') {
        updateAdminBadges();
        switchAdminView(currentAdminView);
        checkGlobalAlerts();
    }
}

// 8. Charts (Chart.js)
function renderDetailChart(space) {
    const ctx = document.getElementById('comfortChart');
    if(!ctx) return;
    if(charts.detail) charts.detail.destroy();
    const data = [ space.comfortScore-10, space.comfortScore-5, space.comfortScore-15, space.comfortScore+2, space.comfortScore-2, space.comfortScore ].map(v => Math.min(100, Math.max(0, v)));
    charts.detail = new Chart(ctx, {
        type: 'line',
        data: { labels: ['08:00', '10:00', '12:00', '14:00', '16:00', 'Now'], datasets: [{ data: data, borderColor: '#7F8FF3', backgroundColor: 'rgba(127, 143, 243, 0.1)', borderWidth: 3, tension: 0.4, fill: true, pointBackgroundColor: '#fff' }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { min: 0, max: 100, grid: { color: 'rgba(217, 222, 250, 0.4)' } } } }
    });
}
function renderAdminEnergyChart() {
    const ctx = document.getElementById('adminEnergyChart');
    if(!ctx) return;
    if(charts.adminEnergy) charts.adminEnergy.destroy();
    charts.adminEnergy = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['M', 'T', 'W', 'T', 'F', 'S', 'S'],
            datasets: [
                { type: 'line', label: 'IEQ (%)', data: [95, 90, 85, 60, 55, 80, 82], borderColor: '#7F8FF3', borderWidth: 2, tension: 0.4, yAxisID: 'y1', pointRadius: 0 },
                { type: 'bar', label: 'Power (kWh)', data: [120, 110, 90, 40, 40, 100, 105], backgroundColor: 'rgba(217, 222, 250, 0.6)', borderRadius: 2, yAxisID: 'y' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { position: 'left', display: false }, y1: { position: 'right', display: false, grid: { drawOnChartArea: false } }, x: { display: false } } }
    });
}

// 9. Real-time Simulation Engine
setInterval(() => {
    spaces.forEach(space => {
        space.temperature = Math.max(18, Math.min(30, space.baseValues.temp + (Math.random()*0.4-0.2)));
        space.humidity = Math.max(30, Math.min(80, space.baseValues.hum + (Math.random()*2-1)));
        space.co2 = Math.max(400, space.baseValues.co2 + Math.floor(Math.random()*20-10));
        
        const tel = document.getElementById(`val-temp-${space.id}`); if(tel) tel.textContent = `${space.temperature.toFixed(1)}°C`;
        const hel = document.getElementById(`val-hum-${space.id}`); if(hel) hel.textContent = `${Math.round(space.humidity)}% RH`;
        const cel = document.getElementById(`val-co2-${space.id}`); if(cel) cel.textContent = `${space.co2} ppm`;
    });
}, 3000);

// Initialize
window.onload = () => { navigateTo('home'); };
