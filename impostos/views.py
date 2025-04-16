from rolepermissions.decorators import has_role_decorator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, UpdateView, DetailView
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Cfop, IcmsCst, IcmsAliquota, IcmsAliquotaReduzida, CBENEF, Protege, PisCofinsCst, NaturezaReceita
from .forms import CfopForm, IcmsCstForm, IcmsAliquotaForm, IcmsAliquotaReduzForm, CBENEFForm, ProtegeForm, PisCofinsCstForm, NaturezaReceitaForm

def get_piscofins_aliquota(request):
    piscofins_cst_code = request.GET.get('piscofins_cst')
    try:
        piscofins_cst = PisCofinsCst.objects.get(code=piscofins_cst_code)
        data = {
            'pis_aliquota': piscofins_cst.pis_aliquota,
            'cofins_aliquota': piscofins_cst.cofins_aliquota
        }
    except PisCofinsCst.DoesNotExist:
        data = {'error': 'PIS/COFINS CST not found'}
    return JsonResponse(data)

@method_decorator(login_required(login_url='login'), name='dispatch')
class CfopsListView(ListView):
    model = Cfop
    form_class = CfopForm
    template_name = 'cfop.html'
    context_object_name = 'cfops'
    success_url = '/impostos/cfop/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CfopForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class CfopCreateView(TemplateView):
    template_name = 'cfop.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CfopForm()
        return context

    def post(self, request, *args, **kwargs):
        form = CfopForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('CFOP', 'CFOP') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class CfopDetailView(DetailView):
    model = Cfop
    context_object_name = 'cfop'

    def get(self, request, *args, **kwargs):
        cfop = self.get_object()
        data = {
            'cfop': cfop.cfop,
            'description': cfop.description,
            'operation': cfop.operation,
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class CfopUpdateView(UpdateView):
    model = Cfop
    form_class = CfopForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class CfopDeleteView(View):
    def delete(self, request, *args, **kwargs):
        cfop_id = kwargs.get('pk')
        try:
            cfop = Cfop.objects.get(id=cfop_id)
            cfop.delete()
            return JsonResponse({'success': True})
        except Cfop.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cfop not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500) 
        
        

@method_decorator(login_required(login_url='login'), name='dispatch')
class IcmsCstListView(ListView):
    model = IcmsCst
    form_class = IcmsCstForm
    template_name = 'icmscst.html'
    context_object_name = 'icmscsts'
    success_url = '/impostos/cst-icms/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IcmsCstForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsCstCreateView(TemplateView):
    template_name = 'icmscst.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IcmsCstForm()
        return context

    def post(self, request, *args, **kwargs):
        form = IcmsCstForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do CST', 'Icms do CST') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class IcmsCstDetailView(DetailView):
    model = IcmsCst
    context_object_name = 'icmscst'

    def get(self, request, *args, **kwargs):
        icmscst = self.get_object()
        data = {
            'code': icmscst.code,
            'description': icmscst.description,
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsCstUpdateView(UpdateView):
    model = IcmsCst
    form_class = IcmsCstForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsCstDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        try:
            icmscst = IcmsCst.objects.get(code=code_id)
            icmscst.delete()
            return JsonResponse({'success': True})
        except IcmsCst.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Icms CST not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)                      


@method_decorator(login_required(login_url='login'), name='dispatch')
class IcmsAliquotaListView(ListView):
    model = IcmsAliquota
    form_class = IcmsAliquotaForm
    template_name = 'icmsaliquota.html'
    context_object_name = 'icmsaliquotas'
    success_url = '/impostos/icms-aliquota/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IcmsAliquotaForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsAliquotaCreateView(TemplateView):
    template_name = 'icmsaliquota.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IcmsAliquotaForm()
        return context

    def post(self, request, *args, **kwargs):
        form = IcmsAliquotaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do Aliquota', 'Icms do Aliquota') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class IcmsAliquotaDetailView(DetailView):
    model = IcmsAliquota
    context_object_name = 'icmsaliquota'

    def get(self, request, *args, **kwargs):
        icmsAliquota = self.get_object()
        data = {
            'code': icmsAliquota.code,
            'description': icmsAliquota.description,
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsAliquotaUpdateView(UpdateView):
    model = IcmsAliquota
    form_class = IcmsAliquotaForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsAliquotaDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        try:
            icmsAliquota = IcmsAliquota.objects.get(code=code_id)
            icmsAliquota.delete()
            return JsonResponse({'success': True})
        except IcmsAliquota.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Icms Aliquota not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500) 
     
     
        
@method_decorator(login_required(login_url='login'), name='dispatch')
class IcmsAliquotaReduzidaListView(ListView):
    model = IcmsAliquotaReduzida
    form_class = IcmsAliquotaReduzForm
    template_name = 'icmsaliquotareduzida.html'
    context_object_name = 'icmsaliquotasreduzidas'
    success_url = '/impostos/icms-aliquota-reduzida/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IcmsAliquotaReduzForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsAliquotaReduzidaCreateView(TemplateView):
    template_name = 'icmsaliquotareduzida.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IcmsAliquotaReduzForm()
        return context

    def post(self, request, *args, **kwargs):
        form = IcmsAliquotaReduzForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do Aliquota', 'Icms do Aliquota') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class IcmsAliquotaReduzidaDetailView(DetailView):
    model = IcmsAliquotaReduzida
    context_object_name = 'icmsaliquotareduzida'

    def get(self, request, *args, **kwargs):
        icmsAliquotaReduzida = self.get_object()
        data = {
            'code': icmsAliquotaReduzida.code,
            'description': icmsAliquotaReduzida.description,
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsAliquotaReduzidaUpdateView(UpdateView):
    model = IcmsAliquotaReduzida
    form_class = IcmsAliquotaReduzForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class IcmsAliquotaReduzidaDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        try:
            icmsAliquotaReduzida = IcmsAliquotaReduzida.objects.get(code=code_id)
            icmsAliquotaReduzida.delete()
            return JsonResponse({'success': True})
        except IcmsAliquotaReduzida.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Icms Aliquota Reduzida not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)                               

        
@method_decorator(login_required(login_url='login'), name='dispatch')
class CbenefListView(ListView):
    model = CBENEF
    form_class = CBENEFForm
    template_name = 'cbenef.html'
    context_object_name = 'cbenefs'
    success_url = '/impostos/icbenef/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CBENEFForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class CbenefCreateView(TemplateView):
    template_name = 'cbenef.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CBENEFForm()
        return context

    def post(self, request, *args, **kwargs):
        form = CBENEFForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do Aliquota', 'Icms do Aliquota') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class CbenefDetailView(DetailView):
    model = CBENEF
    context_object_name = 'cbenef'

    def get(self, request, *args, **kwargs):
        cbenef = self.get_object()
        data = {
            'code': cbenef.code,
            'description': cbenef.description,
            'legislation': cbenef.legislation,
            'icms_cst': {
                'code': cbenef.icms_cst.code,
                'description': cbenef.icms_cst.description
            }
        }
        return JsonResponse(data) 
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class CbenefUpdateView(UpdateView):
    model = CBENEF
    form_class = CBENEFForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class CbenefDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        try:
            cbenef = CBENEF.objects.get(code=code_id)
            cbenef.delete()
            return JsonResponse({'success': True})
        except CBENEF.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'CBENEF not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        
@method_decorator(login_required(login_url='login'), name='dispatch')
class ProtegeListView(ListView):
    model = Protege
    form_class = ProtegeForm
    template_name = 'protege.html'
    context_object_name = 'proteges'
    success_url = '/impostos/protege/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProtegeForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class ProtegeCreateView(TemplateView):
    template_name = 'protege.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProtegeForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ProtegeForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do CST', 'Icms do CST') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class ProtegeDetailView(DetailView):
    model = Protege
    context_object_name = 'protege'

    def get(self, request, *args, **kwargs):
        protege = self.get_object()
        data = {
            'code': protege.code,
            'description': protege.description,
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class ProtegeUpdateView(UpdateView):
    model = Protege
    form_class = ProtegeForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class ProtegeDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        try:
            protege = Protege.objects.get(code=code_id)
            protege.delete()
            return JsonResponse({'success': True})
        except Protege.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Protege not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500) 
        

        
@method_decorator(login_required(login_url='login'), name='dispatch')
class PisCofinsCstListView(ListView):
    model = PisCofinsCst
    form_class = PisCofinsCstForm
    template_name = 'piscofinsaliquota.html'
    context_object_name = 'piscofinscsts'
    success_url = '/impostos/pis-cofins-cst/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PisCofinsCstForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class PisCofinsCstCreateView(TemplateView):
    template_name = 'piscofinsaliquota.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PisCofinsCstForm()
        return context

    def post(self, request, *args, **kwargs):
        form = PisCofinsCstForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do CST', 'Icms do CST') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class PisCofinsCstDetailView(DetailView):
    model = PisCofinsCst
    context_object_name = 'piscofinscst'

    def get(self, request, *args, **kwargs):
        piscofinscst = self.get_object()
        data = {
            'code': piscofinscst.code,
            'description': piscofinscst.description,
            'pis_aliquota': piscofinscst.pis_aliquota,
            'cofins_aliquota': piscofinscst.cofins_aliquota,
            'type_company': piscofinscst.type_company,
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class PisCofinsCstUpdateView(UpdateView):
    model = PisCofinsCst
    form_class = PisCofinsCstForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class PisCofinsCstDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        print(code_id)
        try:
            piscofinscst = PisCofinsCst.objects.get(code=code_id)
            piscofinscst.delete()
            return JsonResponse({'success': True})
        except PisCofinsCst.DoesNotExist:
            print('PisCofinsCst not found')
            return JsonResponse({'success': False, 'error': 'PisCofinsCst not found'}, status=404)
        except Exception as e:
            print(str(e))
            return JsonResponse({'success': False, 'error': str(e)}, status=500) 
        

@method_decorator(login_required(login_url='login'), name='dispatch')
class NaturezaReceitaListView(ListView):
    model = NaturezaReceita
    form_class = NaturezaReceitaForm
    template_name = 'naturezareceita.html'
    context_object_name = 'naturezareceitas'
    success_url = '/impostos/natureza-receita/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = NaturezaReceitaForm()
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class NaturezaReceitaCreateView(TemplateView):
    template_name = 'naturezareceita.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = NaturezaReceitaForm()
        return context

    def post(self, request, *args, **kwargs):
        form = NaturezaReceitaForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = {field: [str(error).replace('Icms do CST', 'Icms do CST') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)
    
@method_decorator(login_required(login_url='login'), name='dispatch')
class NaturezaReceitaDetailView(DetailView):
    model = NaturezaReceita
    context_object_name = 'naturezareceita'

    def get(self, request, *args, **kwargs):
        naturezareceita = self.get_object()
        data = {
            'code': naturezareceita.code,
            'category': naturezareceita.category,
            'description': naturezareceita.description,
            'ncm': naturezareceita.ncm,
            'piscofins_cst': naturezareceita.piscofins_cst.code
        }
        return JsonResponse(data)  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class NaturezaReceitaUpdateView(UpdateView):
    model = NaturezaReceita
    form_class = NaturezaReceitaForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})   
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator('administrador'), name='dispatch')
class NaturezaReceitaDeleteView(View):
    def delete(self, request, *args, **kwargs):
        code_id = kwargs.get('pk')
        try:
            piscofinscst = NaturezaReceita.objects.get(code=code_id)
            piscofinscst.delete()
            return JsonResponse({'success': True})
        except NaturezaReceita.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'NaturezaReceita not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500) 
        
           