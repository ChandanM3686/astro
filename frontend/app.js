// Use absolute URL if needed, or relative for Render
let BASE_URL = '';
if (window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    BASE_URL = 'http://localhost:5002';
}

let userData = null;
let pendingReportType = null;

// Helper to handle API Calls
async function fetchReport(reportType) {
    const payload = { ...userData, report_type: reportType };
    const response = await fetch(`${BASE_URL}/generate_report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate report');
    }
    return await response.json();
}

// 1. Initial Form Submit -> Free Plan
document.getElementById('horoscope-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    userData = {
        name: document.getElementById('name').value,
        birth_date: document.getElementById('birth_date').value,
        birth_time: document.getElementById('birth_time').value,
        place_of_birth: document.getElementById('place_of_birth').value,
        gender: document.getElementById('gender').value
    };

    const btn = document.getElementById('generate-btn');
    const btnText = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');

    btn.disabled = true;
    btnText.style.display = 'none';
    loader.style.display = 'block';

    try {
        const data = await fetchReport('free');
        
        // Hide Form, Show Dashboard
        document.getElementById('form-section').classList.add('hidden');
        document.getElementById('dashboard-section').classList.remove('hidden');

        // Populate Free Preview
        const predictionHtml = marked.parse(data.prediction);
        document.getElementById('free-prediction').innerHTML = predictionHtml;

        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        btn.disabled = false;
        btnText.style.display = 'block';
        loader.style.display = 'none';
    }
});

// 2. Pre-Payment Modals (Partner / Celebrity)
function openPaymentModal(type, price) {
    if (type === 'relationship') {
        document.getElementById('partner-modal').classList.remove('hidden');
        return;
    }
    if (type === 'celebrity') {
        document.getElementById('celebrity-modal').classList.remove('hidden');
        return;
    }
    showCheckout(type, price);
}

function closePartnerModal() {
    document.getElementById('partner-modal').classList.add('hidden');
}

function submitPartnerDetails() {
    userData.partner = {
        name: document.getElementById('p-name').value,
        birth_date: document.getElementById('p-birth_date').value,
        birth_time: document.getElementById('p-birth_time').value,
        place_of_birth: document.getElementById('p-place').value
    };
    closePartnerModal();
    showCheckout('relationship', 399);
}

function closeCelebrityModal() {
    document.getElementById('celebrity-modal').classList.add('hidden');
}

function submitCelebrity() {
    userData.target_celebrity = document.getElementById('target-celebrity').value;
    closeCelebrityModal();
    showCheckout('celebrity', 99);
}

// 3. Payment Flow
function showCheckout(type, price) {
    pendingReportType = type;
    
    const titles = {
        'business': 'Business Astrology Report',
        'complete': 'Complete Life Report',
        'relationship': 'Relationship Compatibility',
        'child': 'Child Future Blueprint',
        'gemstone': 'Gemstone Guidance',
        'numerology': 'Name Numerology',
        'celebrity': 'Celebrity Comparison'
    };

    document.getElementById('payment-desc').textContent = `Unlock: ${titles[type]}`;
    document.getElementById('payment-amount').textContent = `₹${price}`;
    document.getElementById('payment-modal').classList.remove('hidden');
}

function closePaymentModal() {
    document.getElementById('payment-modal').classList.add('hidden');
    pendingReportType = null;
}

async function processPayment() {
    if (!pendingReportType) return;

    const btn = document.getElementById('pay-btn');
    const btnText = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');

    btn.disabled = true;
    btnText.style.display = 'none';
    loader.style.display = 'block';

    // Simulate Payment Delay
    await new Promise(r => setTimeout(r, 1500));

    try {
        // Fetch the premium report
        const data = await fetchReport(pendingReportType);
        
        // Close payment modal
        closePaymentModal();

        // Show Report Modal
        showReportModal(pendingReportType, data.prediction);

    } catch (error) {
        alert(`Error generating report: ${error.message}`);
    } finally {
        btn.disabled = false;
        btnText.style.display = 'block';
        loader.style.display = 'none';
    }
}

// 4. Displaying Premium Report
function showReportModal(type, markdownContent) {
    const titles = {
        'business': 'Business Astrology Report',
        'complete': 'Complete Life Report',
        'relationship': 'Relationship Compatibility',
        'child': 'Child Future Blueprint',
        'gemstone': 'Gemstone Guidance',
        'numerology': 'Name Numerology',
        'celebrity': 'Celebrity Comparison'
    };

    document.getElementById('report-title').textContent = titles[type];
    document.getElementById('report-content').innerHTML = marked.parse(markdownContent);
    document.getElementById('report-modal').classList.remove('hidden');
}

function closeReportModal() {
    document.getElementById('report-modal').classList.add('hidden');
}

// 5. Global Oracle Chat (Dashboard)
document.getElementById('global-ask-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!userData) return;

    const questionInput = document.getElementById('global-question');
    const question = questionInput.value;
    const askBtn = document.getElementById('global-ask-btn');
    const chatResponse = document.getElementById('global-chat-response');

    askBtn.disabled = true;
    askBtn.textContent = '...';
    chatResponse.classList.add('hidden');

    try {
        const payload = { ...userData, question: question };
        const response = await fetch(`${BASE_URL}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to get answer');
        }

        const data = await response.json();
        
        chatResponse.innerHTML = `
            <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1)">
                <strong style="color: var(--accent-glow)">Q:</strong> ${data.question}
            </div>
            <div>
                <strong style="color: var(--accent-glow-secondary)">A:</strong> ${marked.parse(data.answer)}
            </div>
        `;
        chatResponse.classList.remove('hidden');
        questionInput.value = '';

    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        askBtn.disabled = false;
        askBtn.textContent = 'Ask';
    }
});
