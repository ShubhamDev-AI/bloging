# Generated by Django 3.1.1 on 2020-11-05 08:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField()),
                ('last_active', models.DateTimeField(auto_now=True)),
                ('count', models.IntegerField(default=1)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('day', 'user')},
            },
        ),
    ]
