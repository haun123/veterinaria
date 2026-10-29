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
                        <strong class="text-dark">${m.nombre}</strong>
                        <div class="small text-muted">${m.especie} • ${m.raza || 'Raza no especificada'} • ${m.peso} kg</div>
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

// Filtro rápido de búsqueda en tiempo real
function filtrarDuenos() {
    const texto = document.getElementById('inputBuscarDueno').value.toLowerCase();
    const filtrados = listaDuenosGlobal.filter(item => 
        item.nombre_completo.toLowerCase().includes(texto) || 
        item.telefono.includes(texto)
    );
    renderizarTarjetas(filtrados);
}