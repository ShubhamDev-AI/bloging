# Generated by Django 3.1.1 on 2020-11-03 10:22

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('posts', '0020_auto_20201103_1403'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='visitor',
            options={'verbose_name': 'Visitor', 'verbose_name_plural': 'Visitors'},
        ),
        migrations.AddField(
            model_name='visitor',
            name='content_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='visitors', to='contenttypes.contenttype'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='visitor',
            name='headers',
            field=models.TextField(blank=True, null=True, verbose_name='Headers'),
        ),
        migrations.AddField(
            model_name='visitor',
            name='ip_address',
            field=models.CharField(default=django.utils.timezone.now, max_length=40, verbose_name='IP Address'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='visitor',
            name='object_id',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='visitor',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterUniqueTogether(
            name='visitor',
            unique_together={('ip_address', 'object_id', 'content_type')},
        ),
        migrations.RemoveField(
            model_name='visitor',
            name='created',
        ),
        migrations.RemoveField(
            model_name='visitor',
            name='ip',
        ),
        migrations.RemoveField(
            model_name='visitor',
            name='modified',
        ),
        migrations.RemoveField(
            model_name='visitor',
            name='post',
        ),
    ]
