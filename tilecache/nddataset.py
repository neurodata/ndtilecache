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

import json
import shutil
from operator import mul
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from cachedb import CacheDB
from models import Dataset, Channel
from ndchannel import NDChannel
from ndtype import ZSLICES, ISOTROPIC, ND_scalingtoint, SUPERCUBESIZE, S3_TRUE
from restutil import getURL

from ndtilecacheerror import NDTILECACHEError
import logging
logger=logging.getLogger("ndtilecache")


class NDDataset:
  """Dataset interface for each cache Dataset"""

  def __init__(self, dataset_name):
    """Intialize the dataset"""
    
    self.dataset_name = dataset_name
    self.channel_list = []
    self.db = CacheDB()

    try:
      self.ds = Dataset.objects.get(dataset_name = dataset_name)
    except ObjectDoesNotExist as e:
      self.fetchDataset()

    self.populateDataset()
  

  def fetchDataset (self):
    """Fetch a dataset to the list of cacheable datasets"""

    token = self.dataset_name.split('-')[0]
    
    try:
      json_info = json.loads(getURL('http://{}/ocpca/{}/info/'.format(settings.SERVER, token)))
    except Exception as e:
      logger.error("Token {} doesn not exist on the backend {}".format(token, settings.SERVER))
      raise NDTILECACHEError("Token {} doesn not exist on the backend {}".format(token, settings.SERVER))
    
    ximagesize, yimagesize, zimagesize = json_info['dataset']['imagesize']['0']
    xoffset, yoffset, zoffset = json_info['dataset']['offset']['0']
    xvoxelres, yvoxelres, zvoxelres = json_info['dataset']['voxelres']['0']
    scalinglevels = json_info['dataset']['scalinglevels']
    scalingoption = ND_scalingtoint[json_info['dataset']['scaling']]
    starttime, endtime = json_info['dataset']['timerange']
    project_name = json_info['project']['name']
    s3backend = json_info['project']['s3backend']
    
    self.ds = Dataset(dataset_name=self.dataset_name, ximagesize=ximagesize, yimagesize=yimagesize, zimagesize=zimagesize, xoffset=xoffset, yoffset=yoffset, zoffset=zoffset, xvoxelres=xvoxelres, yvoxelres=yvoxelres, zvoxelres=zvoxelres, scalingoption=scalingoption, scalinglevels=scalinglevels, starttime=starttime, endtime=endtime, project_name=project_name, s3backend=s3backend)
    self.ds.save()

    for channel_name in json_info['channels'].keys():
      channel_name = channel_name
      dataset_id = self.dataset_name
      channel_type = json_info['channels'][channel_name]['channel_type']
      channel_datatype = json_info['channels'][channel_name]['datatype']
      startwindow, endwindow = json_info['channels'][channel_name]['windowrange']
      propagate = json_info['channels'][channel_name]['propagate'] 
      readonly = json_info['channels'][channel_name]['readonly']
      ch = Channel(channel_name=channel_name, dataset=self.ds, channel_type=channel_type, channel_datatype=channel_datatype, startwindow=startwindow, endwindow=endwindow, propagate=propagate, readonly=readonly)
      ch.save()


  def populateDataset (self):
    """Populate a dataset information using the information stored"""

    self.resolutions = []
    self.cubedim = {}
    self.supercubedim = {}
    self.imagesz = {}
    self.offset = {}
    self.voxelres = {}
    self.scale = {}
    self.timerange = [self.ds.starttime, self.ds.endtime]

    for i in range(self.ds.scalinglevels+1):

      # add this level to the resolutions
      self.resolutions.append( i )

      # set the image size. the scaled down image rounded up to the nearest cube
      xpixels = ((self.ds.ximagesize-1)/2**i)+1
      ypixels = ((self.ds.yimagesize-1)/2**i)+1
      if self.ds.scalingoption == ZSLICES:
        zpixels = self.ds.zimagesize
      else:
        zpixels = ((self.ds.zimagesize-1)/2**i)+1
      
      self.imagesz[i] = [xpixels, ypixels, zpixels]

      # set the offset
      xoffseti = 0 if self.ds.xoffset == 0 else ((self.ds.xoffset)/2**i)
      yoffseti = 0 if self.ds.yoffset == 0 else ((self.ds.yoffset)/2**i)
      if self.ds.zoffset == 0:
        zoffseti = 0
      else:
        if self.ds.scalingoption == ZSLICES:
          zoffseti = self.ds.zoffset
        else:
          zoffseti = ((self.ds.zoffset)/2**i)
      
      self.offset[i] = [ xoffseti, yoffseti, zoffseti ]

      # set the voxelresolution
      xvoxelresi = self.ds.xvoxelres * float(2**i)
      yvoxelresi = self.ds.yvoxelres * float(2**i)
      zvoxelresi = self.ds.zvoxelres if self.ds.scalingoption == ZSLICES else self.ds.zvoxelres*float(2**i)
            
      self.voxelres[i] = [ xvoxelresi, yvoxelresi, zvoxelresi ]
      self.scale[i] = { 'xy':xvoxelresi/yvoxelresi , 'yz':zvoxelresi/xvoxelresi, 'xz':zvoxelresi/yvoxelresi }
       
      # choose the cubedim as a function of the zscale
      #  this may need to be changed.  
      if self.ds.scalingoption == ZSLICES:
        if float(self.ds.zvoxelres/self.ds.xvoxelres)/(2**i) >  0.5:
          self.cubedim[i] = [128, 128, 16]
        else:
          self.cubedim[i] = [64, 64, 64]
      
      if self.ds.s3backend == S3_TRUE:
        self.supercubedim[i] = map(mul, self.cubedim[i], SUPERCUBESIZE)
      else:
        self.supercubedim[i] = self.cubedim[i]

      # Make an exception for bock11 data -- just an inconsistency in original ingest
      if self.ds.ximagesize == 135424 and i == 5:
        self.cubedim[i] = [128, 128, 16]
      else:
        # RB what should we use as a cubedim?
        self.cubedim[i] = [128, 128, 16]

  def removeDataset(self):
    """Remove a dataset"""
    
    self.ds.delete()
    
    try:
      shutil.rmtree("{}/{}".format(settings.CACHE_DIR, self.dataset_name))
    except Exception as e:
      logger.error("Failed to remove dataset directories at {}. Error {}. Manual cleanup may be necessary.".format(self.dataset_name, e))
      raise NDTILECACHEError("Failed to remove dataset directories at {}. Error {}. Manual cleanup may be necessary.".format(self.dataset_name, e))
  
  # Accessors
  def getDatasetName(self):
    return self.ds.dataset_name
  
  def getDatasetId(self):
    return self.ds.dataset_id

  def getS3Backend(self):
    return self.ds.s3backend

  def getImageSize(self, resolution):
    return self.imagesz[resolution]

  def getVoxelRes(self, resolution):
    return self.voxelres[resolution]

  def getProjectName(self):
    return self.ds.project_name
  
  def getChannelObj(self, channel_name):
    """Return a channel object"""
    
    return NDChannel(channel_name, self.ds)
    # logger.error("Channel {} does not exist for the dataset {}".format(channel_name, self.dataset_name))
    # raise NDTILECACHEError("Channel {} does not exist for the dataset {}".format(channel_name, self.dataset_name))
