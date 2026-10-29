let listaHistorialGlobal = []; // Para almacenar los datos y filtrar en tiempo real

// Cargar todo el historial al iniciar la página
document.addEventListener("DOMContentLoaded", () => {
    cargarHistorialCompleto();
});

// Función central para consultar la API y guardar el arreglo global
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

// Función para pintar las tarjetas usando el diseño unificado de la veterinaria
function renderizarTarjetasHistorial(historiales) {
    const contenedor = document.getElementById('resultadosHistorial');
    contenedor.innerHTML = '';

    historiales.forEach(h => {
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

                            <!-- Información Médica Principal -->
                            <div class="mb-3 text-secondary small">
                                <div class="mb-2">
                                    <strong class="text-dark d-block"><i class="bi bi-clipboard2-pulse text-success me-1"></i> Diagnóstico:</strong>
                                    <span class="text-dark">${h.diagnostico}</span>
                                </div>
                                <div class="mb-2">
                                    <strong class="text-dark d-block"><i class="bi bi-activity text-success me-1"></i> Síntomas:</strong>
                                    <span>${h.sintomas}</span>
                                </div>
                            </div>

                            <hr class="text-muted opacity-25">

                            <!-- Tratamiento -->
                            <div class="mb-2">
                                <h6 class="text-success fw-bold small text-uppercase mb-1"><i class="bi bi-capsule me-1"></i> Tratamiento:</h6>
                                <p class="text-secondary small bg-light p-2 rounded mb-0 border-start border-success border-3">
                                    ${h.tratamiento}
                                </p>
                            </div>
                        </div>

                        <!-- Pie de la tarjeta con el costo de la consulta -->
                        <div class="mt-4 pt-2 border-top d-flex justify-content-between align-items-center">
                            <span class="small text-muted">Costo registrado:</span>
                            <span class="fw-bold text-success fs-6">$${(h.costo || 0).toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
}

// Búsqueda en tiempo real filtrando sobre los datos ya cargados o consultando al servidor
function buscarHistorialEnTiempoReal() {
    const termino = document.getElementById('inputBusquedaHistorial').value;
    cargarHistorialCompleto(termino);
}