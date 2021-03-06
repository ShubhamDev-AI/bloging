# Generated by Django 3.1.1 on 2020-11-03 08:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0016_block'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='follow',
            options={'ordering': ('-created',), 'verbose_name': 'Following', 'verbose_name_plural': 'Following'},
        ),
        migrations.CreateModel(
            name='Visitor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.CharField(max_length=40)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_visitor', to='posts.post')),
            ],
        ),
    ]
