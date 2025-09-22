from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

# Create your views here.

class FlotaVehicularView(LoginRequiredMixin, ListView):
    template_name = 'flota_vehicular/index.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        return []  # Placeholder hasta crear modelos