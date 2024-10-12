# usuarios/models.py

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings  # Importar settings para acessar AUTH_USER_MODEL

class Usuario(AbstractUser):
    # Campos adicionais, se houver
    ativo = models.BooleanField(default=True)
    gerente = models.BooleanField(default=False)  # Campo para indicar se o usuário é gerente
    is_ad_user = models.BooleanField(default=False)  # Para indicar se é um usuário AD

    # Defina `related_name` para evitar conflitos
    groups = models.ManyToManyField(
        Group,
        related_name='usuarios_groups',
        blank=True,
        help_text="Os grupos aos quais o usuário pertence.",
        verbose_name="grupos"
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='usuarios_user_permissions',
        blank=True,
        help_text="Permissões específicas para o usuário.",
        verbose_name="permissões de usuário"
    )

    def __str__(self):
        return self.username

    # Verifica se o usuário tem permissão para aprovar documentos
    def has_approval_permission(self):
        return self.has_perm('documentos.can_approve')


class Grupo(models.Model):
    nome = models.CharField(max_length=255)
    participantes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='grupos')

    def __str__(self):
        return self.nome
