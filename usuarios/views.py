import logging
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UsuarioCadastroForm, UsuarioChangeForm, GrupoForm, UsuarioPermissaoForm, ProfileForm
from .models import Usuario, Grupo
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from ldap3 import Server, Connection, ALL
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LogoutView
from django.contrib.auth.models import Permission, Group
from django.utils.translation import gettext as _


# Configuração do logger
logger = logging.getLogger(__name__)

# Função para renderizar a página home

# Registrar usuários locais no banco de dados
def registrar_usuario(request):
    if request.method == 'POST':
        form = UsuarioCadastroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_ad_user = False  # Usuário local
            user.save()
            login(request, user)  # Faz login automaticamente após o cadastro
            return redirect('usuarios:lista_usuarios')  # Redireciona com o namespace correto
    else:
        form = UsuarioCadastroForm()

    return render(request, 'usuarios/registrar.html', {'form': form})

# Função de login
def login_usuario(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            logger.info(f"Tentando autenticar o usuário: {username}")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                logger.info(f"Usuário {username} autenticado com sucesso.")
                return redirect('home')
            else:
                logger.warning(f"Falha na autenticação do usuário {username}.")
                messages.error(request, 'Usuário ou senha incorretos.')
        else:
            logger.error(f"Erros no formulário de login: {form.errors}")
            messages.error(request, 'Formulário inválido. Verifique os campos.')

        return render(request, 'usuarios/login.html', {'form': form})
    else:
        form = AuthenticationForm(request)
        return render(request, 'usuarios/login.html', {'form': form})

# Função para listar os usuários
@login_required
def lista_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/lista_usuarios.html', {'usuarios': usuarios})

# Função para editar o usuário
@login_required
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        form = UsuarioChangeForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('usuarios:lista_usuarios')
    else:
        form = UsuarioChangeForm(instance=usuario)

    return render(request, 'usuarios/editar_usuario.html', {'form': form})

# Função para buscar e importar usuários do Active Directory
@login_required
def buscar_usuarios_ad(request):
    usuarios_ad = []
    conn = None
    if request.method == "POST":
        nome_usuario = request.POST.get("nome_usuario", "")
        
        ldap_server = "ldap://tcc1.net"
        ldap_user = "CN=Administrator,CN=Users,DC=tcc1,DC=net"
        ldap_password = "Admin@ti"

        try:
            logger.info(f"Tentando conectar ao servidor LDAP: {ldap_server}")
            server = Server(ldap_server, get_info=ALL)
            conn = Connection(server, user=ldap_user, password=ldap_password, auto_bind=True)
            logger.info("Conexão ao LDAP estabelecida com sucesso.")

            search_base = "CN=Users,DC=tcc1,DC=net"
            search_filter = f"(sAMAccountName=*{nome_usuario}*)"

            conn.search(search_base, search_filter, attributes=['sAMAccountName', 'givenName', 'sn', 'mail'])

            if conn.entries:
                for entry in conn.entries:
                    usuario = {
                        'sAMAccountName': entry.sAMAccountName.value,
                        'givenName': entry.givenName.value,
                        'sn': entry.sn.value,
                        'mail': entry.mail.value if 'mail' in entry else ''
                    }
                    usuarios_ad.append(usuario)
            else:
                logger.warning("Nenhum usuário encontrado no AD.")
                messages.error(request, "Nenhum usuário encontrado no AD.")
        except Exception as e:
            logger.error(f"Erro ao buscar usuários no AD: {str(e)}")
            messages.error(request, "Erro ao conectar ao Active Directory.")
        finally:
            if conn:
                conn.unbind()
            logger.info("Conexão com o LDAP encerrada.")

    return render(request, 'usuarios/buscar_usuarios_ad.html', {'usuarios_ad': usuarios_ad})

# Função para importar usuários do AD para o Django
@login_required
def importar_usuarios_ad(request):
    conn = None
    if request.method == "POST":
        usuarios_selecionados = request.POST.getlist("usuarios")

        ldap_server = "ldap://tcc1.net"
        ldap_user = "CN=Administrator,CN=Users,DC=tcc1,DC=net"
        ldap_password = "Admin@ti"

        try:
            logger.info(f"Tentando conectar ao servidor LDAP: {ldap_server}")
            server = Server(ldap_server, get_info=ALL)
            conn = Connection(server, user=ldap_user, password=ldap_password, auto_bind=True)
            logger.info("Conexão ao LDAP estabelecida com sucesso.")

            for username in usuarios_selecionados:
                logger.info(f"Tentando importar usuário: {username}")

                if Usuario.objects.filter(username=username).exists():
                    logger.warning(f"O usuário {username} já existe no sistema.")
                    messages.warning(request, f"O usuário {username} já existe no sistema e não foi importado.")
                    continue

                search_filter = f"(sAMAccountName={username})"
                search_base = "CN=Users,DC=tcc1,DC=net"
                logger.info(f"Buscando no AD com filtro: {search_filter}")

                conn.search(search_base, search_filter, attributes=['sAMAccountName', 'givenName', 'sn', 'mail'])
                logger.info(f"Busca no AD realizada. Resultados encontrados: {len(conn.entries)}")

                if conn.entries:
                    entry = conn.entries[0]
                    logger.info(f"Usuário encontrado no AD: {entry.sAMAccountName.value}")
                    user = Usuario(
                        username=entry.sAMAccountName.value,
                        first_name=entry.givenName.value,
                        last_name=entry.sn.value,
                        email=entry.mail.value if entry.mail else None,
                        is_ad_user=True,
                        ativo=True
                    )
                    user.set_unusable_password()
                    user.save()
                    logger.info(f"Usuário {username} importado com sucesso.")
                    messages.success(request, f"Usuário {username} importado com sucesso.")
                else:
                    logger.warning(f"Usuário {username} não encontrado no AD.")
                    messages.error(request, f"Usuário {username} não encontrado no AD.")

        except Exception as e:
            logger.error(f"Erro ao importar usuários do AD: {str(e)}")
            messages.error(request, "Erro ao importar usuários do Active Directory.")
        finally:
            if conn:
                conn.unbind()
            logger.info("Conexão com o LDAP encerrada.")

    return redirect('usuarios:buscar_usuarios_ad')

# Funções relacionadas a grupos

@login_required
def lista_grupos(request):
    grupos = Grupo.objects.all()
    return render(request, 'usuarios/lista_grupos.html', {'grupos': grupos})

@login_required
def cadastrar_grupo(request):
    if request.method == 'POST':
        nome_grupo = request.POST.get('nome_grupo')
        participantes_ids = request.POST.getlist('participantes')

        if not nome_grupo:
            messages.error(request, "O nome do grupo é obrigatório.")
            return render(request, 'usuarios/cadastrar_grupo.html')

        grupo = Grupo(nome=nome_grupo)
        grupo.save()

        for usuario_id in participantes_ids:
            try:
                usuario = Usuario.objects.get(id=usuario_id)
                grupo.participantes.add(usuario)
            except Usuario.DoesNotExist:
                messages.error(request, f"Usuário com ID {usuario_id} não existe.")

        grupo.save()
        messages.success(request, "Grupo criado com sucesso!")

        return redirect('usuarios:lista_grupos')

    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/cadastrar_grupo.html', {'usuarios': usuarios})

# Função para buscar participantes (usuários) via AJAX
@login_required
def buscar_participantes(request):
    query = request.GET.get('q', '')  # Pega o termo da query string
    if query:
        usuarios = Usuario.objects.filter(username__icontains=query)
        resultados = [{'id': usuario.id, 'username': usuario.username} for usuario in usuarios]
    else:
        resultados = []

    return JsonResponse(resultados, safe=False)

@login_required
def editar_grupo(request, grupo_id):
    grupo = get_object_or_404(Grupo, id=grupo_id)
    if request.method == 'POST':
        nome_grupo = request.POST.get('nome_grupo')
        participantes_ids = request.POST.getlist('participantes')

        if nome_grupo:
            grupo.nome = nome_grupo
            grupo.participantes.clear()  # Remove todos os participantes antigos
            for usuario_id in participantes_ids:
                try:
                    usuario = Usuario.objects.get(id=usuario_id)
                    grupo.participantes.add(usuario)
                except Usuario.DoesNotExist:
                    messages.error(request, f"Usuário com ID {usuario_id} não existe.")
            grupo.save()
            messages.success(request, "Grupo atualizado com sucesso!")
            return redirect('usuarios:lista_grupos')
        else:
            messages.error(request, "O nome do grupo é obrigatório.")
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/editar_grupo.html', {'grupo': grupo, 'usuarios': usuarios})

@login_required
def excluir_grupo(request, grupo_id):
    grupo = get_object_or_404(Grupo, id=grupo_id)
    if request.method == 'POST':
        grupo.delete()
        messages.success(request, "Grupo excluído com sucesso!")
        return redirect('usuarios:lista_grupos')
    return render(request, 'usuarios/excluir_grupo.html', {'grupo': grupo})

# Função para sugerir usuários ou grupos conforme a busca
@login_required
def sugestoes(request):
    query = request.GET.get('q', '')
    sugestoes = []

    if query:
        # Buscar usuários
        usuarios = Usuario.objects.filter(username__icontains=query)[:5]
        for usuario in usuarios:
            sugestoes.append({'id': usuario.id, 'nome': usuario.username, 'tipo': 'Usuário'})

        # Buscar grupos
        grupos = Group.objects.filter(name__icontains=query)[:5]
        for grupo in grupos:
            sugestoes.append({'id': grupo.id, 'nome': grupo.name, 'tipo': 'Grupo'})

    return JsonResponse(sugestoes, safe=False)

# Função para liberar permissões
@login_required
@permission_required('auth.change_permission', raise_exception=True)
def liberar_permissoes(request):
    if request.method == 'GET':
        usuario_grupo_id = request.GET.get('id')
        tipo = request.GET.get('tipo')

        if usuario_grupo_id and tipo:
            permissoes = Permission.objects.all()

            permissoes_list = []
            for p in permissoes:
                display_name = get_permission_display_name(p)
                permissoes_list.append({'id': p.id, 'name': display_name})

            if tipo == 'Usuário':
                usuario = get_object_or_404(Usuario, id=usuario_grupo_id)
                permissoes_selecionadas = usuario.user_permissions.values_list('id', flat=True)
                return JsonResponse({
                    'permissoes': permissoes_list,
                    'permissoes_selecionadas': list(permissoes_selecionadas)
                })

            elif tipo == 'Grupo':
                grupo = get_object_or_404(Group, id=usuario_grupo_id)
                permissoes_selecionadas = grupo.permissions.values_list('id', flat=True)
                return JsonResponse({
                    'permissoes': permissoes_list,
                    'permissoes_selecionadas': list(permissoes_selecionadas)
                })
        else:
            return render(request, 'usuarios/liberar_permissoes.html')

def get_permission_display_name(permission):
    codename = permission.codename
    model = permission.content_type.model_class()
    model_name = model._meta.verbose_name

    if codename.startswith('add_'):
        action = _('Pode adicionar')
    elif codename.startswith('change_'):
        action = _('Pode alterar')
    elif codename.startswith('delete_'):
        action = _('Pode excluir')
    elif codename.startswith('view_'):
        action = _('Pode visualizar')
    else:
        # Para permissões personalizadas, usamos o nome diretamente
        return _(permission.name)

    return f'{action} {model_name}'

# Página de perfil
class ProfileView(TemplateView):
    template_name = 'usuarios/profile.html'  # Defina o caminho correto para o template do perfil do usuário

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user  # Passa o objeto do usuário autenticado para o contexto do template
        return context

# Função para logout
class CustomLogoutView(LogoutView):
    next_page = 'login'  # Após logout, redireciona para a página de login

# Função para listar permissões
@login_required
def lista_permissoes(request):
    permissoes = Permission.objects.all()
    return render(request, 'usuarios/lista_permissoes.html', {'permissoes': permissoes})

@login_required
def editar_perfil(request):
    usuario = request.user  # Pega o usuário logado
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=usuario)  # Inclui arquivos de imagem
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('usuarios:editar_perfil')  # Redireciona para a página de perfil
    else:
        form = ProfileForm(instance=usuario)
    
    return render(request, 'usuarios/editar_perfil.html', {'form': form})
