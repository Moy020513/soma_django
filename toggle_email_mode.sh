#!/bin/bash

# Script para alternar entre modo consola y Gmail en desarrollo
# Uso: ./toggle_email_mode.sh [gmail|console]

ENV_FILE=".env"

if [ "$1" = "gmail" ]; then
    echo "🔄 Cambiando a modo Gmail..."
    echo ""
    echo "⚠️  NECESITAS CONFIGURAR:"
    echo "1. Tu Gmail: EMAIL_HOST_USER=tu-gmail@gmail.com"
    echo "2. Tu contraseña de aplicación: EMAIL_HOST_PASSWORD=xxxx-xxxx-xxxx-xxxx"
    echo ""
    echo "📧 Descomenta estas líneas en tu .env:"
    echo "EMAIL_HOST=smtp.gmail.com"
    echo "EMAIL_HOST_USER=tu-gmail@gmail.com" 
    echo "EMAIL_HOST_PASSWORD=tu-contraseña-de-aplicacion"
    echo "EMAIL_USE_TLS=True"
    echo "EMAIL_PORT=587"
    echo ""
    echo "💡 Para obtener contraseña de aplicación:"
    echo "   Gmail → Gestionar cuenta → Seguridad → Contraseñas de aplicaciones"

elif [ "$1" = "console" ]; then
    echo "🔄 Cambiando a modo consola..."
    echo ""
    echo "📝 Comenta estas líneas en tu .env (agregar # al inicio):"
    echo "# EMAIL_HOST=smtp.gmail.com"
    echo "# EMAIL_HOST_USER=..."
    echo "# EMAIL_HOST_PASSWORD=..."
    echo "# EMAIL_USE_TLS=True"
    echo "# EMAIL_PORT=587"
    echo ""
    echo "✅ Los emails aparecerán en la consola donde corre el servidor"

else
    echo "📧 Toggle Email Mode - SOMA Django"
    echo ""
    echo "Uso:"
    echo "  ./toggle_email_mode.sh gmail     - Configurar para envío real a Gmail"
    echo "  ./toggle_email_mode.sh console   - Volver a modo consola (desarrollo)"
    echo ""
    echo "Estado actual en .env:"
    if grep -q "^EMAIL_HOST=" "$ENV_FILE" 2>/dev/null; then
        echo "✉️  MODO: Gmail (SMTP)"
        echo "📤 Los emails se envían realmente"
    else
        echo "🖥️  MODO: Consola"
        echo "📋 Los emails aparecen en la terminal"
    fi
fi