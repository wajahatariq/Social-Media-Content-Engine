const API_BASE = "https://socialmediacontentengine.vercel.app/api"; 

let calendar;
let activeBrandId = null;
let activePostId = null;

document.addEventListener('DOMContentLoaded', () => {
    initCalendar();
    loadBrands();
});

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
        events: [], 
        eventClick: function(info) {
            openPostDetails(info.event);
        },
        dateClick: function(info) {
            document.getElementById('planDate').value = info.dateStr + "T10:00";
            openPlanModal();
        }
    });
    calendar.render();
}

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

async function refreshCalendar() {
    const res = await fetch(`${API_BASE}/brands/${activeBrandId}/posts`);
    const posts = await res.json();
    
    const events = posts.map(p => ({
        id: p._id,
        title: p.topic,
        start: p.scheduled_date,
        backgroundColor: p.status === 'Approved' ? '#10b981' : (p.status === 'Generated' ? '#3b82f6' : '#334155'),
        extendedProps: p
    }));
    
    calendar.removeAllEvents();
    calendar.addEventSource(events);
}

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

function openPostDetails(event) {
    const p = event.extendedProps;
    activePostId = p._id; 
    
    document.getElementById('viewTopic').textContent = p.topic;
    document.getElementById('viewDate').textContent = new Date(event.start).toLocaleString();
    
    const statusBadge = document.getElementById('viewStatus');
    statusBadge.textContent = p.status;
    statusBadge.className = `status-badge ${p.status.toLowerCase()}`;
    
    const btn = document.getElementById('btnGenerate');
    const contentBox = document.getElementById('aiContent');
    const uploadArea = document.getElementById('uploadArea');
    const btnApprove = document.getElementById('btnApprove');

    if (p.status === 'Generated' || p.status === 'Approved') {
        contentBox.classList.remove('hidden');
        document.getElementById('viewCaption').innerText = p.caption;
        document.getElementById('viewVisual').innerText = p.visual_idea;
        
        uploadArea.classList.remove('hidden');
        btnApprove.classList.remove('hidden');
        btn.innerHTML = 'Regenerate <i class="ph-bold ph-arrows-clockwise"></i>';
    } else {
        contentBox.classList.add('hidden');
        uploadArea.classList.add('hidden');
        btnApprove.classList.add('hidden');
        btn.innerHTML = 'Generate Content <i class="ph-bold ph-lightbulb"></i>';
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
        
        document.getElementById('viewCaption').innerText = updatedPost.caption;
        document.getElementById('viewVisual').innerText = updatedPost.visual_idea;
        document.getElementById('aiContent').classList.remove('hidden');
        document.getElementById('uploadArea').classList.remove('hidden');
        document.getElementById('btnApprove').classList.remove('hidden');
        
        const statusBadge = document.getElementById('viewStatus');
        statusBadge.textContent = "GENERATED";
        statusBadge.classList.add('generated');
        
        refreshCalendar(); 
    } catch(e) {
        alert("Error: " + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Regenerate <i class="ph-bold ph-arrows-clockwise"></i>';
    }
}

async function approveAndQueue() {
    const fileInput = document.getElementById('designUpload');
    if (!fileInput.files[0]) {
        return alert("Please upload your final design image first.");
    }

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onloadend = async () => {
        const base64String = reader.result;
        const btn = document.getElementById('btnApprove');
        btn.innerHTML = 'Queuing... <div class="loader-mini"></div>';

        try {
            await fetch(`${API_BASE}/posts/${activePostId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_base64: base64String })
            });
            
            closeViewModal();
            refreshCalendar(); 
            alert("Post Queued! The system will auto-post it at the scheduled time.");
        } catch (e) {
            alert("Error queuing post.");
        }
    };
    reader.readAsDataURL(file);
}

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
