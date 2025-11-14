/* CTZ admin helpers
   - Moves the CTZItem inline near the Costos fieldset
   - Adds per-field "Agregar ítem" buttons
*/
(function(){
  // Signal load for debugging
  try{ console && console.log && console.log('ctz_admin.js loaded'); }catch(e){}

  // Hide the visual inline module(s) whose header mentions Ítems CTZ to avoid duplicate UI
  function hideInlineModulesVisual(){
    try{
      var modules = Array.prototype.slice.call(document.querySelectorAll('div.module, div.inline-group, div.inline-related'));
      for(var i=0;i<modules.length;i++){
        var h2 = modules[i].querySelector('h2');
        var txt = h2 && h2.textContent ? h2.textContent.trim().toLowerCase() : '';
        if(/ítem|ítems|items/i.test(txt)){
          // keep the DOM nodes (ManagementForm inputs) but hide the visible block to the user
          try{ modules[i].style.display = 'none'; }catch(e){}
        }
      }
    }catch(e){/* no-op */}
  }

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
    el = document.querySelector('[name="' + (name||id.replace(/^id_/,'')) + '"]');
    if(el) return el;
    el = document.querySelector('#' + id + ', .readonly, p.field-'+(name||id.replace(/^id_/,'')));
    return el;
  }

  function _setFieldValue(el, val){
    if(!el) return;
    try{ if('value' in el) el.value = val; else el.textContent = String(val); }catch(e){ try{ el.textContent = String(val); }catch(e){} }
  }

  function compute(){
    function sumField(name){
      var base = parseFloatSafe((_getField('id_' + name)||{}).value);
      var extras = 0;
      try{
        var list = document.querySelector('.ctz-visible-list[data-ctz-owner="'+name+'"]');
        if(list){
          var nodes = list.querySelectorAll('.ctz-visible-cantidad');
          for(var i=0;i<nodes.length;i++) extras += parseFloatSafe(nodes[i].value);
        }
      }catch(e){}
      return base + extras;
    }
    var prov = sumField('proveedor');
    var mo = sumField('mo_soma');
    var otros = sumField('otros_materiales');
    var pct = parseFloatSafe((_getField('id_porcentaje_pu')||{}).value);
    var pu = prov + mo + otros;
    var total = Math.round(pu * (pct || 1));
    _setFieldValue(_getField('id_pu','pu'), pu);
    _setFieldValue(_getField('id_total_pu','total_pu'), total);
  }

  function init(){
    console && console.log && console.log('ctz_admin: init');
    // Attempt to detect admin change/add form robustly. Some admin themes or custom templates
    // may not include an input[name="_save"], so try multiple heuristics:
    var isAdminForm = false;
    try{
      if(document.querySelector('form input[name="_save"]')) isAdminForm = true;
      if(document.getElementById('id_empresa') || document.getElementById('id_proveedor') || document.getElementById('id_mo_soma')) isAdminForm = true;
      if(window.location && typeof window.location.pathname === 'string' && /\/admin\/.+\/ctz\//i.test(window.location.pathname)) isAdminForm = true;
      // fieldset header heuristic (Costos)
      var modules = Array.prototype.slice.call(document.querySelectorAll('div.module, fieldset'));
      for(var mi=0; mi<modules.length && !isAdminForm; mi++){ var h2 = modules[mi].querySelector && (modules[mi].querySelector('h2') || modules[mi].querySelector('legend')); var txt = h2 && h2.textContent ? h2.textContent.trim().toLowerCase() : ''; if(txt.indexOf('costos') !== -1) isAdminForm = true; }
    }catch(e){ isAdminForm = false; }
    if(!isAdminForm){ console && console.log && console.log('ctz_admin: not on admin change form (heuristics failed), aborting init'); return; }
    // hide visual inline modules early in init to avoid flicker
    try{ hideInlineModulesVisual(); }catch(e){}
    ['id_proveedor','id_mo_soma','id_otros_materiales','id_porcentaje_pu'].forEach(function(id){
      var el = _getField(id);
      if(el && ('addEventListener' in el)){
        el.addEventListener('input', compute);
        el.addEventListener('change', compute);
      }
    });
    compute();

  // now setup per-field add buttons (do NOT move the inline module to avoid flicker or removing ManagementForm)
  setupAddButtons();
    // ensure ManagementForm for items exists before submit (defensive patch)
    try{
      // prefer the admin change form: one containing the save button, else first form
      var adminForm = document.querySelector('form input[name="_save"]') ? document.querySelector('form input[name="_save"]').form : document.querySelector('form');
      function ensureItemsManagementForm(){
        try{
          var prefix = 'items';
          if(!adminForm) return;
          // If any inputs with the prefix exist elsewhere in the document, move them into the form
          var allPrefixed = Array.prototype.slice.call(document.querySelectorAll('input[name^="' + prefix + '-"]'));
          for(var i=0;i<allPrefixed.length;i++){ try{ var el = allPrefixed[i]; if(el && el.form !== adminForm){ adminForm.appendChild(el); } }catch(e){} }
          var totalInput = adminForm.querySelector('input[name="' + prefix + '-TOTAL_FORMS"]');
          var initialInput = adminForm.querySelector('input[name="' + prefix + '-INITIAL_FORMS"]');
          var minInput = adminForm.querySelector('input[name="' + prefix + '-MIN_NUM_FORMS"]');
          var maxInput = adminForm.querySelector('input[name="' + prefix + '-MAX_NUM_FORMS"]');
          // discover rows in any inline group that looks like CTZItem
          var inlineGroup = document.querySelector('[id*="ctzitem"]') || document.querySelector('.inline-group') || document.querySelector('.inline-related');
          var rows = [];
          if(inlineGroup){ rows = inlineGroup.querySelectorAll('.inline-related'); if(!rows || rows.length === 0) rows = inlineGroup.querySelectorAll('tr'); }
          var count = (rows && rows.length) ? rows.length : 0;
          // try to compute initial (existing objects) by checking for inputs with name like items-<i>-id and non-empty value
          var initialCount = 0;
          try{
            for(var ri=0; ri<rows.length; ri++){
              var r = rows[ri]; var idInput = r.querySelector('input[name$="-id"]'); if(idInput && idInput.value) initialCount += 1;
            }
          }catch(e){}
          if(!totalInput){ totalInput = document.createElement('input'); totalInput.type = 'hidden'; totalInput.name = prefix + '-TOTAL_FORMS'; totalInput.value = String(count); adminForm.appendChild(totalInput); }
          else { totalInput.value = String(count); }
          if(!initialInput){ initialInput = document.createElement('input'); initialInput.type = 'hidden'; initialInput.name = prefix + '-INITIAL_FORMS'; initialInput.value = String(initialCount); adminForm.appendChild(initialInput); }
          else { initialInput.value = String(initialCount); }
          if(!minInput){ minInput = document.createElement('input'); minInput.type = 'hidden'; minInput.name = prefix + '-MIN_NUM_FORMS'; minInput.value = '0'; adminForm.appendChild(minInput); }
          if(!maxInput){ maxInput = document.createElement('input'); maxInput.type = 'hidden'; maxInput.name = prefix + '-MAX_NUM_FORMS'; maxInput.value = '1000'; adminForm.appendChild(maxInput); }
        }catch(e){ console && console.warn && console.warn('ctz_admin: ensureItemsManagementForm error', e); }
      }
      try{
        ensureItemsManagementForm();
        adminForm.addEventListener && adminForm.addEventListener('submit', ensureItemsManagementForm, true);
        // Extra aggressive submit-time snapshot + injection to help diagnose missing ManagementForm fields.
        adminForm.addEventListener && adminForm.addEventListener('submit', function(ev){
          try{
            var prefix = 'items';
            // ensure the management inputs exist and are enabled
            var totalInput = adminForm.querySelector('input[name="' + prefix + '-TOTAL_FORMS"]');
            var initialInput = adminForm.querySelector('input[name="' + prefix + '-INITIAL_FORMS"]');
            if(totalInput && totalInput.disabled){ totalInput.disabled = false; }
            if(initialInput && initialInput.disabled){ initialInput.disabled = false; }
            if(!totalInput){ totalInput = document.createElement('input'); totalInput.type = 'hidden'; totalInput.name = prefix + '-TOTAL_FORMS'; totalInput.value = '0'; adminForm.appendChild(totalInput); }
            if(!initialInput){ initialInput = document.createElement('input'); initialInput.type = 'hidden'; initialInput.name = prefix + '-INITIAL_FORMS'; initialInput.value = '0'; adminForm.appendChild(initialInput); }

            // Snapshot what will actually be sent for items-* keys
                try{
                  // Before snapshot, serialize visible inputs per owner into hidden inputs named ctz_items_<owner>
                  var owners = ['proveedor','mo_soma','otros_materiales'];
                  owners.forEach(function(owner){
                    // remove previous injected fields to avoid duplicates
                    try{ var prev = adminForm.querySelectorAll('input[name="ctz_items_' + owner + '"]'); for(var pi=0; pi<prev.length; pi++){ prev[pi].parentNode.removeChild(prev[pi]); } }catch(e){}
                    var vis = document.querySelectorAll('.ctz-visible-list[data-ctz-owner="'+owner+'"] .ctz-visible-cantidad');
                    var injectedCount = 0;
                    var injectedValues = [];
                    for(var vi=0; vi<vis.length; vi++){
                      try{
                        var v = String(vis[vi].value || '').trim();
                        if(!v) continue; // skip empty inputs
                        var h = document.createElement('input'); h.type = 'hidden'; h.name = 'ctz_items_' + owner; h.value = v; adminForm.appendChild(h);
                        injectedCount += 1;
                        injectedValues.push(v);
                      }catch(e){}
                    }
                    // submit-injected count for ctz_items_<owner> (silent)
                  });
                  var fd = new FormData(adminForm);
                  var keys = [];
                  for(var k of fd.keys()){ if(String(k).indexOf(prefix + '-') === 0) keys.push(k); }
                }catch(e){ console && console.warn && console.warn('ctz_admin: FormData snapshot failed', e); }
          }catch(e){ console && console.warn && console.warn('ctz_admin: submit-time ensure error', e); }
        }, true);
      }catch(e){}
    }catch(e){}
  }

  function setupAddButtons(){
    var costFields = [
      {name: 'proveedor', tipo: 'proveedor'},
      {name: 'mo_soma', tipo: 'mo_soma'},
      {name: 'otros_materiales', tipo: 'otros_materiales'}
    ];

    function findFieldWrapper(fieldName){
      // Robust discovery of the field wrapper across many admin themes/layouts.
      try{
        // 1) direct id
        var el = document.getElementById('id_' + fieldName);
        if(el){ var wrap = el.closest && (el.closest('p') || el.closest('.form-row') || el.closest('.field') || el.closest('div')) ; if(wrap) return wrap; return el.parentNode || el; }
        // 2) by name attribute (fallback)
        el = document.querySelector('[name="' + fieldName + '"]') || document.querySelector('input[name$="-' + fieldName + '"]');
        if(el){ var wrap2 = el.closest && (el.closest('p') || el.closest('.form-row') || el.closest('.field') || el.closest('div')); if(wrap2) return wrap2; return el.parentNode || el; }
        // 3) label[for=..]
        var lbl = document.querySelector('label[for="id_' + fieldName + '"]');
        if(lbl){ var wrap3 = lbl.closest && (lbl.closest('p') || lbl.closest('div') || lbl.closest('td') || lbl.closest('tr')); if(wrap3) return wrap3; return lbl.parentNode || lbl; }
        // 4) generic label text matching (localized)
        var labels = Array.prototype.slice.call(document.querySelectorAll('label'));
        var needle = fieldName.replace('_',' ');
        for(var i=0;i<labels.length;i++){
          var t = labels[i].textContent && labels[i].textContent.trim(); if(!t) continue; var lowered = t.toLowerCase();
          if(lowered.indexOf(needle.replace('_',' ')) !== -1 || lowered.indexOf(fieldName.replace('_',' ')) !== -1){ var wrap4 = labels[i].closest && (labels[i].closest('p') || labels[i].closest('div') || labels[i].closest('td') || labels[i].parentNode); if(wrap4) return wrap4; }
        }
        // 5) fallback: place into the 'Costos' fieldset/module if present
        var modules = Array.prototype.slice.call(document.querySelectorAll('div.module, fieldset'));
        for(var mi=0; mi<modules.length; mi++){
          var h2 = modules[mi].querySelector('h2, legend');
          var txt = h2 && h2.textContent ? h2.textContent.trim().toLowerCase() : '';
          if(txt.indexOf('costos') !== -1){ return modules[mi]; }
        }
      }catch(e){ /* ignore */ }
      // degrade silently (avoid noisy warnings in console) and return null so caller can handle placement
      return null;
    }

    function createVisibleCantidad(wrapper, inlineRow, fieldName){
      try{
        if(!inlineRow || !fieldName) return null;
        var qtyOrig = inlineRow.querySelector('input[name$="-cantidad"]') || inlineRow.querySelector('input[type="number"]') || inlineRow.querySelector('input[type="text"]');
        if(!qtyOrig) { console && console.warn && console.warn('ctz_admin: cantidad input not found in inlineRow'); return null; }
        var wrapperTarget = wrapper || findFieldWrapper(fieldName) || document.body;
  var list = wrapperTarget.querySelector('.ctz-visible-list[data-ctz-owner="'+fieldName+'"]');
  if(!list){ list = document.createElement('div'); list.className = 'ctz-visible-list'; list.setAttribute('data-ctz-owner', fieldName); list.style.marginTop = '6px'; if(wrapperTarget.nextSibling) wrapperTarget.parentNode.insertBefore(list, wrapperTarget.nextSibling); else wrapperTarget.parentNode.appendChild(list); }
        var uid = String(Date.now()) + '-' + Math.floor(Math.random()*1000);
        var vis = document.createElement('input'); vis.type = 'number'; vis.step = 'any'; vis.className = 'ctz-visible-cantidad'; vis.setAttribute('data-ctz-field', fieldName); vis.setAttribute('data-ctz-uid', uid); vis.style.display = 'inline-block'; vis.style.width = '160px'; vis.style.marginRight = '6px'; vis.value = qtyOrig.value || '';
        try{ qtyOrig.type = 'hidden'; }catch(e){ qtyOrig.style.display = 'none'; }
        try{ inlineRow.style.display = 'none'; }catch(e){}
        // keep a tight binding: only update the matching qtyOrig in this inlineRow by uid
        vis.addEventListener('input', function(){
          try{
            var myuid = vis.getAttribute('data-ctz-uid');
            if(myuid && inlineRow){
              var matched = inlineRow.querySelector('input[data-ctz-uid="'+myuid+'"]');
              if(matched) matched.value = vis.value;
            }
          }catch(e){}
          try{ compute(); }catch(e){}
        });
        // mark the original qty input with the uid so pairing works
        try{ qtyOrig.setAttribute && qtyOrig.setAttribute('data-ctz-uid', uid); }catch(e){}
        list.appendChild(vis);
        return vis;
      }catch(e){ console && console.warn && console.warn('ctz_admin: createVisibleCantidad error', e); return null; }
    }

    function insertAddButton(fieldName, tipo){
      // avoid inserting multiple buttons for the same field globally
      if(document.querySelector('.ctz-add-btn[data-ctz-field="' + fieldName + '"]')) return;
      var wrapper = findFieldWrapper(fieldName);
      var modules = Array.prototype.slice.call(document.querySelectorAll('div.module, div.inline-group, div.inline-related'));
      var target = null; for(var i=0;i<modules.length;i++){ var h2 = modules[i].querySelector('h2'); var txt = h2 && h2.textContent ? h2.textContent.trim() : ''; if(!target && txt.indexOf('Costos') === 0) target = modules[i]; }
  // silent when wrapper not found to avoid noisy console output in production
      // avoid duplicate inside wrapper (extra safety)
  if(wrapper && wrapper.querySelector('.ctz-add-btn')) return;
      var a = document.createElement('a');
      a.href = '#';
      a.className = 'ctz-add-btn';
      a.textContent = '\u2795 Agregar ítem';
      a.style.display = 'inline-block';
      a.style.marginTop = '6px';
      a.style.marginBottom = '6px';
      a.style.fontSize = '90%';
      a.style.color = '#0b62a4';
      a.setAttribute('data-ctz-field', fieldName);
      var processing = false;
      // helper: deterministic clone insertion of a new inline row
      function tryCloneInsert(localInlineGroup){
        try{
          var inlineGroup = localInlineGroup || document.getElementById('ctzitem_set-group') || document.querySelector('[id*="ctzitem"]') || document.querySelector('.inline-group') || document.querySelector('.inline-related');
          var totalInput = inlineGroup && (inlineGroup.querySelector('input[name$="-TOTAL_FORMS"]') || inlineGroup.querySelector('input[name$="TOTAL_FORMS"]')) || document.querySelector('input[name$="-TOTAL_FORMS"]');
          var rows = inlineGroup ? Array.prototype.slice.call(inlineGroup.querySelectorAll('.inline-related')) : [];
          if(rows.length === 0) rows = inlineGroup ? Array.prototype.slice.call(inlineGroup.querySelectorAll('tr')) : [];
          if(rows.length === 0) return null;
          var last = rows[rows.length-1];
          var newIndex = totalInput ? parseInt(totalInput.value,10) : rows.length;
          var clone = last.cloneNode(true);
          var elems = clone.querySelectorAll('*');
          for(var i=0;i<elems.length;i++){
            var el = elems[i];
            if(el.name) el.name = el.name.replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex);
            if(el.id) el.id = el.id.replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex);
            if(el.getAttribute && el.getAttribute('for')) el.setAttribute('for', el.getAttribute('for').replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex));
            if(el.tagName === 'INPUT'){ if(el.type === 'checkbox' || el.type === 'radio') el.checked = false; else el.value = ''; }
            if(el.tagName === 'SELECT') el.selectedIndex = 0;
            if(el.tagName === 'TEXTAREA') el.value = '';
          }
          if(last.parentNode) last.parentNode.insertBefore(clone, last.nextSibling);
          if(totalInput) totalInput.value = (newIndex + 1).toString();
          var sel = clone.querySelector('select[name$="-tipo"]') || clone.querySelector('select');
          if(sel){
            for(var j=0;j<sel.options.length;j++){ var o = sel.options[j]; if(String(o.value).toLowerCase() === tipo.toLowerCase() || String(o.text).toLowerCase().indexOf(tipo.toLowerCase()) !== -1){ sel.selectedIndex = j; break; } }
          }
          return clone;
        }catch(e){ console && console.warn && console.warn('ctz_admin: tryCloneInsert failed', e); return null; }
      }
      a.addEventListener('click', function(ev){
        ev.preventDefault();
        // small helper to clear locks on any early exit
        function _unlock(){ try{ processing = false; window.__ctz_add_processing = false; }catch(e){} }
        // global guard to avoid concurrent handling across multiple buttons/listeners
        try{ if(window.__ctz_add_processing){ console && console.log && console.log('ctz_admin: global lock active, ignoring click'); return; } }catch(e){}
        if(processing) { _unlock(); return; }
        processing = true;
        try{ window.__ctz_add_processing = true; }catch(e){}
        // resolve admin add-link: prefer the inline module whose header mentions ítem/ítems and use its add-row
        var moduleNode = null;
        try{
          var modulesForScan = Array.prototype.slice.call(document.querySelectorAll('div.module, div.inline-group, div.inline-related'));
          for(var mi=0; mi<modulesForScan.length; mi++){ var h2 = modulesForScan[mi].querySelector('h2'); var txt = h2 && h2.textContent ? h2.textContent.trim() : ''; if(/ítem|ítems|items/i.test(txt)){ moduleNode = modulesForScan[mi]; break; } }
        }catch(e){}
        var localAddLink = (moduleNode && (moduleNode.querySelector('a.add-row') || moduleNode.querySelector('a'))) || document.querySelector('.inline-group a.add-row') || document.querySelector('a.add-row');
        // determine inline group root for detection
        var localInlineGroup = moduleNode || (localAddLink ? (localAddLink.closest('.inline-group') || localAddLink.closest('[id*="ctzitem"]') || document.getElementById('ctzitem_set-group')) : (document.getElementById('ctzitem_set-group') || document.querySelector('[id*="ctzitem"]') || document.querySelector('.inline-group') || document.querySelector('.inline-related')));
        console && console.log && console.log('ctz_admin: click handler resolved inlineGroup', !!localInlineGroup, 'addLink', !!localAddLink);

        // If there's no inline formset rendered (we removed it server-side),
        // create a standalone visible cantidad input that updates the main field value.
        if(!localInlineGroup){
          try{
            var wrapperTarget = findFieldWrapper(fieldName) || wrapper || document.body;
            // create a standalone visible input list if not exists
            var list = wrapperTarget.querySelector('.ctz-visible-list[data-ctz-owner="'+fieldName+'"]');
            if(!list){ list = document.createElement('div'); list.className = 'ctz-visible-list'; list.setAttribute('data-ctz-owner', fieldName); list.style.marginTop = '6px'; if(wrapperTarget.nextSibling) wrapperTarget.parentNode.insertBefore(list, wrapperTarget.nextSibling); else wrapperTarget.parentNode.appendChild(list); }
            // create input with remove button
            var uid = String(Date.now()) + '-' + Math.floor(Math.random()*1000);
            var vis = document.createElement('input'); vis.type = 'number'; vis.step = 'any'; vis.className = 'ctz-visible-cantidad'; vis.setAttribute('data-ctz-field', fieldName); vis.setAttribute('data-ctz-uid', uid); vis.style.display = 'inline-block'; vis.style.width = '160px'; vis.style.marginRight = '6px'; vis.value = '';
            var rem = document.createElement('button'); rem.type = 'button'; rem.textContent = '✖'; rem.title = 'Eliminar ítem'; rem.style.marginRight = '8px'; rem.addEventListener('click', function(){ try{ if(vis.parentNode===list) list.removeChild(vis); if(rem.parentNode===list) list.removeChild(rem); _recomputeField(fieldName); }catch(e){} });
            vis.addEventListener('input', function(){ try{ _recomputeField(fieldName); }catch(e){} });
            list.appendChild(vis); list.appendChild(rem); vis.focus();
            // recompute sums into main field
            function _recomputeField(fn){ try{ var inputs = (list.querySelectorAll('.ctz-visible-cantidad[data-ctz-field="'+fn+'"]')||[]); var sum = 0; for(var ii=0; ii<inputs.length; ii++){ var v = parseFloat(inputs[ii].value); if(!isNaN(v)) sum += v; } // intentionally DO NOT update the main field here; visible inputs are independent
              try{ compute(); }catch(e){} }catch(e){} }
            _unlock();
            return;
          }catch(e){}
        }

  if(localAddLink){
          // Prefer a deterministic clone-first insertion to avoid triggering admin add-link listeners which
          // in some setups produce duplicate insertions. If clone works, use it and skip dispatching the admin add-link.
          var cloned = tryCloneInsert(localInlineGroup);
          if(cloned){
            try{ var wrapperTarget = findFieldWrapper(fieldName) || wrapper; createVisibleCantidad(wrapperTarget, cloned, fieldName); compute(); try{ var qty = cloned.querySelector('input[name$="-cantidad"]'); if(qty) qty.focus(); }catch(e){} _unlock(); return; }catch(e){}
          }
          // observe for added nodes
          var detectRoot = localInlineGroup || document;
          var detectNode = localInlineGroup || document.body;
          var initialCount = (detectRoot.querySelectorAll('select[name$="-tipo"]')||[]).length;
          console && console.log && console.log('ctz_admin: waiting for new inline, initialCount=', initialCount);
          var handled = false;
          var obs = null;
          try{
            if(window.MutationObserver){
              obs = new MutationObserver(function(mutations){
                if(handled) return;
                for(var mi=0; mi<mutations.length; mi++){
                  var m = mutations[mi]; if(!m.addedNodes || !m.addedNodes.length) continue;
                  for(var an=0; an<m.addedNodes.length; an++){
                    var node = m.addedNodes[an]; try{
                      var sel = null;
                      if(node.nodeType === 1){ if(node.matches && node.matches('select[name$="-tipo"]')) sel = node; else sel = node.querySelector && node.querySelector('select[name$="-tipo"]'); }
                      if(sel){ handled = true; try{ obs.disconnect(); }catch(e){} console && console.log && console.log('ctz_admin: MutationObserver detected new select (by mutation)');
                        for(var i=0;i<sel.options.length;i++){ var opt = sel.options[i]; if(String(opt.value).toLowerCase() === tipo.toLowerCase() || String(opt.text).toLowerCase().indexOf(tipo.toLowerCase()) !== -1){ sel.selectedIndex = i; break; } }
                        var inlineRow = sel.closest('.inline-related') || sel.closest('.form-row') || sel.closest('tr') || sel.parentNode;
                        var wrapperTarget = findFieldWrapper(fieldName) || wrapper;
                        createVisibleCantidad(wrapperTarget, inlineRow, fieldName); compute(); try{ var qty = inlineRow.querySelector('input[name$="-cantidad"]'); if(qty) qty.focus(); }catch(e){}
                        processing = false; try{ window.__ctz_add_processing = false; }catch(e){}
                        return;
                      }
                    }catch(e){}
                  }
                }
                // fallback: count
                var selects = (detectRoot.querySelectorAll('select[name$="-tipo"]')||[]);
                if(selects.length > initialCount){ handled = true; try{ obs.disconnect(); }catch(e){} var sel = selects[selects.length-1]; console && console.log && console.log('ctz_admin: MutationObserver detected new select (by count)'); for(var i=0;i<sel.options.length;i++){ var opt = sel.options[i]; if(String(opt.value).toLowerCase() === tipo.toLowerCase() || String(opt.text).toLowerCase().indexOf(tipo.toLowerCase()) !== -1){ sel.selectedIndex = i; break; } } var inlineRow = sel.closest('.inline-related') || sel.closest('.form-row') || sel.closest('tr') || sel.parentNode; var wrapperTarget = findFieldWrapper(fieldName) || wrapper; createVisibleCantidad(wrapperTarget, inlineRow, fieldName); compute(); try{ var qty = inlineRow.querySelector('input[name$="-cantidad"]'); if(qty) qty.focus(); }catch(e){} _unlock(); }
              });
              try{ obs.observe(detectNode, { childList: true, subtree: true }); }catch(e){}
            }
          }catch(e){ console && console.warn && console.warn('ctz_admin: MutationObserver setup failed', e); }

          // dispatch click
          try{ localAddLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window })); }catch(e){ try{ localAddLink.click(); }catch(e){} }
          // clone fallback after 1000ms
          setTimeout(function(){ if(!handled){ try{ /* attempt clone fallback: keep user flow alive */ var totalInput = localInlineGroup && (localInlineGroup.querySelector('input[name$="-TOTAL_FORMS"]') || localInlineGroup.querySelector('input[name$="TOTAL_FORMS"]')) || document.querySelector('input[name$="-TOTAL_FORMS"]'); var rows = localInlineGroup ? Array.prototype.slice.call(localInlineGroup.querySelectorAll('.inline-related')) : []; if(rows.length === 0) rows = localInlineGroup ? Array.prototype.slice.call(localInlineGroup.querySelectorAll('tr')) : []; if(rows.length){ var last = rows[rows.length-1]; var newIndex = totalInput ? parseInt(totalInput.value,10) : rows.length; var clone = last.cloneNode(true); var elems = clone.querySelectorAll('*'); for(var i=0;i<elems.length;i++){ var el = elems[i]; if(el.name) el.name = el.name.replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex); if(el.id) el.id = el.id.replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex); if(el.getAttribute && el.getAttribute('for')) el.setAttribute('for', el.getAttribute('for').replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex)); if(el.tagName === 'INPUT'){ if(el.type === 'checkbox' || el.type === 'radio') el.checked = false; else el.value = ''; } if(el.tagName === 'SELECT') el.selectedIndex = 0; if(el.tagName === 'TEXTAREA') el.value = ''; } if(last.parentNode) last.parentNode.insertBefore(clone, last.nextSibling); if(totalInput) totalInput.value = (newIndex + 1).toString(); var sel = clone.querySelector('select[name$="-tipo"]') || clone.querySelector('select'); if(sel){ for(var j=0;j<sel.options.length;j++){ var o = sel.options[j]; if(String(o.value).toLowerCase() === tipo.toLowerCase() || String(o.text).toLowerCase().indexOf(tipo.toLowerCase()) !== -1){ sel.selectedIndex = j; break; } } } createVisibleCantidad(findFieldWrapper(fieldName) || wrapper, clone, fieldName); compute(); _unlock(); } }catch(e){} } }, 1000);

          // polling fallback until timeout
          var start = Date.now(); (function poll(){ if(Date.now() - start > 3000) { _unlock(); return; } try{ var selects = (detectRoot.querySelectorAll('select[name$="-tipo"]')||[]); if(selects.length > initialCount){ var sel = selects[selects.length-1]; for(var i=0;i<sel.options.length;i++){ var opt = sel.options[i]; if(String(opt.value).toLowerCase() === tipo.toLowerCase() || String(opt.text).toLowerCase().indexOf(tipo.toLowerCase()) !== -1){ sel.selectedIndex = i; break; } } var inlineRow = sel.closest('.inline-related') || sel.closest('.form-row') || sel.closest('tr') || sel.parentNode; var wrapperTarget = findFieldWrapper(fieldName) || wrapper; createVisibleCantidad(wrapperTarget, inlineRow, fieldName); compute(); _unlock(); return; } }catch(e){} setTimeout(poll, 50); })();

          return;
        }

        // no admin add-link: try clone fallback immediately
        try{
          var inlineGroup = document.getElementById('ctzitem_set-group') || document.querySelector('[id*="ctzitem"]') || document.querySelector('.inline-group') || document.querySelector('.inline-related');
          var totalInput = inlineGroup && (inlineGroup.querySelector('input[name$="-TOTAL_FORMS"]') || inlineGroup.querySelector('input[name$="TOTAL_FORMS"]')) || document.querySelector('input[name$="-TOTAL_FORMS"]');
          var rows = inlineGroup ? Array.prototype.slice.call(inlineGroup.querySelectorAll('.inline-related')) : [];
          if(rows.length === 0) rows = inlineGroup ? Array.prototype.slice.call(inlineGroup.querySelectorAll('tr')) : [];
          if(rows.length === 0) { _unlock(); return; }
          var last = rows[rows.length-1]; var newIndex = totalInput ? parseInt(totalInput.value,10) : rows.length; var clone = last.cloneNode(true); var elems = clone.querySelectorAll('*'); for(var i=0;i<elems.length;i++){ var el = elems[i]; if(el.name) el.name = el.name.replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex); if(el.id) el.id = el.id.replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex); if(el.getAttribute && el.getAttribute('for')) el.setAttribute('for', el.getAttribute('for').replace(/-\d+-/g, '-'+newIndex+'-').replace(/__prefix__/g, newIndex)); if(el.tagName === 'INPUT'){ if(el.type === 'checkbox' || el.type === 'radio') el.checked = false; else el.value = ''; } if(el.tagName === 'SELECT') el.selectedIndex = 0; if(el.tagName === 'TEXTAREA') el.value = ''; }
          if(last.parentNode) last.parentNode.insertBefore(clone, last.nextSibling); if(totalInput) totalInput.value = (newIndex + 1).toString(); var sel = clone.querySelector('select[name$="-tipo"]') || clone.querySelector('select'); if(sel){ for(var j=0;j<sel.options.length;j++){ var o = sel.options[j]; if(String(o.value).toLowerCase() === tipo.toLowerCase() || String(o.text).toLowerCase().indexOf(tipo.toLowerCase()) !== -1){ sel.selectedIndex = j; break; } } }
          createVisibleCantidad(findFieldWrapper(fieldName) || wrapper, clone, fieldName); compute(); processing = false; try{ window.__ctz_add_processing = false; }catch(e){}
        }catch(e){ console && console.warn && console.warn('ctz_admin: error cloning inline', e); }
      });

      // insert button in DOM
      if(wrapper && wrapper.parentNode){ if(wrapper.nextSibling) wrapper.parentNode.insertBefore(a, wrapper.nextSibling); else wrapper.parentNode.appendChild(a); }
      else if(target && target.appendChild){ var holder = document.createElement('div'); holder.className = 'ctz-add-holder'; holder.style.marginTop = '6px'; holder.appendChild(a); target.appendChild(holder); }
  else {/* cannot place add button: silent fallback will use Costos toolbar */}
    }

    // insert buttons for each field
    costFields.forEach(function(cf){ insertAddButton(cf.name, cf.tipo); });

    // create Costos toolbar if possible
    try{
      var modules2 = Array.prototype.slice.call(document.querySelectorAll('div.module, div.inline-group, div.inline-related'));
      var target2 = null; for(var i=0;i<modules2.length;i++){ var h2 = modules2[i].querySelector('h2'); var txt = h2 && h2.textContent ? h2.textContent.trim() : ''; if(!target2 && txt.indexOf('Costos') === 0) target2 = modules2[i]; }
      if(target2 && !target2.querySelector('.ctz-costs-toolbar')){
        var toolbar = document.createElement('div'); toolbar.className = 'ctz-costs-toolbar'; toolbar.style.marginTop = '8px'; toolbar.style.marginBottom = '8px'; costFields.forEach(function(cf){ var b = document.createElement('button'); b.type='button'; b.textContent = '\u2795 Añadir ' + (cf.name === 'proveedor' ? 'Proveedor' : (cf.name === 'mo_soma' ? 'MO SOMA' : 'Otros')); b.style.marginRight='8px'; b.addEventListener('click', function(){ insertAddButton(cf.name, cf.tipo); }); toolbar.appendChild(b); }); target2.appendChild(toolbar);
      }
    }catch(e){ console && console.warn && console.warn('ctz_admin: error creating toolbar', e); }

    // Do not hide or move the original inline module; keep Django admin DOM intact to preserve ManagementForm

  }

  // bootstrap: only attach listener if DOM not ready; otherwise call init once
  if(document.readyState && document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    try{ init(); }catch(e){}
  }

})();
