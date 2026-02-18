const API_BASE = "https://socialmediacontentengine.vercel.app/api";
let currentBrandId = null;

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    loadBrands();
});

// --- Brand Management ---
async function loadBrands() {
    const grid = document.getElementById('brandGrid');
    grid.innerHTML = '';
    document.getElementById('loadingBrands').classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE}/brands`);
        const brands = await res.json();

        document.getElementById('loadingBrands').classList.add('hidden');

        if (brands.length === 0) {
            grid.innerHTML = '<p class="empty-text">No brands yet. Create one to get started.</p>';
            return;
        }

        brands.forEach(brand => {
            const card = document.createElement('div');
            card.className = 'brand-card';
            card.innerHTML = `
                <div class="brand-icon">${brand.name.substring(0,2).toUpperCase()}</div>
                <h3>${brand.name}</h3>
                <p>${brand.industry}</p>
            `;
            card.onclick = () => openBrand(brand);
            grid.appendChild(card);
        });
    } catch (e) {
        console.error(e);
        grid.innerHTML = '<p class="error-text">Failed to load brands.</p>';
    }
}

async function createBrand() {
    const name = document.getElementById('newBrandName').value;
    const industry = document.getElementById('newBrandIndustry').value;
    const website = document.getElementById('newBrandWebsite').value;

    if (!name || !industry) return alert("Name and Industry are required");

    try {
        await fetch(`${API_BASE}/brands`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, industry, website })
        });
        toggleBrandModal();
        loadBrands();
    } catch (e) {
        alert("Error creating brand");
    }
}

// --- Brand Detail View ---
async function openBrand(brand) {
    currentBrandId = brand._id; // Store ID for scheduling
    
    // UI Updates
    document.getElementById('dashboardView').classList.add('hidden');
    document.getElementById('brandDetailView').classList.remove('hidden');
    document.getElementById('currentBrandName').textContent = brand.name;
    document.getElementById('currentBrandIndustry').textContent = brand.industry;

    loadPosts(brand._id);
}

async function loadPosts(brandId) {
    const container = document.getElementById('postsContainer');
    container.innerHTML = '<div class="loader"></div>';

    try {
        const res = await fetch(`${API_BASE}/brands/${brandId}/posts`);
        const posts = await res.json();
        
        container.innerHTML = '';
        
        if (posts.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No scheduled content.</p></div>';
            return;
        }

        posts.forEach(post => {
            container.innerHTML += `
                <div class="post-card">
                    <div class="post-header">
                        <span class="post-topic">${post.topic}</span>
                        <span class="post-status ${post.status.toLowerCase()}">${post.status}</span>
                    </div>
                    <div class="post-content">
                        <p class="caption">${post.caption}</p>
                    </div>
                    <div class="post-visual">
                        <i class="ph-bold ph-image"></i> ${post.visual_idea}
                    </div>
                </div>
            `;
        });
    } catch (e) {
        console.error(e);
    }
}

function showDashboard() {
    document.getElementById('brandDetailView').classList.add('hidden');
    document.getElementById('dashboardView').classList.remove('hidden');
    currentBrandId = null;
    loadBrands();
}

// --- Content Generation ---
async function generateSchedule() {
    const btn = document.getElementById('generateBtn');
    const topicsRaw = document.getElementById('weekTopics').value;
    const focus = document.getElementById('weekFocus').value;

    if (!topicsRaw) return alert("Please enter at least one topic");

    // Convert new lines to array items
    const topics = topicsRaw.split('\n').filter(t => t.trim() !== '');

    btn.disabled = true;
    btn.innerHTML = 'Generating... <div class="loader-mini"></div>';

    try {
        const res = await fetch(`${API_BASE}/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                brand_id: currentBrandId,
                week_focus: focus,
                topics: topics
            })
        });

        if (!res.ok) throw new Error("Generation failed");

        toggleScheduleModal();
        loadPosts(currentBrandId); // Refresh list
        
        // Reset form
        document.getElementById('weekTopics').value = '';
        document.getElementById('weekFocus').value = '';

    } catch (e) {
        alert("Failed to generate content. Ensure Backend is running.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Generate Content <i class="ph-bold ph-sparkle"></i>';
    }
}

// --- UI Helpers ---
function toggleBrandModal() {
    document.getElementById('brandModal').classList.toggle('hidden');
}
function toggleScheduleModal() {
    document.getElementById('scheduleModal').classList.toggle('hidden');
}


