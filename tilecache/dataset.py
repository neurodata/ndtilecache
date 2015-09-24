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
from django.conf import settings

from cachedb import CacheDB
from dbtype import ZSLICES, ISOTROPIC
from util import getURL
import dbtype

from ocptilecacheerror import OCPTILECACHEError
import logging
logger=logging.getLogger("ocptilecache")


class Dataset:
  """Dataset interface for each cache Dataset"""

  def __init__(self, dataset_name):
    """Intialize the dataset"""

    self.db = CacheDB()
    self.dataset_name = dataset_name
    self.channel_list = []

    try:
      self.db.getDataset(self)
    except Exception:
      self.fetchDataset()
      self.db.addDataset(self)
      self.db.getDataset(self)

    self.populateDataset()
  

  def fetchDataset (self):
    """Fetch a dataset to the list of cacheable datasets"""

    token = self.dataset_name.split('-')[0]
    f = getURL('http://{}/ocpca/{}/info/'.format(settings.SERVER, token))
    info = json.loads(f.read())
    self.ximagesz, self.yimagesz, self.zimagesz = info['dataset']['imagesize']['0']
    self.xoffset, self.yoffset, self.zoffset = info['dataset']['offset']['0']
    self.xvoxelres, self.yvoxelres, self.zvoxelres = info['dataset']['voxelres']['0']
    self.scalinglevels = info['dataset']['scalinglevels']
    self.scalingoption = dbtype.OCP_scalingtoint[info['dataset']['scaling']]
    self.starttime, self.endtime = info['dataset']['timerange']

    for channel_name in info['channels'].keys():
      self.channel_list.append(Channel(channel_name, self.dataset_name, info['channels'][channel_name]['channel_type'], info['channels'][channel_name]['datatype'], *info['channels'][channel_name]['windowrange']))


  def populateDataset (self):
    """Populate a dataset information using the information stored"""

    self.resolutions = []
    self.cubedim = {}
    self.imagesz = {}
    self.offset = {}
    self.voxelres = {}
    self.scale = {}
    self.timerange = [self.starttime, self.endtime]

    if not self.channel_list:
      self.db.getChannel(self)

    for i in range(self.scalinglevels+1):

      # add this level to the resolutions
      self.resolutions.append( i )

      # set the image size. the scaled down image rounded up to the nearest cube
      xpixels = ((self.ximagesz-1)/2**i)+1
      ypixels = ((self.yimagesz-1)/2**i)+1
      if self.scalingoption == ZSLICES:
        zpixels = self.zimagesz
      else:
        zpixels = ((self.ds.zimagesz-1)/2**i)+1
      
      self.imagesz[i] = [xpixels, ypixels, zpixels]

      # set the offset
      xoffseti = 0 if self.xoffset == 0 else ((self.xoffset)/2**i)
      yoffseti = 0 if self.yoffset == 0 else ((self.yoffset)/2**i)
      if self.zoffset == 0:
        zoffseti = 0
      else:
        if self.scalingoption == ZSLICES:
          zoffseti = self.zoffset
        else:
          zoffseti = ((self.zoffset)/2**i)
      
      self.offset[i] = [ xoffseti, yoffseti, zoffseti ]

      # set the voxelresolution
      xvoxelresi = self.xvoxelres * float(2**i)
      yvoxelresi = self.yvoxelres * float(2**i)
      zvoxelresi = self.zvoxelres if self.scalingoption == ZSLICES else self.zvoxelres*float(2**i)
            
      self.voxelres[i] = [ xvoxelresi, yvoxelresi, zvoxelresi ]
      self.scale[i] = { 'xy':xvoxelresi/yvoxelresi , 'yz':zvoxelresi/xvoxelresi, 'xz':zvoxelresi/yvoxelresi }
       
      # choose the cubedim as a function of the zscale
      #  this may need to be changed.  
      if self.scalingoption == ZSLICES:
        if float(self.zvoxelres/self.xvoxelres)/(2**i) >  0.5:
          self.cubedim[i] = [128, 128, 16]
        else:
          self.cubedim[i] = [64, 64, 64]

      # Make an exception for bock11 data -- just an inconsistency in original ingest
      if self.ximagesz == 135424 and i == 5:
        self.cubedim[i] = [128, 128, 16]
      else:
        # RB what should we use as a cubedim?
        self.cubedim[i] = [128, 128, 16]

  def removeDataset(self):
    """Remove a dataset"""
    
    self.db.removeDataset(self.dataset_name)
    import shutil
    try:
      shutil.rmtree("{}/{}".format(settings.CACHE_DIR, self.dataset_name))
    except Exception, e:
      logger.warning ("Failed to remove dataset directories at {}. Error {}. Manual cleanup may be necessary.".format(self.dataset_name, e))


  def getChannelObj(self, channel_name):
    """Return a channel object"""

    for ch in self.channel_list:
      if ch.getChannelName() == channel_name:
        return ch

    logger.warning("Channel {} does not exist for the dataset {}".format(channel_name, self.dataset_name))
    raise OCPTILECACHEError("Channel {} does not exist for the dataset {}".format(channel_name, self.dataset_name))


class Channel:

  def __init__(self, channel_name, dataset, channel_type, channel_datatype, startwindow, endwindow):
    """Intialize the channel"""

    self.channel_name = channel_name
    self.dataset = dataset
    self.channel_type = channel_type
    self.channel_datatype = channel_datatype
    self.startwindow = startwindow
    self.endwindow = endwindow

  def getWindowRange(self):
    return [self.startwindow, self.endwindow]
  def getChannelType(self):
    return self.channel_type
  def getDataType(self):
    return self.channel_datatype
  def getChannelName(self):
    return self.channel_name
  def getDataset(self):
    return self.dataset
