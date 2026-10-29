let listaHistorialGlobal = [];

// Cargar todo el historial al iniciar la página
document.addEventListener("DOMContentLoaded", () => {
    cargarHistorialCompleto();
});

async function cargarHistorialCompleto(termino = '') {
    try {
        const response = await fetch(`/api/historial/buscar?termino=${encodeURIComponent(termino)}`);
        const result = await response.json();
        
        if (result.success && result.data.length > 0) {
            listaHistorialGlobal = result.data;
            renderizarTarjetasHistorial(listaHistorialGlobal);
        } else {
            const contenedor = document.getElementById('resultadosHistorial');
            contenedor.innerHTML = `
                <div class="col-12 text-center text-muted py-5">
                    <i class="bi bi-journal-x fs-1 d-block mb-2"></i>
                    <p>No se encontraron registros en el historial clínico que coincidan con la búsqueda.</p>
                </div>`;
        }
    } catch (error) {
        console.error("Error cargando el historial clínico:", error);
    }
}

function renderizarTarjetasHistorial(historiales) {
    const contenedor = document.getElementById('resultadosHistorial');
    contenedor.innerHTML = '';

    historiales.forEach(h => {
        // Generar HTML para los tratamientos
        let tratamientosHtml = '';
        if (h.tratamientos && h.tratamientos.length > 0) {
            tratamientosHtml = h.tratamientos.map(t => `
                <div class="d-flex align-items-center bg-light p-2 rounded mb-1 border-start border-success border-3">
                    <i class="bi bi-capsule text-success me-2"></i>
                    <div class="small text-dark">${t}</div>
                </div>
            `).join('');
        } else {
            tratamientosHtml = '<span class="text-muted small fst-italic">Sin tratamientos prescritos.</span>';
        }

        contenedor.innerHTML += `
            <div class="col-md-6 col-lg-4">
                <div class="card card-custom h-100 shadow-sm border-0">
                    <div class="card-body d-flex flex-column justify-content-between">
                        <div>
                            <!-- Cabecera de la tarjeta: Mascota y Fecha -->
                            <div class="d-flex align-items-center mb-3">
                                <div class="bg-success text-white rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style="width: 45px; height: 45px;">
                                    <i class="bi bi-journal-medical fs-5"></i>
                                </div>
                                <div>
                                    <h5 class="card-title fw-bold text-dark m-0">${h.mascota_nombre}</h5>
                                    <span class="badge bg-success-subtle text-success small"><i class="bi bi-calendar-event me-1"></i>${h.fecha}</span>
                                </div>
                            </div>

                            <!-- Motivo y Diagnóstico -->
                            <div class="mb-3 text-secondary small">
                                <div class="mb-1"><strong>Motivo:</strong> ${h.motivo}</div>
                                <div class="mb-1"><strong class="text-dark">Diagnóstico:</strong> <span class="text-success fw-bold">${h.diagnostico}</span></div>
                                <div><strong>Síntomas:</strong> ${h.sintomas}</div>
                            </div>

                            <!-- Signos Vitales (Mini badges) -->
                            <div class="mb-3 p-2 bg-light rounded small text-secondary d-flex justify-content-around">
                                <span><i class="bi bi-speedometer2 text-success"></i> ${h.signos_vitales.peso} kg</span>
                                <span><i class="bi bi-thermometer-half text-success"></i> ${h.signos_vitales.temp} °C</span>
                                <span><i class="bi bi-heart-pulse text-success"></i> ${h.signos_vitales.fc} bpm</span>
                            </div>

                            <hr class="text-muted opacity-25">

                            <!-- Tratamientos -->
                            <div class="mb-2">
                                <h6 class="text-success fw-bold small text-uppercase mb-2"><i class="bi bi-prescription2 me-1"></i> Tratamiento recetado:</h6>
                                <div class="tratamientos-list">
                                    ${tratamientosHtml}
                                </div>
                            </div>

                            ${h.observaciones ? `
                                <div class="mt-2 small text-muted fst-italic">
                                    <i class="bi bi-info-circle me-1"></i> Obs: ${h.observaciones}
                                </div>
                            ` : ''}
                        </div>

                        <!-- Pie de tarjeta con próxima revisión -->
                        <div class="mt-4 pt-2 border-top d-flex justify-content-between align-items-center small text-muted">
                            <span><i class="bi bi-clock-history me-1"></i> Próx: ${h.proxima_revision || 'N/D'}</span>
                            <span class="fw-bold text-success">$${(h.costo || 0).toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
}

function buscarHistorialEnTiempoReal() {
    const termino = document.getElementById('inputBusquedaHistorial').value;
    cargarHistorialCompleto(termino);
}