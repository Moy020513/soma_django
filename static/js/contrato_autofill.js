document.addEventListener('DOMContentLoaded', function() {
    // Buscar el select original que contiene las opciones (FilteredSelectMultiple usa select[name="asignaciones_vinculadas"])
    var select = document.querySelector('select[name="asignaciones_vinculadas"]');
    if (!select) return;

    var infoUrl = select.dataset.assignmentsInfoUrl;
    if (!infoUrl) return;

    // Campos a rellenar
    var empresaField = document.querySelector('#id_empresa');
    var cantidadField = document.querySelector('#id_cantidad_empleados');
    var periodoField = document.querySelector('#id_periodo_ejecucion');

    function clearFields() {
        if (empresaField) {
            // Si es select, dejamos sin selección
            if (empresaField.tagName.toLowerCase() === 'select') {
                empresaField.value = '';
            } else {
                empresaField.value = '';
            }
        }
        if (cantidadField) cantidadField.value = '';
        if (periodoField) periodoField.value = '';
    }

    function updateFromSelection() {
        var selected = Array.from(select.selectedOptions).map(function(opt){ return opt.value; }).filter(Boolean);
        if (selected.length === 0) {
            clearFields();
            return;
        }
        var q = infoUrl + '?ids=' + selected.join(',');
        fetch(q, { credentials: 'same-origin' })
            .then(function(resp){ return resp.json(); })
            .then(function(data){
                if (!data || !data.ok) {
                    return;
                }
                // Empresa: si viene empresa_id, asignar (es un select en admin)
                if (empresaField) {
                    if (data.empresa_id) {
                        empresaField.value = String(data.empresa_id);
                    } else if (empresaField.tagName.toLowerCase() === 'input') {
                        empresaField.value = data.empresa || '';
                    } else {
                        empresaField.value = '';
                    }
                    // Trigger change so admin widgets update
                    empresaField.dispatchEvent(new Event('change'));
                }
                if (cantidadField) cantidadField.value = data.total_emps || '';
                if (periodoField) periodoField.value = data.periodo || '';
            }).catch(function(err){
                console.error('Error fetching assignments info', err);
            });
    }

    // Nueva función: cargar asignaciones para la empresa seleccionada y actualizar el select
    function loadAssignmentsForEmpresa(empresaId) {
        if (!empresaId) {
            // si no hay empresa, limpiamos opciones
            select.innerHTML = '';
            select.dispatchEvent(new Event('change'));
            return;
        }
        var q = infoUrl + '?empresa_id=' + encodeURIComponent(empresaId);
        fetch(q, { credentials: 'same-origin' })
            .then(function(resp){ return resp.json(); })
            .then(function(data){
                if (!data || !data.ok) return;
                var assignments = data.assignments || [];
                // Guardar valores seleccionados actuales
                var selected = new Set(Array.from(select.selectedOptions).map(function(o){ return o.value; }));
                // Limpiar opciones actuales
                select.innerHTML = '';
                assignments.forEach(function(a){
                    var opt = document.createElement('option');
                    opt.value = String(a.pk);
                    var text = a.numero_cotizacion !== null && a.numero_cotizacion !== undefined ? String(a.numero_cotizacion) : '(sin cot)';
                    opt.text = text;
                    if (selected.has(String(a.pk))) opt.selected = true;
                    select.appendChild(opt);
                });
                // Notificar al widget que cambió
                select.dispatchEvent(new Event('change'));
            }).catch(function(err){
                console.error('Error fetching assignments by empresa', err);
            });
    }

    // FilteredSelectMultiple creates two select boxes; but the original select still dispatches change events.
    select.addEventListener('change', updateFromSelection);
    // Initialize on load
    updateFromSelection();

    // Cuando cambie la empresa, recargar las asignaciones disponibles
    if (empresaField) {
        empresaField.addEventListener('change', function(ev){
            var val = empresaField.value;
            // Si es un select con opción vacía, val puede ser ''
            loadAssignmentsForEmpresa(val);
        });
        // Si ya hay empresa seleccionada al cargar, forzar carga.
        if (empresaField.value) {
            loadAssignmentsForEmpresa(empresaField.value);
        }
    }
});
