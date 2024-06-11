from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView
from .models import Task
from .forms import TaskForm

class TaskCreateView(CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_form.html'
    success_url = '/configuracoes/horario-execucao/'  # Altere para a URL de sucesso desejada

    def get(self, request, *args, **kwargs):
        if Task.objects.exists():
            first_task = Task.objects.first()
            return redirect('task_update_execution_time', pk=first_task.pk)
        return super().get(request, *args, **kwargs)    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view'] = {'action': 'create'}
        return context   

class TaskUpdateView(UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view'] = {'action': 'update'}
        return context    
    
    def get_success_url(self):
        return reverse_lazy('task_update_execution_time', kwargs={'pk': self.object.pk})     

