# Generated by Django 5.1.2 on 2024-10-20 01:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0011_usuario_profile_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='profile_photo',
            field=models.ImageField(blank=True, default='default_user.png', null=True, upload_to='profile_photos/'),
        ),
    ]
