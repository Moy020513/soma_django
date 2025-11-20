(function(){
  // Pequeño script para el admin de CTZFormato:
  // - al seleccionar una CTZ, pide el total_pu (JSON) y lo copia en PU
  // - recalcula Total = Cantidad * PU al cambiar Cantidad o PU
  // Funciona tanto en formulario de add como change.

  function parseNumber(v){
    if(v === null || v === undefined) return 0;
    try{
      var s = String(v).trim();
      if(s === '') return 0;
      // aceptar coma decimal
      s = s.replace(',', '.');
      var f = parseFloat(s);
      return isNaN(f) ? 0 : f;
    }catch(e){return 0}
  }

  function fmtNumber(v){
    // Formateo simple con 2 decimales
    try{
      return parseFloat(v).toFixed(2);
    }catch(e){return v}
  }

  function computeAndSetTotals(){
    var subtotalEl = document.getElementById('id_subtotal');
    var ivaEl = document.getElementById('id_iva');
    var totalEl = document.getElementById('id_total');
    if(!subtotalEl || !ivaEl || !totalEl) return;
    // Si existen filas por CTZ (selección múltiple), sumar sus totales.
    var ctzRows = document.querySelectorAll('.ctz-row');
    var subtotal = 0;
    if(ctzRows && ctzRows.length){
      ctzRows.forEach(function(row){
        var perTotal = row.querySelector('.ctz-per-total');
        var v = perTotal ? parseNumber(perTotal.value) : 0;
        subtotal += v;
      });
    } else {
      // Fallback: usar campos únicos pu/cantidad
      var puEl = document.getElementById('id_pu');
      var cantEl = document.getElementById('id_cantidad');
      var pu = puEl ? parseNumber(puEl.value) : 0;
      var cantidad = cantEl ? parseNumber(cantEl.value) : 0;
      subtotal = cantidad * pu;
    }
    var iva = subtotal * 0.16;
    var total = subtotal + iva;
    // escribir con 2 decimales
    try{ subtotalEl.value = fmtNumber(subtotal); }catch(e){}
    try{ ivaEl.value = fmtNumber(iva); }catch(e){}
    try{ totalEl.value = fmtNumber(total); }catch(e){}
  }

  function findCTZSelect(){
    // Buscar de forma robusta el select asociado al campo M2M `ctzs`.
    // Puede presentarse como:
    // - #id_ctzs (sin filter_horizontal)
    // - select[name="ctzs"]
    // - #id_ctzs_from / #id_ctzs_to (filter_horizontal)
    var sel = document.getElementById('id_ctzs');
    if(sel) return sel;
    sel = document.querySelector('select[name="ctzs"]');
    if(sel) return sel;
    // buscar selects que terminen en _ctzs_to o _ctzs_from
    sel = document.querySelector('select[id$="_ctzs_to"]') || document.querySelector('select[id$="_ctzs_from"]');
    if(sel) return sel;
    // fallback: cualquier select cuyo id contenga 'ctzs'
    sel = document.querySelector('select[id*="ctzs"]');
    return sel;
  }

  function buildCTZRowsFromSelect(selectEl){
    var containerId = 'ctz_rows_container';
    var container = document.getElementById(containerId);
    if(!container){
      container = document.createElement('div');
      container.id = containerId;
      // insert after the select
      selectEl.parentNode.insertBefore(container, selectEl.nextSibling);
    }
    // determine selected ids
    // Prefer the explicit '_to' select used by Django's filter_horizontal.
    // If a _to select exists anywhere in the page for this field, use it
    // exclusively; otherwise fall back to the provided selectEl.selectedOptions.
    var chosenSelect = null;
    try{
      // First try to find any select that ends with '_ctzs_to' (robust for admin ids)
      chosenSelect = document.querySelector('select[id$="_ctzs_to"]');
      // If not found, and selectEl has an id, try the conventional id + '_to'
      if(!chosenSelect && selectEl && selectEl.id){
        chosenSelect = document.getElementById(selectEl.id + '_to');
      }
      // If selectEl itself *is* a _to select, respect it
      if(!chosenSelect && selectEl && selectEl.id && selectEl.id.endsWith('_to')){
        chosenSelect = selectEl;
      }
    }catch(e){ chosenSelect = null; }
    var opts = [];
    if(chosenSelect){
      // Use only the options in the _to select. This avoids creating rows when
      // the user merely clicks options in the "available" list on the left.
      opts = Array.from(chosenSelect.options || []);
    } else {
      // Fallback: use only the options that are actually selected in the original select.
      opts = Array.from(selectEl.selectedOptions || []);
    }
    var selected = opts.map(function(o){ return {id: o.value, text: o.text}; }).filter(function(s){ return s.id; });
    // remove rows for deselected
    var existingRows = container.querySelectorAll('.ctz-row');
    existingRows.forEach(function(r){
      var rid = r.getAttribute('data-ctz-id');
      if(!selected.find(function(s){return s.id === rid;})){
        r.remove();
      }
    });
    // add rows for newly selected
    selected.forEach(function(s){
      if(!container.querySelector('.ctz-row[data-ctz-id="'+s.id+'"]')){
        // create row
        var row = document.createElement('div');
        row.className = 'ctz-row';
        row.setAttribute('data-ctz-id', s.id);
        row.style.margin = '8px 0';
        // label
        var lbl = document.createElement('div'); lbl.textContent = s.text; lbl.style.fontWeight = '600';
        // pu (readonly)
        var puInput = document.createElement('input'); puInput.type = 'number'; puInput.step = '0.01'; puInput.readOnly = true; puInput.className = 'ctz-pu'; puInput.id = 'id_ctz_pu_'+s.id;
        // cantidad (editable)
        var qtyInput = document.createElement('input'); qtyInput.type = 'number'; qtyInput.step = '0.001'; qtyInput.value = '0'; qtyInput.className = 'ctz-qty'; qtyInput.id = 'id_ctz_qty_'+s.id; qtyInput.name = 'ctz_qty_'+s.id;
  // concepto específico por CTZ (editable)
  var conceptInput = document.createElement('input'); conceptInput.type = 'text'; conceptInput.className = 'ctz-concept'; conceptInput.id = 'id_ctz_concept_'+s.id; conceptInput.name = 'ctz_concept_'+s.id; conceptInput.placeholder = 'Concepto específico...'; conceptInput.style.minWidth = '180px';
    // unidad específica por CTZ
    var unitInput = document.createElement('input'); unitInput.type = 'text'; unitInput.className = 'ctz-unit'; unitInput.id = 'id_ctz_unit_'+s.id; unitInput.name = 'ctz_unit_'+s.id; unitInput.placeholder = 'Unidad'; unitInput.style.minWidth = '80px';
        // per-ctz total (readonly)
        var perTotal = document.createElement('input'); perTotal.type = 'number'; perTotal.step = '0.01'; perTotal.readOnly = true; perTotal.className = 'ctz-per-total'; perTotal.id = 'id_ctz_total_'+s.id;
        // small layout
        var layout = document.createElement('div');
        layout.appendChild(lbl);
  var inner = document.createElement('div'); inner.style.display='flex'; inner.style.gap='8px'; inner.style.marginTop='4px'; inner.style.alignItems='center';
  var puWrap = document.createElement('div'); puWrap.appendChild(document.createTextNode('PU: ')); puWrap.appendChild(puInput);
  var qtyWrap = document.createElement('div'); qtyWrap.appendChild(document.createTextNode('Cantidad: ')); qtyWrap.appendChild(qtyInput);
  var conceptWrap = document.createElement('div'); conceptWrap.appendChild(document.createTextNode('Concepto: ')); conceptWrap.appendChild(conceptInput);
  var unitWrap = document.createElement('div'); unitWrap.appendChild(document.createTextNode('Unidad: ')); unitWrap.appendChild(unitInput);
  var totalWrap = document.createElement('div'); totalWrap.appendChild(document.createTextNode('Total: ')); totalWrap.appendChild(perTotal);
  inner.appendChild(puWrap); inner.appendChild(qtyWrap); inner.appendChild(unitWrap); inner.appendChild(conceptWrap); inner.appendChild(totalWrap);
        layout.appendChild(inner);
        row.appendChild(layout);
        container.appendChild(row);
        // fetch PU value
        fetch('/admin/empresas/ctzformato/ctz-total-pu/'+s.id+'/', {credentials:'same-origin'})
          .then(function(r){ if(!r.ok) throw new Error('network'); return r.json(); })
          .then(function(data){ if(data && typeof data.total_pu !== 'undefined'){ puInput.value = fmtNumber(data.total_pu); // set initial
                // compute per-ctz total when pu known
                var qty = parseNumber(qtyInput.value || 0);
                perTotal.value = fmtNumber(qty * parseNumber(puInput.value));
                computeAndSetTotals();
            }})
          .catch(function(e){ console && console.debug && console.debug('fetch pu failed', e); });
        // recompute when cantidad changes
        qtyInput.addEventListener('input', function(){
          try{ perTotal.value = fmtNumber(parseNumber(qtyInput.value) * parseNumber(puInput.value)); }catch(e){}
          computeAndSetTotals();
        });
        // Optional: recompute totals when concept changes has no effect, but keep for future
        conceptInput.addEventListener('input', function(){ /* noop for now */ });
      }
    });
    // finally recompute totals
    computeAndSetTotals();
  }

  document.addEventListener('DOMContentLoaded', function(){
    // Inicializar comportamiento basado en el multi-select `ctzs`.
    var selectEl = findCTZSelect();
    if(selectEl){
      // construir filas si ya hay opciones seleccionadas
      buildCTZRowsFromSelect(selectEl);
      // Si estamos en la vista de cambio (URL contiene /ctzformato/<id>/change/),
      // pedir los detalles guardados vía AJAX y rellenar las filas dinámicas.
      try{
        var m = window.location.pathname.match(/\/admin\/empresas\/ctzformato\/(\d+)\/change\/?$/);
        if(m && m[1]){
          var formatoId = m[1];
          // esperar un poco para que el widget filter_horizontal esté inicializado
          setTimeout(function(){
            fetch('/admin/empresas/ctzformato/ctz-detalles/'+formatoId+'/', {credentials:'same-origin'})
              .then(function(r){ if(!r.ok) throw new Error('network'); return r.json(); })
              .then(function(data){
                if(!data || !data.detalles) return;
                data.detalles.forEach(function(d){
                  // Asegurarse de que la fila exista (buildCTZRowsFromSelect ya la creó si la CTZ está seleccionada)
                  var row = document.querySelector('.ctz-row[data-ctz-id="'+d.ctz_id+'"]');
                  if(!row){
                    // Forzar creación si por algún motivo no existe
                    buildCTZRowsFromSelect(selectEl);
                    row = document.querySelector('.ctz-row[data-ctz-id="'+d.ctz_id+'"]');
                  }
                  if(row){
                    try{ var qty = row.querySelector('.ctz-qty'); if(qty) qty.value = d.cantidad; }catch(e){}
                    try{ var concept = row.querySelector('.ctz-concept'); if(concept) concept.value = d.concepto; }catch(e){}
                    try{ var unit = row.querySelector('.ctz-unit'); if(unit) unit.value = d.unidad; }catch(e){}
                    try{ var pu = row.querySelector('.ctz-pu'); if(pu) pu.value = fmtNumber(d.pu); }catch(e){}
                    try{ var per = row.querySelector('.ctz-per-total'); if(per) per.value = fmtNumber(d.total); }catch(e){}
                  }
                });
                computeAndSetTotals();
              })
              .catch(function(e){ console && console.debug && console.debug('fetch detalles failed', e); });
          }, 60);
        }
      }catch(e){}
      // Intentar escuchar cambios en el select "elegidos" (_to) o en el propio select
      var chosen = document.getElementById(selectEl.id + '_to') || selectEl;
      try{
        chosen.addEventListener('change', function(){ buildCTZRowsFromSelect(selectEl); });
      }catch(e){}

      // Usar MutationObserver para detectar movimientos entre columnas (filter_horizontal)
      try{
        var observer = new MutationObserver(function(){ buildCTZRowsFromSelect(selectEl); });
        observer.observe(chosen, { childList: true });
      }catch(e){}

      // También reconstruir después de clicks en controles del selector (por si no se disparan events de change)
      document.addEventListener('click', function(e){
        var t = e.target || e.srcElement;
        if(!t) return;
        // detectar botones/link del widget selector (clases que usa Django admin)
        if(t.classList && (t.classList.contains('selector-add') || t.classList.contains('selector-remove') || t.classList.contains('selector-chooser'))){
          setTimeout(function(){ buildCTZRowsFromSelect(selectEl); }, 50);
        }
      }, true);
    }
  });

})();
