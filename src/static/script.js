let currentPage = 0;
const limit = 10;
let currentEmails = [];
let selectedEmail = null;
let currentProfiles = [];
let currentProfileId = null;

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

        // Actualizar Cabecera con Usuario
        const userEmail = data.exchange_user || data.active_profile_name || 'Usuario';
        const userName = (data.active_profile_name || userEmail).split('@')[0].split('.')[0];
        document.getElementById('user-name').innerText = userName.charAt(0).toUpperCase() + userName.slice(1);
        document.getElementById('user-avatar').innerText = userEmail.charAt(0).toUpperCase();

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

        // Ocultar todas las secciones principales
        document.querySelector('.stats-grid').style.display = 'none';
        document.querySelector('.live-feed').style.display = 'none';
        document.getElementById('settings-section').style.display = 'none';
        document.getElementById('knowledge-section').style.display = 'none';

        if (tabName === 'Dashboard') {
            document.querySelector('.stats-grid').style.display = 'grid';
            document.querySelector('.live-feed').style.display = 'block';
        } else if (tabName === 'Correos') {
            document.querySelector('.stats-grid').style.display = 'grid';
            document.querySelector('.live-feed').style.display = 'block';
            currentPage = 0;
            fetchEmails();
        } else if (tabName === 'Conocimiento') {
            document.getElementById('knowledge-section').style.display = 'block';
            loadKnowledge();
        } else if (tabName === 'Ajustes') {
            document.getElementById('settings-section').style.display = 'block';
            loadSettings();
        }
    });
});

async function loadKnowledge() {
    const listBody = document.getElementById('knowledge-body');
    if (!listBody) return;
    
    try {
        const response = await fetch('/api/knowledge');
        const data = await response.json();
        
        listBody.innerHTML = '';
        if (data.length === 0) {
            listBody.innerHTML = '<tr><td colspan="3" class="empty-msg">No hay documentos indexados.</td></tr>';
            return;
        }
        
        data.forEach(doc => {
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid var(--glass-border)';
            row.innerHTML = `
                <td style="padding: 12px; font-size: 14px;">📄 ${doc.filename}</td>
                <td style="padding: 12px; font-size: 14px; color: var(--text-dim);">${doc.created_at}</td>
                <td style="padding: 12px; font-size: 14px;"><span style="color: var(--accent-blue); cursor: pointer;">🔍 Ver</span></td>
            `;
            listBody.appendChild(row);
        });
    } catch (e) {
        listBody.innerHTML = '<tr><td colspan="3" class="empty-msg">Error al cargar conocimiento.</td></tr>';
    }
}

async function handleFileUpload(file) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    const dropZone = document.getElementById('drop-zone');
    const originalContent = dropZone.innerHTML;
    dropZone.innerHTML = `<h4>Procesando e Indexando...</h4><p>${file.name}</p><div class="processing-loader" style="margin: 10px auto;"></div>`;
    
    try {
        const response = await fetch('/api/knowledge/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        alert(result.message);
        loadKnowledge();
    } catch (e) {
        alert('Error al subir el archivo');
    } finally {
        dropZone.innerHTML = originalContent;
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();

        currentProfiles = data.profiles || [];
        currentProfileId = data.active_profile_id || data.profile_id || null;

        populateProfileSelector(currentProfiles, currentProfileId);
        fillSettingsForm(data);
    } catch (e) {
        console.error(e);
    }
}

function populateProfileSelector(profiles, selectedId) {
    const select = document.getElementById('setting-profile-select');
    if (!select) return;

    select.innerHTML = '';

    if (!profiles.length) {
        const option = document.createElement('option');
        option.value = '';
        option.innerText = 'Sin perfiles configurados';
        select.appendChild(option);
        return;
    }

    profiles.forEach(profile => {
        const option = document.createElement('option');
        option.value = profile.id;
        option.innerText = profile.is_active ? `${profile.name} (activo)` : profile.name;
        if (profile.id === selectedId) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

function fillSettingsForm(data) {
    document.getElementById('setting-profile-name').value = data.profile_name || '';
    document.getElementById('setting-ex-user').value = data.exchange_user || '';
    document.getElementById('setting-ex-server').value = data.exchange_server || '';
    document.getElementById('setting-ex-upn').value = data.exchange_upn || '';
    document.getElementById('setting-ex-folder').value = data.exchange_folder || 'INBOX';
    document.getElementById('setting-ex-pass').value = data.exchange_pass || '';
    document.getElementById('setting-ai-threads').value = data.ai_threads || 4;
    document.getElementById('setting-ai-temp').value = data.ai_temp || 0.1;
}

function getSelectedProfile() {
    return currentProfiles.find(profile => profile.id === currentProfileId) || null;
}

function handleNewProfile() {
    currentProfileId = null;
    document.getElementById('setting-profile-select').value = '';
    fillSettingsForm({
        profile_name: '',
        exchange_user: '',
        exchange_server: '',
        exchange_upn: '',
        exchange_folder: 'INBOX',
        exchange_pass: '',
        ai_threads: document.getElementById('setting-ai-threads').value || 4,
        ai_temp: document.getElementById('setting-ai-temp').value || 0.1,
    });
}

async function handleActivateProfile() {
    const select = document.getElementById('setting-profile-select');
    const profileId = select ? select.value : null;
    if (!profileId) {
        alert('Selecciona un perfil para activarlo.');
        return;
    }

    try {
        const response = await fetch('/api/mail-profiles/activate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile_id: profileId })
        });
        const data = await response.json();
        alert(data.message);
        await loadSettings();
        await fetchEmails();
        await updateStatus();
    } catch (e) {
        alert('Error al activar el perfil.');
    }
}

async function handleDeleteProfile() {
    const select = document.getElementById('setting-profile-select');
    const profileId = select ? select.value : null;
    if (!profileId) {
        alert('Selecciona un perfil para eliminarlo.');
        return;
    }
    if (!confirm('¿Eliminar este perfil y sus correos sincronizados?')) {
        return;
    }

    try {
        const response = await fetch(`/api/mail-profiles/${profileId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        alert(data.message);
        await loadSettings();
        await fetchEmails();
        await updateStatus();
    } catch (e) {
        alert('Error al eliminar el perfil.');
    }
}

async function handleSaveConfig() {
    const profileName = document.getElementById('setting-profile-name').value;
    const user = document.getElementById('setting-ex-user').value;
    const server = document.getElementById('setting-ex-server').value;
    const upn = document.getElementById('setting-ex-upn').value;
    const folder = document.getElementById('setting-ex-folder').value;
    const pass = document.getElementById('setting-ex-pass').value;
    const threads = parseInt(document.getElementById('setting-ai-threads').value);
    const temp = parseFloat(document.getElementById('setting-ai-temp').value);

    if (!profileName || !user || !server) {
        alert('Completa nombre de perfil, usuario y servidor.');
        return;
    }

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_id: currentProfileId,
                profile_name: profileName,
                exchange_user: user,
                exchange_server: server,
                exchange_upn: upn,
                exchange_folder: folder,
                exchange_pass: (pass && pass !== "••••••••") ? pass : null,
                ai_threads: threads,
                ai_temp: temp,
                set_active: true
            })
        });
        const data = await response.json();
        alert(data.message);
        await loadSettings();
        await fetchEmails();
        await updateStatus();
    } catch (e) {
        alert('Error al guardar la configuración');
    }
}

document.addEventListener('change', (event) => {
    if (event.target && event.target.id === 'setting-profile-select') {
        const selectedId = event.target.value;
        currentProfileId = selectedId || null;
        const profile = currentProfiles.find(item => item.id === selectedId);
        if (profile) {
            fillSettingsForm({
                profile_id: profile.id,
                profile_name: profile.name,
                exchange_user: profile.email,
                exchange_server: profile.server,
                exchange_upn: profile.upn,
                exchange_folder: profile.folder,
                exchange_pass: '••••••••',
                ai_threads: document.getElementById('setting-ai-threads').value || 4,
                ai_temp: document.getElementById('setting-ai-temp').value || 0.1,
            });
        }
    }
});

setInterval(updateStatus, 5000);
updateStatus();
