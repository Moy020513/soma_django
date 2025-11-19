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
    var puEl = document.getElementById('id_pu');
    var cantEl = document.getElementById('id_cantidad');
    var subtotalEl = document.getElementById('id_subtotal');
    var ivaEl = document.getElementById('id_iva');
    var totalEl = document.getElementById('id_total');
    if(!subtotalEl || !ivaEl || !totalEl) return;
    var pu = puEl ? parseNumber(puEl.value) : 0;
    var cantidad = cantEl ? parseNumber(cantEl.value) : 0;
    var subtotal = cantidad * pu;
    var iva = subtotal * 0.16;
    var total = subtotal + iva;
    // escribir con 2 decimales
    try{ subtotalEl.value = fmtNumber(subtotal); }catch(e){}
    try{ ivaEl.value = fmtNumber(iva); }catch(e){}
    try{ totalEl.value = fmtNumber(total); }catch(e){}
  }

  function onCTZChange(){
    var sel = document.getElementById('id_ctz');
    if(!sel) return;
    var val = sel.value;
    var puEl = document.getElementById('id_pu');
    if(!val){
      // si no hay selection, no hacemos nada
      return computeAndSetTotal();
    }
    // Construir URL relativa a admin; asumimos rutas: /admin/empresas/ctzformato/ctz-total-pu/<id>/
    var url = '/admin/empresas/ctzformato/ctz-total-pu/' + val + '/';
    fetch(url, {credentials: 'same-origin'})
      .then(function(resp){
        if(!resp.ok) throw new Error('network');
        return resp.json();
      })
      .then(function(data){
        if(data && (typeof data.total_pu !== 'undefined')){
          try{ if(puEl) puEl.value = data.total_pu; }catch(e){}
          computeAndSetTotal();
        }
      })
      .catch(function(err){
        // Silencioso: si falla la petición, no rompemos el formulario
        console && console.debug && console.debug('ctz_total_pu fetch failed', err);
      });
  }

  document.addEventListener('DOMContentLoaded', function(){
    var sel = document.getElementById('id_ctz');
    var puEl = document.getElementById('id_pu');
    var cantEl = document.getElementById('id_cantidad');
    // Recalcular al cambiar cantidad o pu
    if(cantEl) cantEl.addEventListener('input', computeAndSetTotals);
    if(puEl) puEl.addEventListener('input', computeAndSetTotals);
    if(sel){
      sel.addEventListener('change', onCTZChange);
      // si ya hay un valor seleccionado al cargar, solicitar el PU
      if(sel.value){
        onCTZChange();
        // además recalcular totales iniciales
        computeAndSetTotals();
      }
    }
  });

})();
