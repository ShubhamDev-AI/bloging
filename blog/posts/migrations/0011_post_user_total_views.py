# Generated by Django 3.1.1 on 2020-10-29 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0010_post_dislike'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='user_total_views',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
