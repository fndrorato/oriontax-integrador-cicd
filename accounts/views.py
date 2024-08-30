# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import PasswordChangeView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse, reverse_lazy
from django.utils.html import strip_tags
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import IntegrityError
from django.views.generic import TemplateView, ListView, UpdateView
from django.contrib.auth.models import Group, User 
from rolepermissions.roles import assign_role
from rolepermissions.decorators import has_role_decorator
from .models import Profile
from .forms import UserModelForm, ProfileForm, generate_temporary_password
import random
import string


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        login_form = AuthenticationForm(request, data=request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data.get("username")
            password = login_form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Obtém o nome do grupo do usuário
                user_group = user.groups.first()  # Assume que o usuário pertence a apenas um grupo
                if user_group:
                    assign_role(user, user_group.name.lower())  # Atribui o papel com base no nome do grupo
                                
                return JsonResponse({"success": True, "redirect_url": reverse_lazy('home')})
            else:
                return JsonResponse({"success": False, "errors": ["Email ou senha inválida."]})
        else:
            errors = [error for sublist in login_form.errors.values() for error in sublist]
            return JsonResponse({"success": False, "errors": errors})

    return render(request, 'login.html', {'login_form': AuthenticationForm()})

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class UsersListView(ListView):
    model = User
    template_name = 'list_users.html'
    context_object_name = 'users'
    
    def get_queryset(self):      
        return User.objects.select_related('profile').prefetch_related('groups').exclude(id=1)

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')    
class UserCreateView(TemplateView):
    template_name = 'create_user.html'

    def get(self, request, *args, **kwargs):
        user_form = UserModelForm() 
        profile_form = ProfileForm()
        group_choices = Group.objects.all().values_list('name', flat=True)
        return render(request, self.template_name, {
            'user_form': user_form, 
            'profile_form': profile_form, 
            'group_choices': group_choices
        })

    def post(self, request, *args, **kwargs):
        user_form = UserModelForm(request.POST) 
        profile_form = ProfileForm(request.POST)
        password = generate_temporary_password()

        if user_form.is_valid() and profile_form.is_valid():
            try:
                user = user_form.save(commit=False)
                user.username = user.email  # set username to email
                user.set_password(password)  # set temporary password
                user.is_active = True
                user.save()

                # Verifique se o usuário já tem um perfil
                if hasattr(user, 'profile'):
                    profile = user.profile  # Use o perfil existente
                else:
                    profile = profile_form.save(commit=False)
                    profile.user = user  # set the user instance
                
                # Atualize os campos do perfil
                profile.birth_date = profile_form.cleaned_data['birth_date']
                profile.phone = profile_form.cleaned_data['phone']
                profile.save()

                # Add user to the selected group
                if request.POST.get('group'):
                    selected_group = Group.objects.get(name=request.POST.get('group'))
                    selected_group.user_set.add(user)
                    
                # Enviar e-mail de boas-vindas
                self.send_welcome_email(user, request)                    

                return redirect(reverse_lazy('new_user'))
            except IntegrityError as e:
                print(e)
                user_form.add_error(None, "A user with this email already exists.")
        else:          
            user_form_errors = user_form.errors
            profile_form_errors = profile_form.errors

        return render(request, self.template_name, {
            'user_form': user_form, 
            'profile_form': profile_form, 
            'group_choices': Group.objects.all().values_list('name', flat=True)
        })
        
    def send_welcome_email(self, user, request):
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        password_reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        context = {
            'user': user,
            'password_reset_url': password_reset_url,
        }
        subject = render_to_string('welcome_email_subject.txt', context)
        message = render_to_string('welcome_email.txt', context)
        send_mail(
            subject.strip(),  # Assunto do e-mail
            message,  # Corpo do e-mail
            None,  # Remetente (usa DEFAULT_FROM_EMAIL do settings)
            [user.email]  # Destinatário
        )       

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')    
class UserUpdateView(UpdateView):
    model = User
    form_class = UserModelForm
    template_name = 'update_user.html'

    def get_object(self, queryset=None):
        return get_object_or_404(User, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        if self.request.POST:
            context['profile_form'] = ProfileForm(self.request.POST, instance=user.profile)
        else:
            context['profile_form'] = ProfileForm(instance=user.profile)

        context['groups'] = Group.objects.all()
        context['selected_group'] = user.groups.first()  # Assume que o usuário está em um único grupo
        
        # Carregar apenas os supervisores para o formulário
        supervisor_users = User.objects.filter(groups__name='supervisor')
        context['supervisor_users'] = supervisor_users
        
        # Carregar apenas os supervisores para o formulário
        gerente_users = User.objects.filter(groups__name='gerente')
        context['gerente_users'] = gerente_users        

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        if form.is_valid() and profile_form.is_valid():
            self.object = form.save()
            profile = profile_form.save(commit=False)
            profile.user = self.object
            profile.save()

            # Atualizar o grupo do usuário
            group_name = self.request.POST.get('group')
            if group_name:
                group = Group.objects.get(name=group_name)
                self.object.groups.clear()
                self.object.groups.add(group)

            # return redirect(self.success_url)
            return redirect(reverse_lazy('user_update', kwargs={'pk': self.object.pk}))
        else:
            return self.render_to_response(self.get_context_data(form=form))    

@method_decorator(login_required(login_url='login'), name='dispatch')
class UserPasswordChangeView(PasswordChangeView):
    template_name = 'change_password.html'
    success_url = reverse_lazy('password_change_done')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['password_change_success'] = False
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
class PasswordChangeDoneView(PasswordChangeView):
    template_name = 'change_password.html'
    success_url = reverse_lazy('password_change_done')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['password_change_success'] = True
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
class ProfileUpdateView(UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'update_profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_form'] = UserModelForm(instance=self.request.user)
        return context

    def form_valid(self, form):
        user_form = UserModelForm(self.request.POST, instance=self.request.user)
        
        # Definir a flag antes de chamar `is_valid`
        user_form.skip_email_validation = True  # Ou False, dependendo da necessidade
        
        # Definir o campo is_active como True
        user_form.instance.is_active = True
                
        if user_form.is_valid() and form.is_valid():
            user_form.save()
            return super().form_valid(form)
        else:         
            return self.render_to_response(self.get_context_data(form=form))
            
def logout_view(request):
    logout(request)
    return redirect('login')


class PasswordResetView(PasswordResetView):
    template_name = 'reset_password.html'
    email_template_name = 'password_reset_email.txt'
    html_email_template_name = 'password_reset_email.html'
    subject_template_name = 'custom_password_reset_subject.txt'
    success_url = '/password_reset/done/'   
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['protocol'] = self.request.scheme
        context['domain'] = self.request.get_host()
        return context 
    
    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        # Add user to context
        User = get_user_model()
        # Obtenha o usuário com segurança
        try:
            user = get_object_or_404(User, email=context['email'])
        except User.DoesNotExist:
            user = None 
            
        # Adicione o usuário ao contexto se existir
        if user:
            context['user'] = user             
        
        subject = render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')
        email_message.send()       
    
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'password_reset_complete.html'    