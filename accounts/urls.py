# URL relacionandas aos usuários
from django.urls import path
from . import views

urlpatterns = [
    path('usuarios/novousuario/', views.UserCreateView.as_view(), name='new_user'),
    path('usuarios/', views.UsersListView.as_view(), name='users_list'),
    path('usuarios/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'), 
    path('change-password/', views.UserPasswordChangeView.as_view(), name='change_password'),
    path('change-passowrd-done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('profile/', views.ProfileUpdateView.as_view(), name="profile"),
    path('auth/login', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
