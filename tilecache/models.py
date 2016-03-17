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

from django.conf import settings
from django.db import models

from ndtype import ISOTROPIC, ZSLICES, UINT8, UINT16, UINT32, UINT64, FLOAT32, IMAGE, TIMESERIES, ANNOTATION, READONLY_TRUE, READONLY_FALSE, PROPAGATED, NOT_PROPAGATED, S3_TRUE, S3_FALSE

# Create your models here
# class ProjectServer ( models.Model ):
  # project = models.CharField(max_length=255, primary_key=True)
  # server = models.CharField(max_length=255)

class Dataset (models.Model):
  dataset_name = models.CharField(max_length=255, unique=True)
  dataset_id = models.AutoField(primary_key=True, unique=True)
  ximagesize = models.IntegerField()
  yimagesize = models.IntegerField()
  zimagesize = models.IntegerField()
  xoffset = models.IntegerField(default=0.0)
  yoffset = models.IntegerField(default=0.0)
  zoffset = models.IntegerField(default=0.0)
  xvoxelres = models.FloatField(default=1.0)
  yvoxelres = models.FloatField(default=1.0)
  zvoxelres = models.FloatField(default=1.0)
  SCALING_CHOICES = (
    (ZSLICES, 'Z Slices'),
    (ISOTROPIC, 'Isotropic'),
  )
  scalingoption = models.IntegerField(default=ZSLICES, choices=SCALING_CHOICES)
  scalinglevels = models.IntegerField(default=0)
  starttime = models.IntegerField(default=0)
  endtime = models.IntegerField(default=0)
  project_name = models.CharField(max_length=255)
  S3BACKEND_CHOICES = (
    (S3_TRUE, 'Yes'),
    (S3_FALSE, 'No'),
  )
  s3backend = models.IntegerField(choices=S3BACKEND_CHOICES, default=S3_TRUE)
  

  class Meta:
    """ Meta """
    # Required to overwrite default table name
    db_table = u"datasets"
    managed = True

  def __unicode__(self):
    return self.dataset_id

class Channel (models.Model):
  channel_name = models.CharField(max_length=255, unique=True)
  dataset = models.ForeignKey(Dataset) 
  CHANNELTYPE_CHOICES = (
    (IMAGE, 'IMAGES'),
    (ANNOTATION, 'ANNOTATIONS'),
    (TIMESERIES,'TIMESERIES'),
  )
  channel_type = models.CharField(max_length=255, choices=CHANNELTYPE_CHOICES)
  resolution = models.IntegerField(default=0)
  PROPAGATE_CHOICES = (
    (NOT_PROPAGATED, 'NOT PROPAGATED'),
    (PROPAGATED, 'PROPAGATED'),
  )
  propagate =  models.IntegerField(choices=PROPAGATE_CHOICES, default=NOT_PROPAGATED)
  DATATYPE_CHOICES = (
    (UINT8, 'uint8'),
    (UINT16, 'uint16'),
    (UINT32, 'uint32'),
    (UINT64, 'uint64'),
    (FLOAT32, 'float32'),
  )
  channel_datatype = models.CharField(max_length=255, choices=DATATYPE_CHOICES)
  READONLY_CHOICES = (
    (READONLY_TRUE, 'Yes'),
    (READONLY_FALSE, 'No'),
  )
  readonly =  models.IntegerField(choices=READONLY_CHOICES, default=READONLY_FALSE)
  startwindow = models.IntegerField(default=0)
  endwindow = models.IntegerField(default=0)

  class Meta:
    """Meta"""
    # Required to overwrite default table name
    db_table = u"channels"
    managed = True
    unique_together = ('channel_name', 'dataset',)
  

#class Fetching ( models.Model ):
  #url = models.CharField(max_length=255, primary_key=True)

  #class Meta:
    #""" Meta """
    #db_table = u"fetching"
    #managed = True

  #def __unicode__(self):
    #return self.url

  
#class Metadata ( models.Model ):
  #numtiles = models.IntegerField(primary_key=True)

  #class Meta:
    #""" Meta """
    #db_table = u"metadata"
    #managed = True

  #def __unicode__(self):
    #return self.numtiles

#class Contents ( models.Model ):
  #key = models.BigIntegerField(primary_key=True, default=0)
  #filename = models.CharField(max_length=255)
  #reftime = models.TimeField(auto_now=True,auto_now_add=True)

  #class Meta:
    #""" Meta """
    #db_table = u"contents"
    #managed = True

  #def __unicode__(self):
    #return self.key
