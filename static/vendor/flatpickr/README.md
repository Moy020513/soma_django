Instrucciones para Flatpickr assets

Archivos creados (placeholders) — pega el contenido minificado correspondiente en cada uno:

- flatpickr.min.css  -> pegar CSS minificado (o usar CDN)
- flatpickr.min.js   -> pegar JS minificado (o usar CDN)
- l10n/es.js         -> opcional: pegar locale en español

Recomendaciones:
1) Si vas a servir estáticos desde Django en producción, después de pegar los archivos ejecuta:

   python manage.py collectstatic

2) Asegúrate de que la ruta es `static/vendor/flatpickr/flatpickr.min.js` y `flatpickr.min.css` para que la plantilla `templates/admin/change_form.html` los cargue.
3) Si prefieres usar CDN, no hace falta pegar los archivos; el template ya tiene fallback a CDN.
4) Si quieres, puedo descargar y pegar los archivos por ti si me das permiso.
