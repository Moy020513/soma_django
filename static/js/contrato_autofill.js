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

    // FilteredSelectMultiple creates two select boxes; but the original select still dispatches change events.
    select.addEventListener('change', updateFromSelection);
    // Initialize on load
    updateFromSelection();
});
