/**
 * Gestión de Servicios — Studio Salta
 * Maneja el reordenamiento de servicios mediante drag/drop (flechas)
 */
function moverFila(btn, direccion) {
    const fila = btn.closest('tr');
    const tabla = fila.parentElement;
    const filas = Array.from(tabla.querySelectorAll('tr[data-id]'));
    const idx = filas.indexOf(fila);
    const destino = idx + direccion;

    if (destino < 0 || destino >= filas.length) return;

    if (direccion === -1) {
        tabla.insertBefore(fila, filas[destino]);
    } else {
        tabla.insertBefore(filas[destino], fila);
    }

    recalcularOrden();
    marcarModificado();
}

function recalcularOrden() {
    const filas = document.querySelectorAll('#tabla-servicios tr[data-id]');
    filas.forEach((fila, idx) => {
        fila.dataset.orden = idx + 1;
        fila.querySelector('.orden-badge').textContent = idx + 1;
    });
}

function marcarModificado() {
    const btnGuardar = document.getElementById('btn-guardar-orden');
    if (btnGuardar && btnGuardar.classList.contains('d-none')) {
        btnGuardar.classList.remove('d-none');
    }
}

function guardarOrden(url, csrfToken) {
    const filas = document.querySelectorAll('#tabla-servicios tr[data-id]');
    const ordenes = {};
    filas.forEach(fila => {
        ordenes[fila.dataset.id] = parseInt(fila.dataset.orden);
    });

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ ordenes })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById('btn-guardar-orden').classList.add('d-none');
            const alerta = document.getElementById('alerta-orden');
            alerta.classList.remove('d-none');
            alerta.classList.add('show');
            setTimeout(() => {
                alerta.classList.remove('show');
                alerta.classList.add('d-none');
            }, 3000);
        } else {
            alert('Error al guardar: ' + (data.error || 'desconocido'));
        }
    })
    .catch(() => alert('Error de red al guardar el orden.'));
}
