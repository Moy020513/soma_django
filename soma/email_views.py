from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from .forms import CustomPasswordResetForm

class CustomPasswordResetView(PasswordResetView):
    """
    Vista personalizada para envío de emails multipart (HTML + texto)
    con validación de email existente
    """
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    success_url = '/accounts/password_reset/done/'
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Envía email con versión HTML y texto plano para mejor compatibilidad
        """
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())  # Remover saltos de línea del subject
        
        # Renderizar template de texto plano
        body_txt = render_to_string(email_template_name, context)
        
        # Renderizar template HTML si existe
        body_html = None
        if html_email_template_name:
            body_html = render_to_string(html_email_template_name, context)
        
        # Crear email multipart
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=body_txt,  # Versión texto plano
            from_email=from_email,
            to=[to_email]
        )
        
        # Agregar versión HTML si existe
        if body_html:
            email_message.attach_alternative(body_html, "text/html")
        
        # Enviar email
        email_message.send(fail_silently=False)