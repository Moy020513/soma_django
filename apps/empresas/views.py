from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Empresa

# Create your views here.

class EmpresasView(LoginRequiredMixin, ListView):
    model = Empresa
    template_name = 'empresas/index.html'
    context_object_name = 'empresas'


class EmpresaDetailView(LoginRequiredMixin, DetailView):
    model = Empresa
    template_name = 'empresas/detalle.html'
    context_object_name = 'empresa'