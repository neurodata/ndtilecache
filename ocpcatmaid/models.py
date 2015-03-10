# Copyright 2014 Open Connectome Project (http://openconnecto.me)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.db import models

# Create your models here
class Datasets ( models.Model ):
  dataset_name = models.CharField(max_length=255, primary_key=True)
  dataset_id = models.AutoField(unique=True)
  ximagesize = models.IntegerField()
  yimagesize = models.IntegerField()
  zimagesize = models.IntegerField()
  zoffset = models.IntegerField()
  zscale = models.FloatField(default=1.0)

  class Meta:
    """ Meta """
    db_table = u"datasets"
    managed = True

  def __unicode__(self):
    return self.dataset_name


class Fetching ( models.Model ):
  url = models.CharField(max_length=255, primary_key=True)

  class Meta:
    """ Meta """
    db_table = u"fetching"
    managed = True

  def __unicode__(self):
    return self.url

  
class Metadata ( models.Model ):
  numtiles = models.IntegerField(primary_key=True)

  class Meta:
    """ Meta """
    db_table = u"metadata"
    managed = True

  def __unicode__(self):
    return self.numtiles

class Contents ( models.Model ):
  highkey = models.BigIntegerField(primary_key=True, default=0)
  lowkey = models.BigIntegerField(primary_key=True, default=0)
  filename = models.CharField(max_length=255)
  reftime = models.TimeField(auto_now=True,auto_now_add=True)

  class Meta:
    """ Meta """
    db_table = u"contents"
    managed = True

  def __unicode__(self):
    return self.highkey
