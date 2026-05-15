/**
 * Gestión de Ventas y Facturación — Studio Salta
 * Maneja la adición dinámica de filas de productos/insumos y el cálculo de totales.
 */

function inicializarVentas(config) {
    const { precioBase, totalInputId } = config;
    // Exponer globalmente para los onchange/onclick inline en los partials HTML
    window.totalInput = document.getElementById(totalInputId);

    const btnAgregarProducto = document.getElementById('btn-agregar-producto');
    if (btnAgregarProducto) {
        btnAgregarProducto.addEventListener('click', function() {
            const tr = document.querySelector('#templates .fila-producto').cloneNode(true);
            document.querySelector('#tabla-productos tbody').appendChild(tr);
            recalcularTotal(precioBase, window.totalInput);
        });
    }

    const btnAgregarInsumo = document.getElementById('btn-agregar-insumo');
    if (btnAgregarInsumo) {
        btnAgregarInsumo.addEventListener('click', function() {
            const tr = document.querySelector('#templates .fila-insumo').cloneNode(true);
            document.querySelector('#tabla-insumos tbody').appendChild(tr);
        });
    }
}

function eliminarFila(btn, precioBase, totalInputId) {
    btn.closest('tr').remove();
    const totalInput = document.getElementById(totalInputId);
    recalcularTotal(precioBase, totalInput);
}

function recalcularTotal(precioBase, totalInput) {
    let extra = 0;
    document.querySelectorAll('.fila-producto').forEach(row => {
        const select = row.querySelector('.select-producto');
        const cantInput = row.querySelector('.cantidad-producto');
        const subtotalSpan = row.querySelector('.subtotal-producto');
        
        if (select && select.value) {
            const precio = parseFloat(select.options[select.selectedIndex].dataset.precio);
            const cant = parseInt(cantInput.value) || 0;
            const sub = precio * cant;
            extra += sub;
            if (subtotalSpan) {
                subtotalSpan.innerText = '$' + sub.toFixed(2);
            }
        }
    });
    
    if (totalInput) {
        totalInput.value = (precioBase + extra).toFixed(2);
    }
}
