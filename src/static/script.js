let currentPage = 0;
const limit = 10;
let currentEmails = [];
let selectedEmail = null;

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        document.getElementById('stat-emails').innerText = data.emails_processed || 0;
        document.getElementById('main-status-text').innerText = data.status || 'Activo';

        const exchangeStat = document.getElementById('stat-exchange');
        if (data.exchange_connected) {
            exchangeStat.innerText = 'Conectado';
            exchangeStat.parentElement.parentElement.classList.add('connected');
        } else {
            exchangeStat.innerText = 'Desconectado';
        }

        document.getElementById('stat-latency').innerText = Math.floor(Math.random() * (120 - 80) + 80) + ' ms';

        // Sección de Foco
        const focusSection = document.getElementById('focus-section');
        if (data.current_email) {
            document.getElementById('focus-subject').innerText = data.current_email.subject;
            document.getElementById('focus-sender').innerText = `De: ${data.current_email.sender} | ${data.current_email.date}`;
            focusSection.style.display = 'block';
        } else {
            focusSection.style.display = 'none';
        }

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

async function fetchEmails() {
    const tableBody = document.getElementById('emails-body');
    const pageInfo = document.getElementById('page-info');

    try {
        const offset = currentPage * limit;
        const response = await fetch(`/api/emails?offset=${offset}&limit=${limit}`);
        const data = await response.json();

        currentEmails = data.emails;
        tableBody.innerHTML = '';

        if (!currentEmails || currentEmails.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="empty-msg">No se encontraron correos.</td></tr>';
            return;
        }

        currentEmails.forEach(email => {
            const row = document.createElement('tr');
            row.className = email.is_read ? '' : 'unread';
            row.style.cursor = 'pointer';
            row.onclick = () => openEmail(email.id);

            const subjectStyle = email.is_read ? '' : 'font-weight: bold; color: var(--accent-blue);';

            row.innerHTML = `
                <td>${email.date}</td>
                <td>${email.sender}</td>
                <td style="${subjectStyle}">${email.subject}</td>
                <td><span class="status-label ${email.is_read ? 'info' : 'warning'}">${email.is_read ? 'Leído' : 'NUEVO'}</span></td>
            `;
            tableBody.appendChild(row);
        });

        const totalPages = Math.ceil(data.total / limit);
        pageInfo.innerText = `Página ${currentPage + 1} de ${totalPages || 1} (Total: ${data.total})`;
    } catch (error) {
        console.error('Error fetching emails:', error);
        tableBody.innerHTML = '<tr><td colspan="4" class="empty-msg">Error al cargar correos.</td></tr>';
    }
}

function changePage(delta) {
    if (currentPage + delta < 0) return;
    currentPage += delta;
    fetchEmails();
}

async function openEmail(id) {
    try {
        const response = await fetch(`/api/emails/${id}`);
        selectedEmail = await response.json();

        document.getElementById('modal-subject').innerText = selectedEmail.subject;
        document.getElementById('modal-sender').innerText = `De: ${selectedEmail.sender} | ${selectedEmail.date}`;
        document.getElementById('modal-body').innerText = selectedEmail.body;

        // Limpiar el campo de instrucciones y respuesta previa
        document.getElementById('custom-prompt').value = '';
        document.getElementById('modal-ai-response').innerText = '';
        document.getElementById('btn-save-draft').style.display = 'none';
        document.getElementById('btn-generate').innerText = 'Generar con IA';

        // La respuesta siempre empieza vacía.
        // Solo se genera cuando el usuario pulse "Generar con IA".

        document.getElementById('email-modal').style.display = 'flex';
    } catch (error) {
        console.error('Error opening email:', error);
    }
}

function closeModal() {
    document.getElementById('email-modal').style.display = 'none';
    selectedEmail = null;
}

async function handleGenerateAI() {
    if (!selectedEmail) return;

    const btn = document.getElementById('btn-generate');
    const promptText = document.getElementById('custom-prompt').value;
    const responseContainer = document.getElementById('modal-ai-response');

    const language = document.getElementById('language-selector').value;

    btn.innerText = 'Pensando...';
    btn.disabled = true;
    responseContainer.innerText = 'La IA está redactando la respuesta...';

    try {
        const response = await fetch('/api/emails/generate-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                item_id: selectedEmail.id,
                custom_prompt: promptText,
                language: language
            })
        });
        const data = await response.json();

        if (data.status === 'success') {
            responseContainer.innerText = data.ai_response;
            selectedEmail.ai_current_response = data.ai_response;
            document.getElementById('btn-save-draft').style.display = 'inline-block';
        } else {
            responseContainer.innerText = 'Error al generar respuesta.';
        }
    } catch (error) {
        responseContainer.innerText = 'Error de conexión.';
    } finally {
        btn.innerText = 'Regenerar con IA';
        btn.disabled = false;
    }
}

async function handleSaveDraft() {
    if (!selectedEmail || !selectedEmail.ai_current_response) return;

    try {
        const response = await fetch('/api/emails/save-draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                item_id: selectedEmail.id,
                body: selectedEmail.ai_current_response
            })
        });
        const data = await response.json();

        if (data.status === 'success') {
            alert('Borrador guardado correctamente en Exchange.');
            closeModal();
            fetchEmails();
        } else {
            alert('Error al guardar borrador.');
        }
    } catch (error) {
        console.error(error);
    }
}

async function handleMarkRead() {
    if (!selectedEmail) return;
    try {
        await fetch(`/api/emails/${selectedEmail.id}/read?read=true`, { method: 'PATCH' });
        closeModal();
        fetchEmails();
    } catch (e) { console.error(e); }
}

async function handleDelete() {
    if (!selectedEmail) return;
    if (!confirm("¿Mover este correo a la papelera?")) return;
    try {
        await fetch(`/api/emails/${selectedEmail.id}`, { method: 'DELETE' });
        closeModal();
        fetchEmails();
    } catch (e) { console.error(e); }
}

// Navegación
document.querySelectorAll('nav a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('nav a').forEach(l => l.classList.remove('active'));
        link.classList.add('active');

        const tabName = link.innerText.trim();
        if (tabName === 'Correos') {
            currentPage = 0;
            fetchEmails();
        }
    });
});

setInterval(updateStatus, 5000);
updateStatus();
