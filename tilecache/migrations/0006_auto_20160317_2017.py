# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-18 00:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tilecache', '0005_auto_20160317_1525'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='channel_name',
            field=models.CharField(max_length=255),
        ),
    ]
