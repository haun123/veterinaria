let listaDuenosGlobal = []; // Para almacenar los datos y filtrar rápido si es necesario

// Cargar el directorio de dueños y mascotas al iniciar
document.addEventListener("DOMContentLoaded", () => {
    cargarDirectorioDuenos();
});

// Obtener los datos del backend y renderizar las tarjetas
async function cargarDirectorioDuenos() {
    try {
        const response = await fetch('/api/pacientes/listar');
        const result = await response.json();

        const contenedor = document.getElementById('contenedorDuenos');
        contenedor.innerHTML = '';

        if (result.success && result.data.length > 0) {
            listaDuenosGlobal = result.data; // Guardamos para búsqueda local
            renderizarTarjetas(listaDuenosGlobal);
        } else {
            contenedor.innerHTML = `
                <div class="col-12 text-center text-muted py-5">
                    <i class="bi bi-people fs-1 d-block mb-2"></i>
                    <p>No hay dueños ni mascotas registradas en el sistema.</p>
                </div>`;
        }
    } catch (error) {
        console.error("Error cargando el directorio:", error);
    }
}

// Función para pintar las tarjetas en el HTML
function renderizarTarjetas(duenos) {
    const contenedor = document.getElementById('contenedorDuenos');
    contenedor.innerHTML = '';

    duenos.forEach(item => {
        let mascotasHtml = '';
        if (item.mascotas && item.mascotas.length > 0) {
            mascotasHtml = item.mascotas.map(m => `
                <div class="d-flex align-items-center bg-light p-2 rounded mb-1 border-start border-success border-3">
                    <i class="bi bi-heart-pulse-fill text-success me-2"></i>
                    <div>
                        <!-- Cambiamos href="#" por javascript:void(0); para un control fluido -->
                        <a href="javascript:void(0);" onclick="verHistorialMascota('${m._id}', '${m.nombre}')" class="text-decoration-none fw-bold text-dark">
                            ${m.nombre} <i class="bi bi-box-arrow-up-right small text-muted"></i>
                        </a>
                        <div class="small text-muted">
                            ${m.especie} - ${m.raza || 'Raza no especificada'} - ${m.peso} kg
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            mascotasHtml = '<p class="text-muted small fst-italic mb-0">Sin mascotas asociadas por el momento.</p>';
        }

        contenedor.innerHTML += `
            <div class="col-md-6 col-lg-4">
                <div class="card card-custom h-100 shadow-sm border-0">
                    <div class="card-body d-flex flex-column justify-content-between">
                        <div>
                            <!-- Cabecera de la tarjeta: Nombre del Dueño -->
                            <div class="d-flex align-items-center mb-3">
                                <div class="bg-success text-white rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style="width: 45px; height: 45px;">
                                    <i class="bi bi-person-fill fs-5"></i>
                                </div>
                                <div>
                                    <h5 class="card-title fw-bold text-dark m-0">${item.nombre_completo}</h5>
                                </div>
                            </div>

                            <!-- Información de Contacto -->
                            <div class="mb-3 text-secondary small">
                                <div class="mb-1"><i class="bi bi-telephone-fill text-success me-2"></i><strong>Tel:</strong> ${item.telefono}</div>
                                <div><i class="bi bi-envelope-fill text-success me-2"></i><strong>Email:</strong> ${item.email}</div>
                            </div>

                            <hr class="text-muted opacity-25">

                            <!-- Sección de Mascotas -->
                            <div class="mb-2">
                                <h6 class="text-success fw-bold small text-uppercase mb-2"><i class="bi bi-shield-shaded me-1"></i> Mascotas a su cargo:</h6>
                                <div class="mascotas-list">
                                    ${mascotasHtml}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
}

async function verHistorialMascota(mascotaId, nombreMascota) {
    // Validación rápida por si el ID llega vacío o indefinido
    if (!mascotaId || mascotaId === 'undefined') {
        alert("No se pudo identificar el ID de esta mascota.");
        return;
    }

    try {
        // 1. Mostrar el modal inmediatamente con un indicador de carga
        const modalBody = document.getElementById('modalHistorialBody');
        document.getElementById('modalHistorialTitulo').innerText = `Historial Clínico: ${nombreMascota}`;

        modalBody.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-success" role="status"></div>
                <p class="text-muted small mt-2">Buscando expediente clínico...</p>
            </div>
        `;

        const modalEl = document.getElementById('modalVerHistorialMascota');
        const modalInstance = new bootstrap.Modal(modalEl);
        modalInstance.show();

        // 2. Consultar al backend Flask usando el ID de la mascota
        const response = await fetch(`/api/historial/mascota/${mascotaId}`);
        const result = await response.json();

        let contenidoHtml = '';

        if (result.success && result.data && result.data.length > 0) {
            contenidoHtml = `<div class="list-group">`;

            result.data.forEach(h => {
                // Preparamos la lista de tratamientos si vienen en la API
                let tratamientosHtml = '';
                if (h.tratamientos && h.tratamientos.length > 0) {
                    tratamientosHtml = `
                <div class="mb-2">
                    <strong class="small text-success"><i class="bi bi-capsule me-1"></i> Tratamientos:</strong>
                    <ul class="mb-1 ps-3 small text-secondary">
                        ${h.tratamientos.map(t => `<li>${t}</li>`).join('')}
                    </ul>
                </div>
            `;
                }

                contenidoHtml += `
            <div class="list-group-item mb-3 rounded border-start border-success border-4 shadow-sm p-3">
                <div class="d-flex w-100 justify-content-between align-items-center mb-2">
                    <h6 class="mb-0 fw-bold text-success">
                        <i class="bi bi-file-medical-fill me-1"></i> ${h.motivo || 'Consulta Médica'}
                    </h6>
                    <span class="badge bg-success text-white">${h.fecha || 'Sin fecha'}</span>
                </div>

                <!-- Signos Vitales -->
                <div class="row text-center mb-3 p-2 bg-light rounded border g-0">
                    <div class="col-4 border-end">
                        <small class="text-muted d-block" style="font-size: 0.75rem;"><i class="bi bi-speedometer2 text-danger"></i> Peso</small>
                        <span class="fw-bold text-dark small">${h.signos_vitales?.peso || 0} kg</span>
                    </div>
                    <div class="col-4 border-end">
                        <small class="text-muted d-block" style="font-size: 0.75rem;"><i class="bi bi-thermometer-half text-warning"></i> Temp</small>
                        <span class="fw-bold text-dark small">${h.signos_vitales?.temp || 0} °C</span>
                    </div>
                    <div class="col-4">
                        <small class="text-muted d-block" style="font-size: 0.75rem;"><i class="bi bi-heart-pulse text-primary"></i> F. Cardíaca</small>
                        <span class="fw-bold text-dark small">${h.signos_vitales?.fc || 0} lpm</span>
                    </div>
                </div>

                <p class="mb-1 text-secondary small"><strong>Síntomas:</strong> ${h.sintomas || 'No especificado'}</p>
                <p class="mb-1 text-dark"><strong>Diagnóstico:</strong> ${h.diagnostico || 'Pendiente'}</p>
                
                ${tratamientosHtml}

                ${h.observaciones ? `<p class="mb-1 small text-muted"><strong>Observaciones:</strong> ${h.observaciones}</p>` : ''}

                <div class="d-flex justify-content-between align-items-center mt-3 pt-2 border-top small text-muted">
                    <span><i class="bi bi-calendar-event me-1"></i> Próxima revisión: <strong>${h.proxima_revision || 'No programada'}</strong></span>
                    <span class="badge bg-secondary">$${h.costo || 0} MXN</span>
                </div>
            </div>
        `;
            });

            contenidoHtml += `</div>`;
        } else {
            contenidoHtml = `
        <div class="text-center py-5 text-muted">
            <i class="bi bi-folder2-open display-4 opacity-50"></i>
            <p class="mt-3 mb-0">Esta mascota aún no cuenta con registros en su historial clínico.</p>
        </div>
    `;
        }

        modalBody.innerHTML = contenidoHtml;

    } catch (error) {
        console.error("Error al obtener el historial:", error);
        document.getElementById('modalHistorialBody').innerHTML = `
            <div class="alert alert-danger text-center m-3" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i> Error al conectar con el servidor para cargar el historial.
            </div>
        `;
    }
}

// Filtro rápido de búsqueda en tiempo real
function filtrarDuenos() {
    const texto = document.getElementById('inputBuscarDueno').value.toLowerCase();
    const filtrados = listaDuenosGlobal.filter(item =>
        item.nombre_completo.toLowerCase().includes(texto) ||
        item.telefono.includes(texto)
    );
    renderizarTarjetas(filtrados);
}