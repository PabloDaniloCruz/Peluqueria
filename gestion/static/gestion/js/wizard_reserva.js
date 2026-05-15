/**
 * Wizard de Reserva Interna — Studio Salta
 *
 * Lee configuración de window.WIZARD_CONFIG (inyectado por el template):
 *   - servicios:     lista de servicios activos
 *   - profesionales: lista de profesionales con habilidades
 *   - urls:          { buscarClientes, disponibilidad, reservar }
 *   - csrfToken:     token CSRF
 */
document.addEventListener('DOMContentLoaded', function () {
    const CONFIG = window.WIZARD_CONFIG;
    const serviciosData = CONFIG.servicios;
    const profesionalesData = CONFIG.profesionales;

    // --- Estado del wizard ---
    let serviciosSeleccionados = [];  // [{servicio_id, orden}]
    let opcionesData = null;          // Respuesta cacheada de disponibilidad

    // =========================================================
    // Buscador de Clientes (Paso 1)
    // =========================================================
    const searchInput = document.getElementById('clienteSearch');
    const resultsDiv = document.getElementById('searchResults');
    let debounceTimer;

    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const query = this.value;
        if (query.length < 2) {
            resultsDiv.style.display = 'none';
            return;
        }
        debounceTimer = setTimeout(() => {
            fetch(`${CONFIG.urls.buscarClientes}?q=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => {
                    resultsDiv.innerHTML = '';
                    if (data.results.length > 0) {
                        data.results.forEach(c => {
                            const btn = document.createElement('button');
                            btn.type = 'button';
                            btn.className = 'list-group-item list-group-item-action';
                            btn.innerHTML = `<strong>${c.nombre} ${c.apellido}</strong><br><small class="text-muted">${c.telefono}</small>`;
                            btn.onclick = () => seleccionarCliente(c);
                            resultsDiv.appendChild(btn);
                        });
                        resultsDiv.style.display = 'block';
                    } else {
                        resultsDiv.style.display = 'none';
                    }
                });
        }, 300);
    });

    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.style.display = 'none';
        }
    });

    function seleccionarCliente(c) {
        document.getElementById('cliente_id').value = c.id;
        document.getElementById('inp_nombre').value = c.nombre;
        document.getElementById('inp_apellido').value = c.apellido;
        document.getElementById('inp_telefono').value = c.telefono;
        resultsDiv.style.display = 'none';
        searchInput.value = `${c.nombre} ${c.apellido}`;
        ['inp_nombre', 'inp_apellido', 'inp_telefono'].forEach(id =>
            document.getElementById(id).classList.add('bg-light')
        );
    }

    // =========================================================
    // Servicios (Paso 1)
    // =========================================================
    function renderServicios() {
        const container = document.getElementById('lista-servicios');
        container.innerHTML = '';

        serviciosData.forEach(s => {
            const horas = Math.floor(s.duracion_estimada / 60);
            const mins = s.duracion_estimada % 60;
            const durStr = horas > 0
                ? `${horas}h ${mins > 0 ? mins + 'min' : ''}`
                : `${mins} min`;

            const col = document.createElement('div');
            col.className = 'col';
            col.innerHTML = `
                <div class="card servicio-card h-100" data-id="${s.id}" onclick="toggleServicio(${s.id})">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title mb-1">${s.nombre}</h6>
                            <small class="text-muted">${durStr}</small>
                        </div>
                        <div class="text-end">
                            <span class="fw-bold text-primary">$${parseFloat(s.precio_sugerido).toLocaleString()}</span>
                            <br>
                            <span class="badge bg-light text-dark mt-1 check-badge" style="display:none;">✓ Seleccionado</span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(col);
        });
    }

    window.toggleServicio = function (servId) {
        const idx = serviciosSeleccionados.findIndex(s => s.servicio_id === servId);
        if (idx >= 0) {
            serviciosSeleccionados.splice(idx, 1);
        } else {
            const servData = serviciosData.find(s => s.id === servId);
            serviciosSeleccionados.push({
                servicio_id: servId,
                orden: servData.orden_sugerido
            });
            serviciosSeleccionados.sort((a, b) => a.orden - b.orden);
        }
        actualizarUIServicios();
    };

    function actualizarUIServicios() {
        document.querySelectorAll('.servicio-card').forEach(card => {
            const id = parseInt(card.dataset.id);
            const selected = serviciosSeleccionados.some(s => s.servicio_id === id);
            card.classList.toggle('selected', selected);
            card.querySelector('.check-badge').style.display = selected ? '' : 'none';
        });

        const resumen = document.getElementById('resumen-servicios');
        if (serviciosSeleccionados.length > 0) {
            resumen.style.display = '';
            let totalDur = 0, totalPrecio = 0;
            serviciosSeleccionados.forEach(s => {
                const data = serviciosData.find(d => d.id === s.servicio_id);
                totalDur += data.duracion_estimada;
                totalPrecio += parseFloat(data.precio_sugerido);
            });

            const horas = Math.floor(totalDur / 60);
            const mins = totalDur % 60;
            document.getElementById('count-servicios').textContent = serviciosSeleccionados.length;
            document.getElementById('duracion-total').textContent =
                horas > 0 ? `${horas}h ${mins}min` : `${mins} min`;
            document.getElementById('precio-total').textContent = totalPrecio.toLocaleString();
        } else {
            resumen.style.display = 'none';
        }

        document.getElementById('btn-paso2').disabled = serviciosSeleccionados.length === 0;
    }

    // =========================================================
    // Navegación de Pasos
    // =========================================================
    window.irAPaso = function (paso) {
        if (paso === 2 && serviciosSeleccionados.length === 0) {
            mostrarError('Seleccioná al menos un servicio.');
            return;
        }
        if (paso === 2) renderProfesionales();

        document.querySelectorAll('.wizard-step').forEach(el => el.style.display = 'none');
        document.getElementById(`paso-${paso}`).style.display = '';

        document.querySelectorAll('.step-item').forEach(el => {
            const s = parseInt(el.dataset.step);
            el.classList.remove('active', 'done');
            if (s < paso) el.classList.add('done');
            if (s === paso) el.classList.add('active');
        });
    };

    // =========================================================
    // Profesionales (Paso 2)
    // =========================================================
    function renderProfesionales() {
        const container = document.getElementById('asignacion-profesionales');
        container.innerHTML = '';

        serviciosSeleccionados.forEach((sel, idx) => {
            const servData = serviciosData.find(s => s.id === sel.servicio_id);
            const profsHabilitados = profesionalesData.filter(p =>
                p.habilidades.includes(sel.servicio_id)
            );

            const div = document.createElement('div');
            div.className = 'card mb-3 border-0 bg-light';
            div.innerHTML = `
                <div class="card-body d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-0">${idx + 1}. ${servData.nombre}</h6>
                        <small class="text-muted">${servData.duracion_estimada} min</small>
                    </div>
                    <div style="min-width: 250px;">
                        <select class="form-select select-prof" data-servicio="${sel.servicio_id}">
                            <option value="">Cualquier profesional</option>
                            ${profsHabilitados.map(p =>
                                `<option value="${p.id}">${p.nombre}</option>`
                            ).join('')}
                        </select>
                    </div>
                </div>
            `;
            container.appendChild(div);
        });
    }

    // =========================================================
    // Buscar Disponibilidad (Paso 2 → 3)
    // =========================================================
    window.buscarDisponibilidad = function () {
        const servicios = [];
        document.querySelectorAll('.select-prof').forEach(sel => {
            servicios.push({
                servicio_id: parseInt(sel.dataset.servicio),
                profesional_id: sel.value ? parseInt(sel.value) : null
            });
        });

        const fecha = document.getElementById('inp_fecha').value;
        const clienteId = document.getElementById('cliente_id').value;

        if (!fecha) {
            mostrarError('Seleccioná una fecha.');
            return;
        }

        irAPaso(3);
        document.getElementById('loading-horarios').style.display = '';
        document.getElementById('opciones-horarios').innerHTML = '';
        document.getElementById('alternativas-section').style.display = 'none';

        fetch(CONFIG.urls.disponibilidad, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken,
            },
            body: JSON.stringify({
                fecha: fecha,
                hora_preferida: document.getElementById('inp_hora_preferida').value || null,
                cliente_id: clienteId || null,
                servicios: servicios
            })
        })
        .then(r => r.json())
        .then(data => {
            document.getElementById('loading-horarios').style.display = 'none';
            opcionesData = data;

            if (data.error) {
                document.getElementById('opciones-horarios').innerHTML =
                    `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            renderOpciones(data.opciones || [], 'opciones-horarios', false);

            if (data.alternativas && data.alternativas.length > 0) {
                document.getElementById('alternativas-section').style.display = '';
                renderOpciones(data.alternativas, 'alternativas-horarios', true);
            }
        })
        .catch(() => {
            document.getElementById('loading-horarios').style.display = 'none';
            mostrarError('Error de conexión al buscar horarios.');
        });
    };

    // =========================================================
    // Renderizar Opciones de Horario (Paso 3)
    // =========================================================
    function renderOpciones(opciones, containerId, esAlternativa) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (opciones.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <h5>No se encontraron horarios disponibles</h5>
                    <p>Probá otra fecha o cambiá los servicios/profesionales.</p>
                </div>
            `;
            return;
        }

        opciones.forEach((op, idx) => {
            const horas = Math.floor(op.duracion_total / 60);
            const mins = op.duracion_total % 60;
            const durStr = horas > 0
                ? `${horas}h ${mins > 0 ? mins + 'min' : ''}`
                : `${mins} min`;

            const isMejor = idx === 0 && !esAlternativa;
            const div = document.createElement('div');
            div.className = `opcion-horario ${esAlternativa ? 'alternativa' : ''}`;
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <div>
                        ${isMejor ? '<span class="badge bg-success badge-score me-2">⭐ Mejor opción</span>' : ''}
                        <strong>${op.inicio} → ${op.fin}</strong>
                        <span class="text-muted ms-2">(${durStr})</span>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="confirmarOpcion(${idx}, ${esAlternativa})">
                        Elegir esta opción
                    </button>
                </div>
                <div class="timeline-bloques">
                    ${op.bloques.map(b => `
                        <div class="bloque-timeline">
                            <span class="hora">${b.inicio} - ${b.fin}</span>
                            <div>
                                <span class="servicio-nombre">${b.servicio_nombre}</span>
                                <span class="prof-nombre">— ${b.profesional_nombre}</span>
                            </div>
                            <span class="badge bg-light text-muted">${b.duracion} min</span>
                        </div>
                    `).join('')}
                </div>
            `;
            container.appendChild(div);
        });
    }

    // =========================================================
    // Confirmar Opción Elegida
    // =========================================================
    window.confirmarOpcion = function (idx, esAlternativa) {
        if (!opcionesData) return;

        const lista = esAlternativa ? opcionesData.alternativas : opcionesData.opciones;
        const opcionElegida = lista[idx];

        const payload = {
            fecha: document.getElementById('inp_fecha').value,
            cliente_id: document.getElementById('cliente_id').value || null,
            nombre: document.getElementById('inp_nombre').value,
            apellido: document.getElementById('inp_apellido').value,
            telefono: document.getElementById('inp_telefono').value,
            opcion: opcionElegida
        };

        fetch(CONFIG.urls.reservar, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken,
            },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                mostrarExito(data.message);
                setTimeout(() => window.location.href = data.redirect, 1500);
            } else {
                mostrarError(data.error || 'Error al confirmar la reserva.');
            }
        })
        .catch(() => {
            mostrarError('Error de conexión al confirmar.');
        });
    };

    // =========================================================
    // Helpers
    // =========================================================
    function mostrarError(msg) {
        const el = document.getElementById('alerta-error');
        el.textContent = msg;
        el.classList.remove('d-none');
        setTimeout(() => el.classList.add('d-none'), 5000);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function mostrarExito(msg) {
        const el = document.getElementById('alerta-exito');
        el.textContent = msg;
        el.classList.remove('d-none');
    }

    // =========================================================
    // Inicializar Selector de Horarios (Dinamizado por DB)
    // =========================================================
    function initTimePicker() {
        const select = document.getElementById('inp_hora_preferida');
        const fechaVal = document.getElementById('inp_fecha').value;
        if (!select || !fechaVal) return;

        // Guardar valor actual para intentar restaurarlo
        const valorActual = select.value;
        // Limpiar opciones actuales (excepto "Cualquier horario")
        while (select.options.length > 1) select.remove(1);

        // Calcular día de la semana (Django 0=Lunes, JS getDay() 0=Domingo)
        const fecha = new Date(fechaVal + 'T00:00:00');
        const diaSemana = (fecha.getDay() + 6) % 7; 

        const horario = CONFIG.horarios.find(h => h.dia_semana === diaSemana);
        
        if (!horario) {
            const opt = document.createElement('option');
            opt.textContent = "Local cerrado este día";
            opt.disabled = true;
            select.appendChild(opt);
            return;
        }

        const [h_ini, m_ini] = horario.hora_apertura.split(':').map(Number);
        const [h_fin, m_fin] = horario.hora_cierre.split(':').map(Number);

        let h = h_ini, m = m_ini;
        const totalMinFin = h_fin * 60 + m_fin;

        while ((h * 60 + m) <= totalMinFin) {
            const hh = h.toString().padStart(2, '0');
            const mm = m.toString().padStart(2, '0');
            const time = `${hh}:${mm}`;
            
            const option = document.createElement('option');
            option.value = time;
            option.textContent = time;
            if (time === valorActual) option.selected = true;
            select.appendChild(option);

            m += 5;
            if (m >= 60) { m = 0; h++; }
        }
    }

    // --- Init ---
    initTimePicker();
    renderServicios();

    const fechaInput = document.getElementById('inp_fecha');
    if (fechaInput) {
        fechaInput.addEventListener('change', initTimePicker);
    }
});
