(function(){
  function parseIntSafe(v){
    var n = parseInt(String(v||'').replace(/[^0-9-]/g,''), 10);
    return isNaN(n)?0:n;
  }
  function parseFloatSafe(v){
    var n = parseFloat(String(v||'').replace(/,/g,'.'));
    return isNaN(n)?0:n;
  }
  function _getField(id, name){
    var el = document.getElementById(id);
    if(el) return el;
    // try by name
    el = document.querySelector('[name="' + (name||id.replace(/^id_/,'')) + '"]');
    if(el) return el;
    // try readonly display
    el = document.querySelector('#' + id + ', .readonly, p.field-'+(name||id.replace(/^id_/,'')));
    return el;
  }

  function _setFieldValue(el, val){
    if(!el) return;
    try{
      if('value' in el){ el.value = val; }
      else { el.textContent = String(val); }
    }catch(e){
      try{ el.textContent = String(val); }catch(e){}
    }
  }

  function compute(){
    var prov = parseIntSafe((_getField('id_proveedor')||{}).value);
    var mo = parseIntSafe((_getField('id_mo_soma')||{}).value);
    var otros = parseIntSafe((_getField('id_otros_materiales')||{}).value);
    var pct = parseFloatSafe((_getField('id_porcentaje_pu')||{}).value);
    var pu = prov + mo + otros;
    var total = Math.round(pu * (pct || 1));
    var el_pu = _getField('id_pu','pu');
    var el_total = _getField('id_total_pu','total_pu');
    _setFieldValue(el_pu, pu);
    _setFieldValue(el_total, total);
  }
  function init(){
    ['id_proveedor','id_mo_soma','id_otros_materiales','id_porcentaje_pu'].forEach(function(id){
      var el = _getField(id);
      if(el && ('addEventListener' in el)){
        el.addEventListener('input', compute);
        el.addEventListener('change', compute);
      }
    });
    // compute once on load
    compute();
  }
  document.addEventListener('DOMContentLoaded', init);
})();
