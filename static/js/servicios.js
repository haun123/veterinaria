// Cargar servicios al iniciar la página
document.addEventListener("DOMContentLoaded", () => {
    cargarServicios();
});

// Función para obtener los servicios desde Flask y pintarlos en la tabla
async function cargarServicios() {
    try {
        const response = await fetch('/api/servicios');
        const result = await response.json();
        
        const tbody = document.getElementById('tablaServiciosBody');
        tbody.innerHTML = '';

        if (result.success && result.data.length > 0) {
            result.data.forEach(s => {
                tbody.innerHTML += `
                    <tr>
                        <td class="fw-bold">${s.nombre}</td>
                        <td><span class="badge bg-secondary">${s.tipo}</span></td>
                        <td>${s.duracionMin} min</td>
                        <td class="text-success fw-bold">$${s.precio.toFixed(2)}</td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-primary" onclick='abrirEditarServicio(${JSON.stringify(s)})'>
                                <i class="bi bi-pencil-fill"></i> Editar
                            </button>
                        </td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No hay servicios registrados.</td></tr>`;
        }
    } catch (error) {
        console.error("Error cargando servicios:", error);
    }
}

// Preparar el modal para crear uno nuevo
function prepararNuevoServicio() {
    document.getElementById('modalServicioTitulo').innerText = "Registrar Nuevo Servicio";
    document.getElementById('servicioIdEditar').value = "";
    document.getElementById('formServicio').reset();
}

// Rellenar el modal con los datos para editar
function abrirEditarServicio(servicio) {
    document.getElementById('modalServicioTitulo').innerText = "Editar Servicio";
    document.getElementById('servicioIdEditar').value = servicio._id;
    document.getElementById('servNombre').value = servicio.nombre;
    document.getElementById('servTipo').value = servicio.tipo;
    document.getElementById('servDuracion').value = servicio.duracionMin;
    document.getElementById('servPrecio').value = servicio.precio;

    const modal = new bootstrap.Modal(document.getElementById('modalServicio'));
    modal.show();
}

// Guardar (Crear o Actualizar)
async function guardarServicio() {
    const id = document.getElementById('servicioIdEditar').value;
    const datos = {
        nombre: document.getElementById('servNombre').value,
        tipo: document.getElementById('servTipo').value,
        duracion_min: parseInt(document.getElementById('servDuracion').value),
        precio: parseFloat(document.getElementById('servPrecio').value)
    };

    const url = id ? `/api/servicios/actualizar/${id}` : '/api/servicios/crear';
    const metodo = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: metodo,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });

        const result = await response.json();
        if (result.success) {
            const modalEl = document.getElementById('modalServicio');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            modalInstance.hide();
            
            cargarServicios();
        } else {
            alert("Error al guardar: " + result.error);
        }
    } catch (error) {
        console.error("Error en la petición:", error);
    }
}