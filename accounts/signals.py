# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from accounts.models import Profile
from base.models import Costs
from cattles.models import MeatCut, UserMeatCut
from pricing.models import UsersCosts


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Cria o Profile
        Profile.objects.create(user=instance)

        # Adiciona todos os cortes ativos no UserMeatCut
        active_meat_cuts = MeatCut.objects.filter(active=True)
        user_meat_cut_instances = [
            UserMeatCut(user=instance, meat_cut=meat_cut.name)
            for meat_cut in active_meat_cuts
        ]
        UserMeatCut.objects.bulk_create(user_meat_cut_instances)     
        
        # Adiciona todos os custos ativos ao UserCosts
        active_costs = Costs.objects.filter(active=True)
        cost_entries = [
            UsersCosts(user=instance, description=cost.name)
            for cost in active_costs
        ]
        UsersCosts.objects.bulk_create(cost_entries)            

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
