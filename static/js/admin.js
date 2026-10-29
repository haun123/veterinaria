// Función para alternar entre las vistas del panel administrativo
function cambiarSeccion(seccionId, event) {
    event.preventDefault();
    
    // Quitar clase active a todos los links del menú
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Añadir clase active al link presionado
    event.currentTarget.classList.add('active');

    // Ocultar todas las secciones
    document.querySelectorAll('.section-view').forEach(sec => {
        sec.classList.remove('active');
    });

    // Mostrar la sección seleccionada
    const targetSection = document.getElementById('section-' + seccionId);
    if (targetSection) {
        targetSection.classList.add('active');
    }
}