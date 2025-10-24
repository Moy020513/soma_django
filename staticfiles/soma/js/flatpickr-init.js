document.addEventListener('DOMContentLoaded', function() {
  if (typeof flatpickr !== 'undefined') {
    try {
      const selector = '.soma-datepicker, input.vDateField';
      const nodes = document.querySelectorAll(selector);
      if (nodes && nodes.length) {
        nodes.forEach(function(node) {
          // initialize flatpickr on the element if not already initialized
          if (!node._flatpickr) {
            flatpickr(node, {
              dateFormat: 'Y-m-d',
              altInput: true,
              altFormat: 'd/m/Y',
              allowInput: true,
              locale: 'es',
              maxDate: 'today',
              clickOpens: true,
            });
          }
        });
      }
    } catch (e) {
      console.error('flatpickr init error', e);
    }
  }
});
