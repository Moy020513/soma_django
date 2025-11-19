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

  function onCTZChange(){
    // Usamos únicamente el multi-select `ctzs`.
    var multi = document.getElementById('id_ctzs');
    if(multi){
      buildCTZRowsFromSelect(multi);
    }
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
    // If the admin uses filter_horizontal the chosen items live in a separate select
    // with suffix '_to' (e.g. id_ctzs_to). Use that select if present; otherwise
    // fall back to the original select's selectedOptions.
    var chosenSelect = document.getElementById(selectEl.id + '_to');
    var opts = [];
    if(chosenSelect && chosenSelect.options && chosenSelect.options.length > 0){
      // The _to select contains exactly the chosen items; use all its options.
      opts = Array.from(chosenSelect.options);
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
        // per-ctz total (readonly)
        var perTotal = document.createElement('input'); perTotal.type = 'number'; perTotal.step = '0.01'; perTotal.readOnly = true; perTotal.className = 'ctz-per-total'; perTotal.id = 'id_ctz_total_'+s.id;
        // small layout
        var layout = document.createElement('div');
        layout.appendChild(lbl);
        var inner = document.createElement('div'); inner.style.display='flex'; inner.style.gap='8px'; inner.style.marginTop='4px';
        var puWrap = document.createElement('div'); puWrap.appendChild(document.createTextNode('PU: ')); puWrap.appendChild(puInput);
        var qtyWrap = document.createElement('div'); qtyWrap.appendChild(document.createTextNode('Cantidad: ')); qtyWrap.appendChild(qtyInput);
        var totalWrap = document.createElement('div'); totalWrap.appendChild(document.createTextNode('Total: ')); totalWrap.appendChild(perTotal);
        inner.appendChild(puWrap); inner.appendChild(qtyWrap); inner.appendChild(totalWrap);
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
      }
    });
    // finally recompute totals
    computeAndSetTotals();
  }

  document.addEventListener('DOMContentLoaded', function(){
    // Inicializar comportamiento basado en el multi-select `ctzs`.
    var multi = document.getElementById('id_ctzs');
    if(multi){
      // construir filas si ya hay opciones seleccionadas
      buildCTZRowsFromSelect(multi);
      multi.addEventListener('change', function(){ buildCTZRowsFromSelect(multi); });
    }
  });

})();
