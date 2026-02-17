const API_URL = "https://socialmediacontentengine.vercel.app/api/generate";
const form = document.getElementById('agentForm');
const submitBtn = document.getElementById('submitBtn');
const loadingDiv = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const contentDisplay = document.getElementById('contentDisplay');
const cardsContainer = document.getElementById('cardsContainer');
const errorDiv = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // 1. Gather Data
    const formData = {
        client_name: document.getElementById('clientName').value,
        industry: document.getElementById('industry').value,
        website_url: document.getElementById('websiteUrl').value,
        additional_notes: document.getElementById('notes').value
    };

    // 2. UI State: Loading
    showLoading();

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (!response.ok) throw new Error("Server communication failed.");

        const result = await response.json();
        
        // 4. Render Results
        renderCalendar(result.data);

    } catch (error) {
        showError("System Error: Ensure Backend is active on Port 8000.");
        console.error(error);
    }
});

function renderCalendar(data) {
    loadingDiv.classList.add('hidden');
    emptyState.classList.add('hidden');
    contentDisplay.classList.remove('hidden');

    document.getElementById('strategyTitle').textContent = data.week_focus;
    document.getElementById('strategySubtitle').textContent = `Target Protocol: ${data.client_name}`;

    cardsContainer.innerHTML = '';

    data.cards.forEach(card => {
        // No emojis here. Using clean HTML structure.
        const cardHTML = `
            <div class="result-card">
                <span class="day-badge">${card.day}</span>
                <h3>${card.topic}</h3>
                
                <div class="caption-box">
                    ${card.caption}
                </div>
                
                <div class="visual-prompt">
                    <i class="ph-bold ph-image"></i>
                    <div>
                        <span class="visual-label">Generative Prompt</span>
                        <span class="visual-text">"${card.visual_idea}"</span>
                    </div>
                </div>
            </div>
        `;
        cardsContainer.innerHTML += cardHTML;
    });
}

function showLoading() {
    errorDiv.classList.add('hidden');
    contentDisplay.classList.add('hidden');
    emptyState.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    
    // Disable button with a tech-style text
    submitBtn.disabled = true;
    submitBtn.innerHTML = `Running Protocol <div class="loader" style="width:15px; height:15px; border-width:2px; display:inline-block; margin-bottom:0; vertical-align:middle; margin-left:5px;"></div>`;
}

function showError(msg) {
    loadingDiv.classList.add('hidden');
    errorDiv.classList.remove('hidden');
    errorText.textContent = msg;
    
    submitBtn.disabled = false;
    submitBtn.innerHTML = `Initialize Agent <i class="ph-bold ph-arrow-right"></i>`;
}

