from django.contrib import admin
from django.urls import path, include
from usuarios import views
from django.contrib.auth.views import LogoutView
from django.conf import settings  # Importar settings
from django.conf.urls.static import static  # Importar static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # Página inicial (home)
    path('usuarios/', include(('usuarios.urls', 'usuarios'), namespace='usuarios')),  # Inclui as URLs do app 'usuarios' com namespace
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    #URLS DOCUMENTOS
    path('documentos/', include('documentos.urls', namespace='documentos')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
