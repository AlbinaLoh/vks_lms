# Generated by Django 4.0.4 on 2025-05-31 20:09

from django.db import migrations
import froala_editor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_news_content_alter_news_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='content',
            field=froala_editor.fields.FroalaField(verbose_name='Содержание'),
        ),
    ]
