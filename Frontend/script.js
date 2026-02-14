const API_URL = "http://127.0.0.1:8000/api/generate";

const form = document.getElementById('agentForm');
const submitBtn = document.getElementById('submitBtn');
const loadingDiv = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const contentDisplay = document.getElementById('contentDisplay');
const cardsContainer = document.getElementById('cardsContainer');
const errorDiv = document.getElementById('errorMessage');

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
        // 3. Send to Python Backend
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (!response.ok) throw new Error("Backend connection failed");

        const result = await response.json();
        
        // 4. Render Results
        renderCalendar(result.data);

    } catch (error) {
        showError("Agent failed. Is the Python backend running on port 8000?");
        console.error(error);
    }
});

function renderCalendar(data) {
    // Hide loading
    loadingDiv.classList.add('hidden');
    emptyState.classList.add('hidden');
    contentDisplay.classList.remove('hidden');

    // Set Header
    document.getElementById('strategyTitle').textContent = data.week_focus;
    document.getElementById('strategySubtitle').textContent = `Strategy for ${data.client_name}`;

    // Clear previous cards
    cardsContainer.innerHTML = '';

    // Create Cards
    data.cards.forEach(card => {
        const cardHTML = `
            <div class="result-card">
                <span class="day-badge">${card.day}</span>
                <h3>${card.topic}</h3>
                <p style="background:#f1f5f9; padding:10px; border-radius:8px; margin:10px 0; font-family:monospace; font-size:0.9em;">
                    ${card.caption}
                </p>
                <div class="visual-prompt">
                    <span class="visual-label">AI Image Prompt</span>
                    "${card.visual_idea}"
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
    submitBtn.disabled = true;
    submitBtn.textContent = "Agent Working...";
}

function showError(msg) {
    loadingDiv.classList.add('hidden');
    errorDiv.textContent = msg;
    errorDiv.classList.remove('hidden');
    submitBtn.disabled = false;
    submitBtn.textContent = "Start Research Agent";
}