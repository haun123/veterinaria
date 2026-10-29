// Cargar las citas al iniciar la página
document.addEventListener("DOMContentLoaded", () => {
    cargarCitas();
});

// Obtener las citas desde Flask y renderizarlas en la tabla
async function cargarCitas() {
    try {
        const response = await fetch('/api/citas');
        const result = await response.json();
        
        const tbody = document.getElementById('tablaCitasBody');
        tbody.innerHTML = '';

        if (result.success && result.data.length > 0) {
            result.data.forEach(cita => {
                const estado = (cita.estado || 'pendiente').toLowerCase();
                
                // Definir insignia de estado
                let estadoBadge = 'bg-secondary';
                if (estado === 'confirmada' || estado === 'atendida') {
                    estadoBadge = 'bg-success';
                } else if (estado === 'pendiente') {
                    estadoBadge = 'bg-warning text-dark';
                } else if (estado === 'cancelada') {
                    estadoBadge = 'bg-danger';
                }

                // Botón de atender solo si está pendiente
                let botonAccion = '';
                if (estado === 'pendiente') {
                    botonAccion = `
                        <button class="btn btn-sm btn-outline-success" onclick="atenderCita('${cita._id}')" title="Atender cita en mostrador">
                            <i class="bi bi-check-circle-fill me-1"></i> Atender
                        </button>`;
                } else {
                    botonAccion = `<span class="text-muted small">Finalizada / Atendida</span>`;
                }

                tbody.innerHTML += `
                    <tr>
                        <td>
                            <div class="fw-bold text-dark">${cita.tutor_nombre}</div>
                            <small class="text-muted"><i class="bi bi-telephone text-success me-1"></i>${cita.tutor_telefono}</small>
                        </td>
                        <td>
                            <div class="fw-semibold text-success"><i class="bi bi-heart-pulse me-1"></i>${cita.mascota_nombre}</div>
                        </td>
                        <td>
                            <div class="fw-medium">${cita.servicio_nombre}</div>
                            <small class="text-muted">${cita.motivo}</small>
                        </td>
                        <td>
                            <span class="badge ${estadoBadge} text-capitalize">${estado}</span>
                        </td>
                        <td class="text-end">
                            ${botonAccion}
                        </td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-4">
                        <i class="bi bi-calendar-x fs-3 d-block mb-2"></i>
                        No hay citas registradas en la agenda.
                    </td>
                </tr>`;
        }
    } catch (error) {
        console.error("Error cargando las citas:", error);
    }
}

// Acción de atender cita
function atenderCita(id) {
    alert("Atendiendo cita ID: " + id + ". Aquí pasaremos al flujo de consulta y generación de historial.");
}

// ==========================================
// FUNCIONES PARA CREAR NUEVA CITA / MOSTRADOR
// ==========================================

// Cargar categorías y servicios al inicializar los selectores del modal de citas
async function prepararNuevaCita() {
    const form = document.getElementById('formNuevaCita');
    if (form) form.reset();
    
    try {
        // Cargar Categorías
        const resCat = await fetch('/api/categorias');
        const dataCat = await resCat.json();
        const selectCat = document.getElementById('citaSelectCategoria');
        if (selectCat) {
            selectCat.innerHTML = '<option value="">Seleccione especie...</option>';
            if (dataCat.success) {
                dataCat.data.forEach(c => {
                    selectCat.innerHTML += `<option value="${c._id}">${c.especie}</option>`;
                });
            }
        }

        // Cargar Servicios
        const resServ = await fetch('/api/servicios');
        const dataServ = await resServ.json();
        const selectServ = document.getElementById('citaSelectServicio');
        if (selectServ) {
            selectServ.innerHTML = '<option value="">Seleccione servicio...</option>';
            if (dataServ.success) {
                dataServ.data.forEach(s => {
                    selectServ.innerHTML += `<option value="${s._id}">${s.nombre} ($${s.precio})</option>`;
                });
            }
        }
    } catch (error) {
        console.error("Error preparando selectores para nueva cita:", error);
    }
}

// Enviar el registro de la nueva cita al backend
async function guardarNuevaCita() {
    const datos = {
        tutor_nombre: document.getElementById('citaTutorNombre').value,
        tutor_apellidos: document.getElementById('citaTutorApellidos').value,
        tutor_telefono: document.getElementById('citaTutorTelefono').value,
        tutor_email: document.getElementById('citaTutorEmail').value,
        mascota_nombre: document.getElementById('citaMascotaNombre').value,
        categoria_id: document.getElementById('citaSelectCategoria').value,
        mascota_raza: document.getElementById('citaMascotaRaza').value,
        mascota_sexo: document.getElementById('citaMascotaSexo').value,
        mascota_peso: parseFloat(document.getElementById('citaMascotaPeso').value) || 0,
        mascota_color: document.getElementById('citaMascotaColor').value,
        mascota_alergias: document.getElementById('citaMascotaAlergias').value,
        servicio_id: document.getElementById('citaSelectServicio').value,
        motivo: document.getElementById('citaMotivo').value
    };

    if (!datos.tutor_nombre || !datos.tutor_telefono || !datos.mascota_nombre || !datos.servicio_id) {
        alert("Por favor completa los campos obligatorios del tutor, mascota y servicio.");
        return;
    }

    try {
        const response = await fetch('/api/citas/crear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });

        const result = await response.json();
        if (result.success) {
            // Cerrar modal y refrescar la tabla de citas
            const modalEl = document.getElementById('modalNuevaCita');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();

            cargarCitas(); // Recargar la tabla
        } else {
            alert("Error al registrar la cita: " + result.error);
        }
    } catch (error) {
        console.error("Error en la petición de nueva cita:", error);
    }
}