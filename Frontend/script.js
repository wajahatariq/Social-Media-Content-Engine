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
        }
    });
    calendar.render();
}

async function loadBrands() {
    try {
        const res = await fetch(`${API_BASE}/brands`);
        if (!res.ok) throw new Error("Backend connection failed.");
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
    } catch(e) { 
        document.getElementById('brandList').innerHTML = `<p style="color:red; font-size: 0.8rem; padding: 1rem;">Server Offline</p>`;
    }
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
    if (!activeBrandId) return;
    const res = await fetch(`${API_BASE}/brands/${activeBrandId}/posts`);
    const posts = await res.json();
    
    const events = posts.map(p => {
        // NEW: Force the browser to recognize the database time as UTC
        let secureDate = p.scheduled_date;
        if (!secureDate.endsWith('Z') && !secureDate.includes('+')) {
            secureDate += 'Z'; 
        }
        p.scheduled_date = secureDate; // Update it for the View Modal too
        
        return {
            id: p._id,
            title: p.topic,
            start: secureDate,
            backgroundColor: p.status === 'Approved' ? '#10b981' : '#3b82f6',
            extendedProps: p
        };
    });
    
    calendar.removeAllEvents();
    calendar.addEventSource(events);
}
    
    calendar.removeAllEvents();
    calendar.addEventSource(events);
}

// THE NEW ONE-CLICK GENERATOR
async function generateMonth() {
    if(!activeBrandId) return;
    
    const btn = document.getElementById('btnMonth');
    btn.innerHTML = '<div class="loader-mini" style="display:inline-block; border-top-color: #3b82f6; width: 14px; height: 14px; margin-right: 5px;"></div> Planning 12 Posts...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/posts/generate_month`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ brand_id: activeBrandId })
        });
        
        if (!res.ok) throw new Error("Failed to generate.");
        
        await refreshCalendar();
        alert("Success! 12 new posts have been distributed across your calendar.");
    } catch(e) {
        alert("Generation failed. The AI might have taken too long.");
    } finally {
        btn.innerHTML = '<i class="ph-bold ph-calendar-plus"></i> Generate 1-Month Plan';
        btn.disabled = false;
    }
}

function openPostDetails(event) {
    const p = event.extendedProps;
    activePostId = p._id; 
    
    document.getElementById('viewTopic').textContent = p.topic;
    document.getElementById('viewDate').textContent = new Date(event.start).toLocaleString();
    
    const localDate = new Date(event.start);
    localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
    document.getElementById('scheduleDate').value = localDate.toISOString().slice(0, 16);
    
    const statusBadge = document.getElementById('viewStatus');
    statusBadge.textContent = p.status;
    statusBadge.className = `status-badge ${p.status.toLowerCase()}`;
    
    const contentBox = document.getElementById('aiContent');
    const uploadArea = document.getElementById('uploadArea');
    const btnApprove = document.getElementById('btnApprove');

    contentBox.classList.remove('hidden');
    document.getElementById('viewCaption').innerText = p.caption;
    document.getElementById('viewVisual').innerText = p.visual_idea;
    
    if (p.status !== 'Approved') {
        uploadArea.classList.remove('hidden');
        btnApprove.classList.remove('hidden');
    } else {
        uploadArea.classList.add('hidden');
        btnApprove.classList.add('hidden');
    }
    
    document.getElementById('viewModal').classList.remove('hidden');
}

async function approveAndQueue() {
    const fileInput = document.getElementById('designUpload');
    const dateInput = document.getElementById('scheduleDate').value;

    if (!fileInput.files[0]) {
        return alert("Please upload your final design image first.");
    }
    if (!dateInput) {
        return alert("Please select a date and time to publish this post.");
    }

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onloadend = async () => {
        // Create a hidden image element to process the compression
        const img = new Image();
        img.src = reader.result;
        
        img.onload = async () => {
            // Setup an invisible canvas to resize the image
            const canvas = document.createElement('canvas');
            const MAX_WIDTH = 1080; // Standard optimal width for Facebook/Instagram
            let scaleSize = 1;
            
            if (img.width > MAX_WIDTH) {
                scaleSize = MAX_WIDTH / img.width;
            }
            
            canvas.width = img.width * scaleSize;
            canvas.height = img.height * scaleSize;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            
            // Compress the image to an 80% quality JPEG
            const compressedBase64 = canvas.toDataURL('image/jpeg', 0.8);

            const btn = document.getElementById('btnApprove');
            btn.innerHTML = 'Queuing...';
            btn.disabled = true;

            try {
                const res = await fetch(`${API_BASE}/posts/${activePostId}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        image_base64: compressedBase64,
                        scheduled_date: new Date(dateInput).toISOString()
                    })
                });
                
                if (!res.ok) {
                    const errorText = await res.text();
                    throw new Error(`Server Error: ${res.status} - ${errorText}`);
                }
                
                closeViewModal();
                refreshCalendar(); 
                alert("Post Queued! It will be published at your selected time.");
            } catch (e) {
                alert("Error queuing post:\n" + e.message);
                console.error(e);
            } finally {
                btn.innerHTML = '<i class="ph-bold ph-check-circle"></i> Approve and Queue';
                btn.disabled = false;
            }
        };
    };
    reader.readAsDataURL(file);
}

function toggleBrandModal() { document.getElementById('brandModal').classList.toggle('hidden'); }
function closeViewModal() { document.getElementById('viewModal').classList.add('hidden'); }

async function createBrand() {
    const data = {
        name: document.getElementById('newBrandName').value,
        industry: document.getElementById('newBrandIndustry').value,
        website: document.getElementById('newBrandWebsite').value,
        phone_number: document.getElementById('newBrandPhone').value,
        facebook_page_id: document.getElementById('newBrandFbPageId').value,
        facebook_access_token: document.getElementById('newBrandFbToken').value
    };

    if (!data.name || !data.industry || !data.website || !data.phone_number) {
        return alert("Name, Industry, Website, and Phone are required.");
    }

    await fetch(`${API_BASE}/brands`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    toggleBrandModal();
    loadBrands();
}

async function deleteBrand() {
    if (!activeBrandId) return;
    if (confirm("Are you sure you want to delete this brand and all its scheduled posts?")) {
        try {
            await fetch(`${API_BASE}/brands/${activeBrandId}`, { method: 'DELETE' });
            activeBrandId = null;
            document.getElementById('emptyState').classList.remove('hidden');
            document.getElementById('calendarWrapper').classList.add('hidden');
            document.getElementById('actions').classList.add('hidden');
            document.getElementById('activeBrandHeader').innerHTML = `
                <h2>Select a Brand</h2>
                <p>Select a brand from the sidebar to view calendar.</p>
            `;
            loadBrands();
        } catch (e) {
            alert("Failed to delete brand.");
        }
    }
}


