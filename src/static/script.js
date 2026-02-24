async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Actualizar textos básicos
        document.getElementById('stat-emails').innerText = data.emails_processed || 0;
        document.getElementById('main-status-text').innerText = data.status || 'Activo';

        const exchangeStat = document.getElementById('stat-exchange');
        if (data.exchange_connected) {
            exchangeStat.innerText = 'Conectado';
            exchangeStat.parentElement.parentElement.classList.add('connected');
        } else {
            exchangeStat.innerText = 'Desconectado';
        }

        // Actualizar tabla de correos si estamos en esa pestaña
        if (data.emails && data.emails.length > 0) {
            updateEmailsTable(data.emails);
        }

        // Simular latencia dinámica
        document.getElementById('stat-latency').innerText = Math.floor(Math.random() * (120 - 80) + 80) + ' ms';

        // Actualización de la tabla de eventos (si el estado cambia)
        if (data.last_error) {
            addEvent('Error', data.last_error, 'danger');
        }

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

function addEvent(event, detail, type = 'info') {
    const tableBody = document.getElementById('events-body');
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' +
        now.getMinutes().toString().padStart(2, '0') + ':' +
        now.getSeconds().toString().padStart(2, '0');

    // Evitar duplicados consecutivos de errores
    const firstRow = tableBody.firstChild;
    if (firstRow && firstRow.innerText && firstRow.innerText.includes(detail)) return;

    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${timeStr}</td>
        <td>${event}</td>
        <td>${detail}</td>
        <td><span class="status-label ${type}">${type === 'danger' ? 'ERROR' : 'OK'}</span></td>
    `;

    if (tableBody.querySelector('.empty-msg')) {
        tableBody.innerHTML = '';
    }

    tableBody.insertBefore(row, tableBody.firstChild);

    // Limitar a los últimos 10 eventos
    if (tableBody.children.length > 10) {
        tableBody.removeChild(tableBody.lastChild);
    }
}

// Almacén temporal de correos para interactividad
let currentEmails = [];

function updateEmailsTable(emails) {
    currentEmails = emails; // Guardar para usar al hacer clic
    const tableBody = document.getElementById('events-body');
    // Si el usuario está en la pestaña de correos (esto es simplificado)
    if (document.querySelector('nav a.active').innerText.includes('Dashboard')) {
        // En el Dashboard mostramos actividad, no los correos directamente
        return;
    }

    tableBody.innerHTML = '';
    emails.forEach(email => {
        const status = email.status || 'PENDIENTE';
        const statusClass = status === 'PROCESADO' ? 'success' : 'info';

        const row = document.createElement('tr');
        row.style.cursor = 'pointer';
        row.onclick = () => showEmailDetail(email);
        row.innerHTML = `
            <td>${email.date.split(' ')[1]}</td>
            <td>${email.sender}</td>
            <td>${email.subject}</td>
            <td><span class="status-label ${statusClass}">${status}</span></td>
        `;
        tableBody.appendChild(row);
    });
}

function showEmailDetail(email) {
    if (!email.ai_response) {
        addEvent('Dashboard', 'El correo aún no ha sido procesado por la IA', 'warning');
        return;
    }

    // Por ahora usamos un alert o un modal simple. Vamos a inyectar un "detalle" en el log
    addEvent('IA Response (' + email.subject.substring(0, 10) + '..)', email.ai_response, 'success');
    console.log("Respuesta Completa:", email.ai_response);
}

// Navegación de pestañas básica
document.querySelectorAll('nav a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('nav a').forEach(l => l.classList.remove('active'));
        link.classList.add('active');

        const tabName = link.innerText.trim();
        const tableHeader = document.querySelector('thead tr');
        const sectionTitle = document.querySelector('.section-header h3');

        if (tabName === 'Correos') {
            sectionTitle.innerText = 'Bandeja de Entrada (vía Exchange)';
            tableHeader.innerHTML = '<th>Hora</th><th>Remitente</th><th>Asunto</th><th>Estado AI</th>';
            document.getElementById('events-body').innerHTML = '<tr><td colspan="4" class="empty-msg">Cargando correos de Exchange...</td></tr>';
            updateStatus(); // Forzar actualización
        } else if (tabName === 'Dashboard') {
            sectionTitle.innerText = 'Actividad Reciente';
            tableHeader.innerHTML = '<th>Hora</th><th>Evento</th><th>Detalle</th><th>Estado</th>';
        }
    });
});

// Iniciar con algunos eventos de bienvenida
setTimeout(() => addEvent('Sistema', 'Dashboard iniciado correctamente', 'info'), 500);
setTimeout(() => addEvent('Conector', 'Buscando servidor Exchange...', 'info'), 1500);

// Actualizar cada 5 segundos
setInterval(updateStatus, 5000);
updateStatus();
