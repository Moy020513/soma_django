# Sistema de Control de Asistencia por Geolocalización

## Descripción General

El sistema de control de asistencia basado en geolocalización permite a los empleados registrar su entrada y salida del trabajo usando las coordenadas GPS de sus dispositivos móviles. Los administradores pueden consultar y supervisar la asistencia en tiempo real.

## Funcionalidades Principales

### 📱 Para Empleados

#### Registro de Ubicación (/ubicaciones/registrar)
- **Geolocalización automática**: Utiliza la API de geolocalización del navegador
- **Dos tipos de registro**:
  - **Entrada**: Al llegar al trabajo
  - **Salida**: Al terminar la jornada
- **Una vez por día**: Solo se permite registrar una entrada y una salida por día
- **Zona horaria**: Maneja correctamente la zona horaria de México (America/Mexico_City)

#### Proceso de Registro:
1. El empleado presiona "Registrar Entrada" o "Registrar Salida"
2. El navegador solicita permiso de ubicación
3. Se obtienen las coordenadas GPS (latitud/longitud) y precisión
4. Se muestra un mapa de previsualización con la ubicación
5. Los datos se envían al servidor con timestamp local
6. El sistema valida que no exista registro previo del mismo tipo para el día
7. Se confirma el registro exitoso

### 👥 Para Administradores

#### Dashboard de Asistencia (/ubicaciones/list)
- **Vista general**: Registros de todos los empleados por fecha
- **Filtrado por fecha**: Consultar asistencia de días específicos
- **Separación por tipo**: Pestañas para entradas y salidas
- **Mapas interactivos**: Cada registro muestra un mini-mapa de la ubicación
- **Estadísticas en tiempo real**:
  - Empleados que ya registraron entrada/salida
  - Lista de empleados faltantes por registrar
- **Función de limpieza**: Borrar todas las ubicaciones (con confirmación)

#### Información Mostrada:
- Nombre del empleado
- Día de la semana y fecha/hora del registro
- Coordenadas GPS exactas
- Mapa interactivo con marcador de posición
- Posibilidad de centrar/navegar en cada mapa

## 🗺️ Datos Capturados

- **Coordenadas GPS**: Latitud y longitud precisas
- **Timestamp**: Fecha y hora exacta del registro
- **Tipo**: 'entrada' o 'salida'
- **Empleado**: ID del empleado que registra
- **Precisión**: Nivel de exactitud de la ubicación GPS

## 🛡️ Validaciones y Seguridad

- **Un registro por día**: Previene registros duplicados
- **Validación temporal**: Verifica que sea el mismo día laboral
- **Permisos de ubicación**: Requiere autorización explícita del usuario
- **Manejo de errores**: Gestiona fallos de GPS y permisos denegados
- **Zona horaria**: Conversión correcta a hora local de México

## 🎨 Experiencia de Usuario

- **Interfaz responsiva**: Funciona en móviles y desktop
- **Mapas integrados**: Usa Leaflet para visualización
- **Feedback visual**: Estados de botones (registrado/pendiente/deshabilitado)
- **Alertas informativas**: Mensajes de éxito, error y advertencias
- **Navegación intuitiva**: Botones grandes para uso móvil

## 📊 Casos de Uso Típicos

1. **Empleado llega al trabajo**: Registra entrada con GPS
2. **Supervisor verifica asistencia**: Consulta quién ha llegado y quién falta
3. **Control de horarios**: Administrador revisa puntualidad y cumplimiento
4. **Empleado termina jornada**: Registra salida antes de irse
5. **Análisis histórico**: Consultar patrones de asistencia por fechas

## ⚙️ Aspectos Técnicos

- **Modelo de datos simple**: Solo almacena coordenadas, timestamp y tipo
- **Relación con empleados**: Foreign key hacia el modelo Empleado
- **API REST**: Endpoints JSON para registro desde JavaScript
- **Integración con mapas**: Leaflet para visualización geográfica
- **Manejo de fechas**: PyTZ para zona horaria correcta

## 🚀 URLs Principales

- `/ubicaciones/registrar/` - Registro para empleados
- `/ubicaciones/list/` - Dashboard para administradores
- `/ubicaciones/list/YYYY-MM-DD/` - Dashboard filtrado por fecha
- `/ubicaciones/api/registrar/` - API para registro
- `/ubicaciones/api/limpiar/` - API para limpiar registros
- `/ubicaciones/mapa/ID/` - Vista detallada de registro

## 🔧 Configuración de Navegación

El sistema agrega automáticamente:
- **Icono de ubicación** en la barra de navegación para empleados
- **Dashboard de asistencia** para administradores
- **Integración en el panel admin** con icono específico

## 📝 Modelo de Base de Datos

```python
class RegistroUbicacion(models.Model):
    empleado = models.ForeignKey(Empleado, ...)
    latitud = models.DecimalField(max_digits=12, decimal_places=8)
    longitud = models.DecimalField(max_digits=12, decimal_places=8) 
    precision = models.FloatField(null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=[('entrada', 'Entrada'), ('salida', 'Salida')])
    timestamp = models.DateTimeField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
```

## 🌟 Beneficios

- **Control preciso**: Ubicación GPS exacta de registros
- **Prevención de fraudes**: Imposible registrar desde ubicaciones remotas
- **Facilidad de uso**: Interface intuitiva y responsiva
- **Supervisión efectiva**: Dashboard completo para administradores
- **Datos históricos**: Almacenamiento para análisis posterior
- **Integración completa**: Funciona con el sistema existente de empleados

El sistema combina control de asistencia tradicional con tecnología GPS moderna, proporcionando comodidad para empleados y supervisión efectiva para administradores.