(function(){
    function toggleUso(){
        var tipo = document.getElementById('id_tipo');
        var usoRow = document.querySelector('.form-row.field-uso_energia');
        if(!usoRow) return;
        var usoInput = document.getElementById('id_uso_energia');
        if(tipo && tipo.value === 'MAQ'){
            usoRow.style.display = '';
            if(usoInput) {
                usoInput.disabled = false;
            }
        } else {
            usoRow.style.display = 'none';
            // limpiar y deshabilitar valor si está oculto
            if(usoInput){
                try{ usoInput.value = ''; }catch(e){}
                usoInput.disabled = true;
            }
        }
    }
    // Esperar hasta que el DOM esté listo
    document.addEventListener('DOMContentLoaded', function(){
        toggleUso();
        var tipo = document.getElementById('id_tipo');
        if(tipo){
            tipo.addEventListener('change', toggleUso);
        }
    });
})();
