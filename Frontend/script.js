// UPDATE THIS URL for Production
const API_BASE = "https://socialmediacontentengine.vercel.app/api"; 
// const API_BASE = "http://localhost:8000/api"; 

let calendar;
let activeBrandId = null;
let activePostId = null;

document.addEventListener('DOMContentLoaded', () => {
    initCalendar();
    loadBrands();
});

// --- 1. SETUP CALENDAR ---
function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        height: 'auto',
        events: [], // Will load from DB
        eventClick: function(info) {
            openPostDetails(info.event);
        },
        dateClick: function(info) {
            // Pre-fill date when clicking a day
            document.getElementById('planDate').value = info.dateStr + "T10:00";
            openPlanModal();
        }
    });
    calendar.render();
}

// --- 2. BRAND SIDEBAR ---
async function loadBrands() {
    try {
        const res = await fetch(`${API_BASE}/brands`);
        const brands = await res.json();
        const list = document.getElementById('brandList');
        list.innerHTML = '';
        
        brands.forEach(b => {
            const item = document.createElement('div');
            item.className = 'brand-item';
            item.innerHTML = `<span class="dot"></span> ${b.name}`;
            item.onclick = () => selectBrand(b, item);
            list.appendChild(item);
        });
    } catch(e) { console.error(e); }
}

async function selectBrand(brand, el) {
    activeBrandId = brand._id;
    
    // UI Updates
    document.querySelectorAll('.brand-item').forEach(i => i.classList.remove('active'));
    el.classList.add('active');
    
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('calendarWrapper').classList.remove('hidden');
    document.getElementById('actions').classList.remove('hidden');
    
    document.getElementById('activeBrandHeader').innerHTML = `
        <h2>${brand.name}</h2>
        <p>${brand.industry} Protocol Active</p>
    `;
    
    refreshCalendar();
}

// --- 3. POSTS & CALENDAR DATA ---
async function refreshCalendar() {
    const res = await fetch(`${API_BASE}/brands/${activeBrandId}/posts`);
    const posts = await res.json();
    
    const events = posts.map(p => ({
        id: p._id,
        title: p.topic,
        start: p.scheduled_date,
        backgroundColor: p.status === 'Generated' ? '#10b981' : '#334155',
        extendedProps: p
    }));
    
    calendar.removeAllEvents();
    calendar.addEventSource(events);
}

// --- 4. PLANNING (Step 1) ---
async function savePlan() {
    const topic = document.getElementById('planTopic').value;
    const date = document.getElementById('planDate').value;
    
    if(!topic || !date) return alert("Required fields missing");

    await fetch(`${API_BASE}/posts/plan`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            brand_id: activeBrandId,
            topic: topic,
            scheduled_date: date
        })
    });
    
    togglePlanModal();
    refreshCalendar();
}

// --- 5. GENERATION (Step 2) ---
function openPostDetails(event) {
    const p = event.extendedProps;
    activePostId = p._id; // Fixed: Use _id from props
    
    document.getElementById('viewTopic').textContent = p.topic;
    document.getElementById('viewDate').textContent = new Date(event.start).toLocaleString();
    
    const statusBadge = document.getElementById('viewStatus');
    statusBadge.textContent = p.status;
    statusBadge.className = `status-badge ${p.status.toLowerCase()}`;
    
    const btn = document.getElementById('btnGenerate');
    const contentBox = document.getElementById('aiContent');

    if (p.status === 'Generated') {
        contentBox.classList.remove('hidden');
        document.getElementById('viewCaption').innerText = p.caption;
        document.getElementById('viewVisual').innerText = p.visual_idea;
        btn.innerHTML = 'Regenerate <i class="ph-bold ph-arrows-clockwise"></i>';
    } else {
        contentBox.classList.add('hidden');
        btn.innerHTML = 'Generate Content <i class="ph-bold ph-sparkle"></i>';
    }
    
    document.getElementById('viewModal').classList.remove('hidden');
}

async function runGenerator() {
    const btn = document.getElementById('btnGenerate');
    btn.disabled = true;
    btn.innerHTML = 'Analyzing Trends... <div class="loader-mini"></div>';
    
    try {
        const res = await fetch(`${API_BASE}/posts/${activePostId}/generate`, {method: 'POST'});
        if(!res.ok) throw new Error("Generation Failed");
        
        const updatedPost = await res.json();
        
        // Update UI immediately
        document.getElementById('viewCaption').innerText = updatedPost.caption;
        document.getElementById('viewVisual').innerText = updatedPost.visual_idea;
        document.getElementById('aiContent').classList.remove('hidden');
        
        const statusBadge = document.getElementById('viewStatus');
        statusBadge.textContent = "GENERATED";
        statusBadge.classList.add('generated');
        
        refreshCalendar(); // Update calendar color
    } catch(e) {
        alert("Error: " + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Regenerate <i class="ph-bold ph-arrows-clockwise"></i>';
    }
}

// --- HELPERS ---
function toggleBrandModal() { document.getElementById('brandModal').classList.toggle('hidden'); }
function togglePlanModal() { document.getElementById('planModal').classList.toggle('hidden'); }
function openPlanModal() { document.getElementById('planModal').classList.remove('hidden'); }
function closeViewModal() { document.getElementById('viewModal').classList.add('hidden'); }
async function createBrand() {
    const name = document.getElementById('newBrandName').value;
    const ind = document.getElementById('newBrandIndustry').value;
    const web = document.getElementById('newBrandWebsite').value;
    await fetch(`${API_BASE}/brands`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, industry: ind, website: web})
    });
    toggleBrandModal();
    loadBrands();
}
