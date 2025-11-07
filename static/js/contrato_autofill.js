document.addEventListener('DOMContentLoaded', function() {
    var select = document.querySelector('select[name="asignaciones_vinculadas"]');
    if (!select) return;

    var infoUrl = select.dataset.assignmentsInfoUrl;
    if (!infoUrl) {
        try {
            var loc = window.location.pathname;
            loc = loc.replace(/\/(add|change\/\d+)\/?$/, '/');
            if (!loc.endsWith('/')) loc += '/';
            infoUrl = loc + 'assignments-info/';
        } catch (e) {
            infoUrl = null;
        }
    }

    var empresaField = document.querySelector('#id_empresa');
    var cantidadField = document.querySelector('#id_cantidad_empleados');
    var fechaInicioField = document.querySelector('#id_fecha_inicio');
    var fechaTerminoField = document.querySelector('#id_fecha_termino');

    function clearFields() {
        if (cantidadField) cantidadField.value = '';
        if (fechaInicioField) fechaInicioField.value = '';
        if (fechaTerminoField) fechaTerminoField.value = '';
    }

    function setEmpresaValue(id, label) {
        if (!empresaField) return;
        try {
            if (empresaField.tagName.toLowerCase() === 'select') {
                var opt = empresaField.querySelector('option[value="' + String(id) + '"]');
                if (!opt) {
                    opt = document.createElement('option');
                    opt.value = String(id);
                    opt.text = label || String(id);
                    empresaField.appendChild(opt);
                }
                empresaField.value = String(id);
            } else {
                empresaField.value = label || String(id);
            }
            empresaField.dispatchEvent(new Event('change'));
        } catch (e) {
            // ignore
        }
    }

    function updateFromSelection() {
        var container = select.closest && select.closest('.selector') ? select.closest('.selector') : select.parentNode;
        var selectsInWidget = container.querySelectorAll('select');
        var chosenSelect = container.querySelector('select.selector-chosen') || container.querySelector('select.chosen') || (selectsInWidget.length > 1 ? selectsInWidget[1] : selectsInWidget[0]);
        if (!chosenSelect) {
            clearFields();
            return;
        }
        var selectedOpts = Array.from(chosenSelect.options).filter(function(o){ return o && o.value; });
        if (selectedOpts.length === 0) {
            clearFields();
            return;
        }

        var haveMeta = selectedOpts.every(function(o){ return o.dataset && ('fecha' in o.dataset); });
        if (haveMeta) {
            var fechas = selectedOpts.map(function(o){ return o.dataset.fecha; }).filter(Boolean).map(function(s){ return new Date(s); });
            var minFecha = null;
            if (fechas.length) minFecha = new Date(Math.min.apply(null, fechas));
            var fechasCompletadas = selectedOpts.filter(function(o){ return o.dataset && (o.dataset.completada === 'true' || o.dataset.completada === '1'); }).map(function(o){ return o.dataset.fecha; }).filter(Boolean).map(function(s){ return new Date(s); });
            var maxFechaCompletada = null;
            if (fechasCompletadas.length) maxFechaCompletada = new Date(Math.max.apply(null, fechasCompletadas));
            var empresaId = selectedOpts.map(function(o){ return o.dataset.empresaId; }).filter(Boolean)[0];
            var empresaLabel = selectedOpts.map(function(o){ return o.dataset.empresaNombre; }).filter(Boolean)[0];
            if (empresaField && empresaId) setEmpresaValue(empresaId, empresaLabel || empresaId);
            if (cantidadField) cantidadField.value = selectedOpts.reduce(function(sum, o){ var v = parseInt(o.dataset.empleados || '0', 10); return sum + (isNaN(v)?0:v); }, 0);
            if (fechaInicioField) fechaInicioField.value = minFecha ? minFecha.toISOString().slice(0,10) : '';
            if (fechaTerminoField) fechaTerminoField.value = maxFechaCompletada ? maxFechaCompletada.toISOString().slice(0,10) : '';
            return;
        }

        if (!infoUrl) return;
        var q = infoUrl + '?ids=' + selectedOpts.map(function(o){ return o.value; }).join(',');
        fetch(q, { credentials: 'same-origin' })
            .then(function(resp){ return resp.json(); })
            .then(function(data){
                if (!data || !data.ok) return;
                if (empresaField) {
                    if (data.empresa_id) setEmpresaValue(data.empresa_id, data.empresa || String(data.empresa_id));
                    else if (empresaField.tagName.toLowerCase() === 'input') { empresaField.value = data.empresa || ''; empresaField.dispatchEvent(new Event('change')); }
                }
                if (cantidadField) cantidadField.value = data.total_emps || '';
                if (fechaInicioField) fechaInicioField.value = data.fecha_inicio || '';
                if (fechaTerminoField) fechaTerminoField.value = data.fecha_termino || '';
            }).catch(function(){ /* ignore */ });
    }

    function loadAssignmentsForEmpresa(empresaId) {
        if (!empresaId) {
            select.innerHTML = '';
            select.dispatchEvent(new Event('change'));
            return;
        }
        if (!infoUrl) return;
        var q = infoUrl + '?empresa_id=' + encodeURIComponent(empresaId);
        fetch(q, { credentials: 'same-origin' })
            .then(function(resp){ return resp.json(); })
            .then(function(data){
                if (!data || !data.ok) return;
                var assignments = data.assignments || [];
                var selected = new Set(Array.from(select.selectedOptions).map(function(o){ return o.value; }));
                select.innerHTML = '';
                assignments.forEach(function(a){
                    var opt = document.createElement('option');
                    opt.value = String(a.pk);
                    var text = a.numero_cotizacion !== null && a.numero_cotizacion !== undefined ? String(a.numero_cotizacion) : '(sin cot)';
                    opt.text = text;
                    if (a.fecha) opt.dataset.fecha = a.fecha;
                    if (typeof a.completada !== 'undefined') opt.dataset.completada = a.completada ? 'true' : 'false';
                    if (a.empresa_id) opt.dataset.empresaId = a.empresa_id;
                    if (a.empresa_nombre) opt.dataset.empresaNombre = a.empresa_nombre;
                    if (typeof a.empleados !== 'undefined') opt.dataset.empleados = String(a.empleados);
                    if (selected.has(String(a.pk))) opt.selected = true;
                    select.appendChild(opt);
                });
                select.dispatchEvent(new Event('change'));
            }).catch(function(){ /* ignore */ });
    }

    var container = select.closest && select.closest('.selector') ? select.closest('.selector') : select.parentNode;
    var selectsInWidget = container.querySelectorAll('select');
    selectsInWidget.forEach(function(s){ s.addEventListener('change', updateFromSelection); });

    function debounce(fn, wait) { var t; return function() { var args = arguments; clearTimeout(t); t = setTimeout(function(){ fn.apply(null, args); }, wait); }; }
    var debouncedUpdate = debounce(updateFromSelection, 120);
    try {
        var mo = new MutationObserver(function(mutations){
            for (var i=0;i<mutations.length;i++){ var m = mutations[i]; if (m.type === 'childList'){ debouncedUpdate(); break; } }
        });
        mo.observe(container, { childList: true, subtree: true });
    } catch (e) { /* ignore */ }

    updateFromSelection();

    if (empresaField) {
        empresaField.addEventListener('change', function(){
            var val = empresaField.value;
            if (!val || val === '') {
                var hidden = document.querySelector('input[name="empresa"]') || document.querySelector('input[id^="id_empresa_"]');
                if (hidden && hidden.value) val = hidden.value;
            }
            loadAssignmentsForEmpresa(val);
        });
        var initialVal = empresaField.value || (document.querySelector('input[name="empresa"]') && document.querySelector('input[name="empresa"]').value) || '';
        if (initialVal) loadAssignmentsForEmpresa(initialVal);
    }
});
