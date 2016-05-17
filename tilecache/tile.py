#, Copyright 2014 Open Connectome Project (http://openconnecto.me)
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

import urllib2
import numpy as np
import blosc
import cStringIO
from PIL import Image
import MySQLdb

from util import getURL, getDatasetName
import tilekey
from PIL import Image
from nddataset import NDDataset
from cachedb import CacheDB
from tilecache import TileCache

import s3io
import mcfc
import ndlib
from ndtype import IMAGE_CHANNELS, TIMESERIES_CHANNELS, ANNOTATION_CHANNELS, DTYPE_uint8, DTYPE_uint16, DTYPE_uint32
from ndtilecacheerror import NDTILECACHEError
import logging
logger=logging.getLogger("ndtilecache")

from django.conf import settings
from django.db import models
from django.conf import settings
#from ndtilecache.models import ProjectServer

# Out of Bounds exception
class OOBException(Exception):
  pass

class Tile:
  """Information specific to a given tile in the tilecache"""

  def __init__(self, token, slice_type, res, xvalue, yvalue, zvalue, tvalue, channels, colors=None):

    # load a cache
    self.db = CacheDB()
    # cutout a a tilesize region
    self.tilesize = settings.TILESIZE
    # setting the server name
    self.server = settings.SERVER
    # take the arguments
    self.token = token
    self.slice_type = slice_type
    self.res = res
    self.xvalue = xvalue
    self.yvalue = yvalue
    self.zvalue = zvalue
    self.tvalue = tvalue
    self.channels = channels
    self.colors = colors
    # set the datasetname and load the data set. If it does not exist in the database then one is fetched and created.
    self.ds = NDDataset(getDatasetName(self.token, self.channels, self.colors, self.slice_type))
    self.getFileName() 
    self.tkey = tilekey.tileKey(self.ds.getDatasetId(), self.res, self.xvalue, self.yvalue, self.zvalue, self.tvalue)
  
  def getFileName (self):
    """Genarate the file name based on the values"""
    
    if self.tvalue is None:
      if self.colors:
        self.filename = '{}/{}-{}-{}/r{}/'.format(settings.CACHE_DIR, self.token, ','.join([a+':'+b for a,b in zip(self.channels,self.colors)]), self.slice_type, self.res)
      else:
        self.filename = '{}/{}-{}-{}/r{}/'.format(settings.CACHE_DIR, self.token, ','.join(self.channels), self.slice_type, self.res)
    else:
      self.filename = '{}/{}-{}-{}/t{}/r{}/'.format(settings.CACHE_DIR, self.token, ','.join(self.channels), self.slice_type, self.tvalue, self.res)
      
    if self.slice_type == 'xy':
        self.filename += 'sl{}/y{}x{}.png'.format(self.zvalue, self.yvalue, self.xvalue)
    elif self.slice_type == 'xz':
        self.filename += 'sl{}/z{}x{}.png'.format(self.yvalue, self.zvalue, self.xvalue)
    elif self.slice_type == 'yz':
        self.filename += 'sl{}/z{}y{}.png'.format(self.xvalue, self.zvalue, self.yvalue)
  

  def initForFetch ( self ):
    """Configure the database when you need to get data from remote site"""

    self.tc = TileCache(self.token, self.slice_type, self.channels, self.colors)

    # Check for a server for this token
    # RB TODO you never implemented a different server per project
    #    projserver = ProjectServer.objects.filter(project=token)
    #    if projserver.exists():
    #      server = projserver[0].server
    #    else:
    xdim, ydim, zdim = self.ds.cubedim[self.res]
    xoffset, yoffset, zoffset = self.ds.offset[self.res]
    ximagesize, yimagesize, zimagesize = self.ds.imagesz[self.res]
    scale = self.ds.scale[self.res][self.slice_type]
    xsuperdim, ysuperdim, zsuperdim = self.ds.supercubedim[self.res]


    # these are relative to the cuboids in the server
    if self.slice_type == 'xy':
      
      if self.ds.getS3Backend():
        self.zslab_offset = (self.zvalue - zoffset) % zsuperdim
        self.zslab = (self.zvalue - zoffset) / zsuperdim
        self.zoff = (self.zvalue - zoffset) % zsuperdim
        self.zmin = (self.zslab)*zsuperdim + zoffset
        self.zmax = min ((self.zslab+1)*zsuperdim + zoffset, zimagesize+zoffset+1)
      else:
        self.zslab_offset = (self.zvalue - zoffset) % zdim
        self.zslab = (self.zvalue - zoffset) / zdim
        self.zoff = (self.zvalue - zoffset) % zdim
        self.zmin = (self.zslab)*zdim + zoffset
        self.zmax = min ((self.zslab+1)*zdim + zoffset, zimagesize+zoffset+1)
      
      self.xmin = self.xvalue * self.tilesize
      self.xmax = min ((self.xvalue+1)*self.tilesize + xoffset, ximagesize+xoffset)
      self.ymin = self.yvalue * self.tilesize
      self.ymax = min ((self.yvalue+1)*self.tilesize + yoffset, yimagesize+yoffset)

    elif self.slice_type == 'xz':
      
      if self.ds.getS3Backend():
        self.yslab = (self.yvalue) / ysuperdim
        self.ymin = self.yslab * ysuperdim
        self.ymax = min ((self.yslab+1)*ysuperdim, yimagesize)
      else:
        self.yslab = (self.yvalue) / ydim
        self.ymin = self.yslab * ydim
        self.ymax = min ((self.yslab+1)*ydim, yimagesize)
      
      self.xmin = self.xvalue * self.tilesize
      self.xmax = min ((self.xvalue+1)*self.tilesize, ximagesize)
      # scale the z cutout by the scalefactor
      self.zmin = int((self.zvalue*self.tilesize)/scale + zoffset)
      self.zmax = min(int((self.zvalue+1)*self.tilesize/scale + zoffset), zimagesize+1)

    elif self.slice_type == 'yz':
      
      if self.ds.getS3Backend():
        self.xslab = (self.xvalue) / xsuperdim
        self.xmin = self.xslab * xsuperdim
        self.xmax = min ((self.xslab+1)*xsuperdim, ximagesize)
      else:
        self.xslab = (self.xvalue) / xdim
        self.xmin = self.xslab * xdim
        self.xmax = min ((self.xslab+1)*xdim, ximagesize)
      
      self.ymin = self.yvalue * self.tilesize
      self.ymax = min ((self.yvalue+1)*self.tilesize, yimagesize)
      # scale the z cutout by the scalefactor
      self.zmin = int((self.zvalue*self.tilesize)/scale + zoffset)
      self.zmax = min(int((self.zvalue+1)*self.tilesize/scale + zoffset), zimagesize+1)

    if self.tvalue is not None:
      self.tmin = self.tvalue
      self.tmax = self.tvalue + 1


    # Build the URLs
    # Non time URLs
    if self.tvalue is None:
      # Non time cuboid
      self.cuboid_url = 'http://{}/ca/{}/{}/blosc/{}/{},{}/{},{}/{},{}/'.format(self.server, self.token, ','.join(self.channels), self.res, self.xmin, self.xmax, self.ymin, self.ymax, self.zmin, self.zmax)
      # Simple Tile
      if self.colors is None:
        self.tile_url = "http://{}/catmaid/{}/{}/{}/{}/{}_{}_{}.png".format(self.server, self.token, ','.join(self.channels), self.slice_type, self.zvalue, self.yvalue, self.xvalue, self.res)
      # Mcfc Tile
      else:
        self.tile_url = "http://{}/catmaid/mcfc/{}/{}/{}/{}/{}_{}_{}.png".format(self.server, self.token, ','.join(['{}:{}'.format(a,b) for a,b in zip(self.channels,self.colors)]), self.slice_type, self.zvalue, self.yvalue, self.xvalue, self.res)
    
    # Time URL's
    else:
      self.cuboid_url = 'http://{}/ca/{}/{}/blosc/{}/{},{}/{},{}/{},{}/{},{}/'.format(self.server, self.token, ','.join(self.channels), self.res, self.xmin, self.xmax, self.ymin, self.ymax, self.zmin, self.zmax, self.tmin, self.tmax)
      # Simple Tile
      if self.colors is None:
        self.tile_url = "http://{}/catmaid/{}/{}/{}/{}/{}/{}_{}_{}.png".format(self.server, self.token, ','.join(self.channels), self.slice_type, self.tvalue, self.zvalue, self.yvalue, self.xvalue, self.res)
      # Mcfc Tile
      else:
        print "Not yet supported"
        raise

    if self.zmin >= self.zmax or self.ymin >= self.ymax or self.xmin >= self.xmax:
      raise OOBException("Out of bounds request")


  def fetch (self):
    """Retrieve the tile from the cache or load the cache and return"""

    try:
      # open file and return
      f = open(self.filename)
      self.db.touch (self.tkey)
      return f.read()
    except IOError:
      pass

      try:
        self.initForFetch()
      except OOBException:
        logger.warning("OOB request. Returning black tile. url={}".format(self.tile_url))
        img = Image.new("L", (settings.TILESIZE, settings.TILESIZE))
        fileobj = cStringIO.StringIO()
        img.save(fileobj, "PNG")
        fileobj.seek(0)
        return fileobj.read()
      

      from tasks import fetchcube

      # check if there is S3 backend and do the calls accordingly
      if self.ds.getS3Backend():
        s3_backend = s3io.S3IO(self.ds, self.channels)
        cubedata = s3_backend.getCutout(self.cuboid_url)
        tile_data = cubedata[:, self.zslab_offset, : ,:]
        # fetchcube(self.token, self.slice_type, self.channels, self.colors, self.cuboid_url, cubedata)
        fetchcube.delay (self.token, self.slice_type, self.channels, self.colors, self.cuboid_url, cubedata)
        
        ch = self.ds.getChannelObj(self.channels[0])
        
        # checking the channel type to process the data correctly
        if self.colors:
          img = mcfc.mcfcPNG (tile_data, self.colors)
        elif ch.getChannelType() in IMAGE_CHANNELS + TIMESERIES_CHANNELS:
          
          if ch.getChannelDataType() in DTYPE_uint8:
            img = Image.frombuffer('L', tile_data.shape[1:][::-1], tile_data.flatten(), 'raw', 'L', 0, 1)
          elif ch.getChannelDataType() in DTYPE_uint16:
            if ch.getWindowRange() != [0,0]:
              tile_data = np.uint8(tile_data)
              img = Image.frombuffer('L', tile_data.shape[1:][::-1], tile_data.flatten(), 'raw', 'L', 0, 1)
            else:
              img = Image.frombuffer ( 'I;16', tile_data.shape[1:][::-1], tile_data.flatten(), 'raw', 'I;16', 0, 1)
              img.point(lambda i:i*(1./256)).convert('L')
          elif ch.getChannelDataType() in DTYPE_uint32 :
            img =  Image.fromarray( tile_data[0,:,:], 'RGBA')
        elif ch.getChannelType() in ANNOTATION_CHANNELS:
          tile_data = tile_data[0,:]
          ndlib.recolor_ctype(tile_data, tile_data)
          img = Image.frombuffer('RGBA', tile_data.shape[1:][::-1], tile_data.flatten(), 'raw', 'RGBA', 0, 1)

        fileobj = cStringIO.StringIO()
        img.save ( fileobj, "PNG" )
        fileobj.seek(0)
        return fileobj.read()
      else:
        # call the celery process to fetch the url
        #fetchurl (self.token, self.slice_type, self.channels, self.colors, self.cuboid_url)
        fetchcube.delay (self.token, self.slice_type, self.channels, self.colors, self.cuboid_url)
        # fetchcube (self.token, self.slice_type, self.channels, self.colors, self.cuboid_url)
        logger.warning("Tile fetch {}".format(self.tile_url))
        return getURL(self.tile_url).read()
