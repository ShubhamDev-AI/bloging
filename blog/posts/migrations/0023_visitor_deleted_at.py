# Generated by Django 3.1.1 on 2020-11-03 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0022_post_deleted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitor',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
