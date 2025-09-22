from django.contrib import admin
from .models import CategoriaHerramienta, Herramienta, AsignacionHerramienta


@admin.register(CategoriaHerramienta)
class CategoriaHerramientaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre', 'descripcion']
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'modelo', 'numero_serie', 'estado', 'fecha_adquisicion']
    list_filter = ['categoria', 'estado', 'fecha_adquisicion']
    search_fields = ['nombre', 'modelo', 'numero_serie', 'descripcion']
    list_editable = ['estado']
    date_hierarchy = 'fecha_adquisicion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'categoria', 'modelo', 'numero_serie')
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'fecha_adquisicion')
        }),
        ('Información Financiera', {
            'fields': ('costo',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('categoria')


@admin.register(AsignacionHerramienta)
class AsignacionHerramientaAdmin(admin.ModelAdmin):
    list_display = ['herramienta', 'empleado', 'fecha_asignacion', 'fecha_devolucion']
    list_filter = ['fecha_asignacion', 'fecha_devolucion', 'herramienta__categoria']
    search_fields = ['herramienta__nombre', 'empleado__nombre', 'empleado__apellidos']
    date_hierarchy = 'fecha_asignacion'
    
    fieldsets = (
        ('Asignación', {
            'fields': ('herramienta', 'empleado')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_devolucion')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('herramienta', 'herramienta__categoria', 'empleado')
    
    actions = ['marcar_como_devueltas']
    
    def marcar_como_devueltas(self, request, queryset):
        from django.utils import timezone
        today = timezone.now().date()
        updated = queryset.filter(fecha_devolucion__isnull=True).update(fecha_devolucion=today)
        self.message_user(request, f'{updated} herramientas marcadas como devueltas.')
    marcar_como_devueltas.short_description = "Marcar como devueltas (fecha actual)"