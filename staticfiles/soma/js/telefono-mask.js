document.addEventListener('DOMContentLoaded', function() {
  function formatPhone(value) {
    const digits = value.replace(/\D/g, '').slice(0,10);
    const parts = [];
    if (digits.length > 0) parts.push(digits.slice(0,3));
    if (digits.length > 3) parts.push(digits.slice(3,6));
    if (digits.length > 6) parts.push(digits.slice(6,10));
    if (parts.length === 0) return '';
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return `(${parts[0]}) ${parts[1]}`;
    return `(${parts[0]}) ${parts[1]}-${parts[2]}`;
  }

  document.querySelectorAll('.telefono-mask').forEach(function(input) {
    // inicializar formato si ya tiene valor
    input.value = formatPhone(input.value);
    input.addEventListener('input', function(e) {
      const pos = input.selectionStart;
      const oldLen = input.value.length;
      input.value = formatPhone(input.value);
      const newLen = input.value.length;
      // Ajustar cursor al final (simple)
      input.setSelectionRange(newLen, newLen);
    });
  });
});
