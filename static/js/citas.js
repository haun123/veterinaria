let listaPacientesGlobalCitas = [];

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
                
                let estadoBadge = 'bg-secondary';
                if (estado === 'confirmada' || estado === 'atendida') {
                    estadoBadge = 'bg-success';
                } else if (estado === 'pendiente') {
                    estadoBadge = 'bg-warning text-dark';
                } else if (estado === 'cancelada') {
                    estadoBadge = 'bg-danger';
                }

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

function atenderCita(id) {
    alert("Atendiendo cita ID: " + id);
}

// ==========================================
// MOSTRADOR Y SELECCIÓN INTELIGENTE
// ==========================================

// Al abrir el modal, cargamos SOLO los tutores y los servicios. Las mascotas inician VACÍAS y bloqueadas.
async function prepararNuevaCita() {
    const form = document.getElementById('formSeleccionCita');
    if (form) form.reset();
    
    try {
        // 1. Cargar tutores desde la API
        const resPacientes = await fetch('/api/pacientes/listar');
        const dataPacientes = await resPacientes.json();
        
        const selectTutor = document.getElementById('selectTutorCita');
        const selectMascota = document.getElementById('selectMascotaCita');
        const btnMascota = document.getElementById('btnAgregarMascotaModal');
        
        if (selectTutor) {
            selectTutor.innerHTML = '<option value="">Seleccione un tutor...</option>';
            if (dataPacientes.success) {
                listaPacientesGlobalCitas = dataPacientes.data;
                listaPacientesGlobalCitas.forEach(tutor => {
                    selectTutor.innerHTML += `<option value="${tutor._id}">${tutor.nombre_completo} (Tel: ${tutor.telefono})</option>`;
                });
            }
        }

        // DEJAR MASCOTAS BLOQUEADAS HASTA QUE SE ELIJA UN TUTOR
        if (selectMascota) {
            selectMascota.innerHTML = '<option value="">Primero seleccione un tutor...</option>';
            selectMascota.disabled = true;
        }
        if (btnMascota) {
            btnMascota.disabled = true;
        }

        // 2. Cargar Servicios
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

        // 3. Cargar Categorías para el sub-modal de mascota nueva
        const resCat = await fetch('/api/categorias');
        const dataCat = await resCat.json();
        const selectCat = document.getElementById('selectCategoriaMascotaModal');
        if (selectCat) {
            selectCat.innerHTML = '<option value="">Seleccione especie...</option>';
            if (dataCat.success) {
                dataCat.data.forEach(c => {
                    selectCat.innerHTML += `<option value="${c._id}">${c.especie}</option>`;
                });
            }
        }
    } catch (error) {
        console.error("Error preparando selectores:", error);
    }
}

// ESTA ES LA CLAVE: Solo se cargan las mascotas del tutor que el usuario elija en el select
function cambiarTutorSeleccionado() {
    const tutorId = document.getElementById('selectTutorCita').value;
    const selectMascota = document.getElementById('selectMascotaCita');
    const btnMascota = document.getElementById('btnAgregarMascotaModal');

    selectMascota.innerHTML = '';
    
    if (!tutorId) {
        selectMascota.innerHTML = '<option value="">Primero seleccione un tutor...</option>';
        selectMascota.disabled = true;
        if (btnMascota) btnMascota.disabled = true;
        return;
    }

    // Buscar al tutor seleccionado dentro de nuestra lista global en memoria
    const tutorEncontrado = listaPacientesGlobalCitas.find(t => t._id === tutorId);

    if (tutorEncontrado && tutorEncontrado.mascotas && tutorEncontrado.mascotas.length > 0) {
        selectMascota.innerHTML = '<option value="">Seleccione una mascota...</option>';
        tutorEncontrado.mascotas.forEach(m => {
            selectMascota.innerHTML += `<option value="${m._id}">${m.nombre} (${m.especie || 'Mascota'} - ${m.raza || 'Sin raza'})</option>`;
        });
        selectMascota.disabled = false;
    } else {
        selectMascota.innerHTML = '<option value="">Este tutor no tiene mascotas registradas</option>';
        selectMascota.disabled = false; // Se habilita para que el usuario pueda usar el botón de "Agregar Mascota"
    }

    if (btnMascota) {
        btnMascota.disabled = false;
    }
}

// Guardar nuevo tutor (Verificando que guarde correctamente en la base de datos)
async function guardarNuevoTutorRapido() {
    const datos = {
        tutor_nombre: document.getElementById('nuevoTutorNombre').value,
        tutor_apellidos: document.getElementById('nuevoTutorApellidos').value,
        tutor_telefono: document.getElementById('nuevoTutorTelefono').value,
        tutor_email: document.getElementById('nuevoTutorEmail').value
    };

    if (!datos.tutor_nombre || !datos.tutor_telefono) {
        alert("Por favor complete el nombre y el teléfono del tutor.");
        return;
    }

    try {
        const response = await fetch('/api/tutores/registrar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        const result = await response.json();

        if (result.success) {
            // Cerrar sub-modal y limpiar formulario
            const modalEl = document.getElementById('modalNuevoTutor');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
            document.getElementById('formNuevoTutor').reset();

            // Refrescar la lista de tutores en el modal principal
            prepararNuevaCita();
            alert("Tutor registrado correctamente en el sistema.");
        } else {
            alert("Error al registrar tutor: " + result.error);
        }
    } catch (error) {
        console.error("Error en la petición de registro de tutor:", error);
    }
}

// Guardar mascota nueva asociada al tutor seleccionado
async function guardarNuevaMascotaRapida() {
    const tutorIdSeleccionado = document.getElementById('selectTutorCita').value;
    if (!tutorIdSeleccionado) {
        alert("Debe seleccionar un tutor primero.");
        return;
    }

    const datos = {
        tutor_id: tutorIdSeleccionado,
        nombre: document.getElementById('nuevaMascotaNombre').value,
        categoria_id: document.getElementById('selectCategoriaMascotaModal').value,
        sexo: document.getElementById('nuevaMascotaSexo').value,
        raza: document.getElementById('nuevaMascotaRaza').value,
        color: document.getElementById('nuevaMascotaColor').value
    };

    if (!datos.nombre || !datos.categoria_id || !datos.sexo) {
        alert("Por favor complete los campos obligatorios: Nombre, Especie y Sexo.");
        return;
    }

    try {
        const response = await fetch('/api/mascotas/registrar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        const result = await response.json();

        if (result.success) {
            const modalEl = document.getElementById('modalNuevaMascotaModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
            document.getElementById('formNuevaMascotaModal').reset();
            
            prepararNuevaCita(); // Recarga los selectores para reflejar la nueva mascota
            alert("Mascota registrada y asociada con éxito.");
        } else {
            alert("Error al registrar mascota: " + result.error);
        }
    } catch (error) {
        console.error("Error guardando mascota rápida:", error);
    }
}