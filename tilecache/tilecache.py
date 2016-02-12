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

import os
import zlib
import cStringIO
import math
import urllib2
import django
import numpy as np
import json
import blosc
import re
from PIL import Image
import MySQLdb

from django.conf import settings

from cachedb import CacheDB
from dataset import Dataset
from util import getURL, window
import tilekey
from ndtype import IMAGE_CHANNELS, TIMESERIES_CHANNELS, ANNOTATION_CHANNELS, DTYPE_uint8, DTYPE_uint16, DTYPE_uint32 
import ndlib
from util import getURL, postURL, getDatasetName
from mcfc import mcfcPNG
from windowcutout import windowCutout

from ndtilecacheerror import NDTILECACHEError
import logging
logger=logging.getLogger("ndtilecache")

#from django.db import models
#from tilecache.models import ProjectServer

class TileCache:

  def __init__ (self, token, slice_type, channels, colors=None):
    """Setup the state for this cache request"""

    # set the arguments
    self.token = token
    self.slice_type = slice_type
    self.channels = channels
    self.colors = colors
    self.server = settings.SERVER
    self.dataset_name = getDatasetName(self.token, self.channels, self.colors, self.slice_type)
    # set the datasetname
    self.ds = Dataset(self.dataset_name)
  

  def loadCube (self, cuboidurl, cubedata):
    """Load a cube of data into the cache"""

    try:
      # argument of the form /ca/token/channel/blosc/cutoutargs
      m = re.match("^http://.*/ca/\w+/(?:[\w+,]+/)?blosc/(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+)?,?(\d+)?/?$", cuboidurl)
      [res, xmin, xmax, ymin, ymax, zmin, zmax, tmin, tmax] = [int(i) if i is not None else None for i in m.groups()]
    except Exception, e:
      logger.error("Failed to parse url {}".format(cuboidurl))
      raise NDTILECACHEError("Failed to parse url {}".format(cuboidurl))

    # otherwise load a cube
    logger.warning ("Loading cache for {}".format(cuboidurl))

    # ensure only one request of a cube at a time
    try:
      self.ds.db.fetchlock(cuboidurl)
    except Exception, e:
      logger.warning("Already fetching {}. Returning.".format(cuboidurl))
      return

    # try block to ensure that we call fetchrelease
    try:

      try:
        # Get cube in question
        # import pdb; pdb.set_trace()
        import s3io
        test = s3io.S3IO(self.ds, self.channels)
        import time
        start = time.time()
        # cubedata = test.getCutout(cuboidurl)
        print time.time()-start
        # f = getURL(cuboidurl)
        # cubedata = blosc.unpack_array(f.read())
      except urllib2.URLError, e:
        # release the fetch lock
        self.ds.db.fetchrelease(cuboidurl)
        raise

      # get the cutout data

      # properties
      [ximagesize, yimagesize, zimagesize] = self.ds.imagesz[res]
      (xdim, ydim, zdim) = self.ds.cubedim[res]
      (xsuperdim, ysuperdim, zsuperdim) = self.ds.supercubedim[res]
      [xoffset, yoffset, zoffset] = self.ds.offset[res]
      scale = self.ds.scale[res][self.slice_type]

      if xmax == ximagesize or ymax == yimagesize or zmax == zimagesize:
        if self.colors:
          # 3d cutout if not a channel database
          # multi-channel cutout.  turn into false color
          cuboid = np.zeros ((cubedata.shape[0], zdim, settings.TILESIZE, settings.TILESIZE), dtype = cubedata.dtype)
          cuboid[:, 0:(zmax-zmin), 0:(ymax-ymin), 0:(xmax-xmin)] = cubedata
        else:
          # Check to see is this is a partial cutout if so pad the space
          cuboid = np.zeros((cubedata.shape[0], zsuperdim, settings.TILESIZE, settings.TILESIZE), dtype=cubedata.dtype)
          cuboid[:, 0:zsuperdim, 0:(ymax-ymin), 0:(xmax-xmin)] = cubedata[:, :, 0:(ymax-ymin), 0:(xmax-xmin)]
          # cuboid[:, 0:(zmax-zmin), 0:(ymax-ymin), 0:(xmax-xmin)] = cubedata
      else:
        cuboid = cubedata

      if self.slice_type == 'xy':
        xtile = xmin / settings.TILESIZE
        ytile = ymin / settings.TILESIZE
        cuboid_args = (xtile, ytile, zmin, zdim, tmin)

      elif self.slice_type == 'xz':
        # round to the nearest tile size and scale 
        cmzmin = int(math.floor(((zmin-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        cmzmax = int(math.ceil(((zmax-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        xtile = xmin / settings.TILESIZE
        ztile = cmzmin / settings.TILESIZE
        cuboid_args = (xtile, ztile, ymin, ydim, tmin)

      elif self.slice_type == 'yz':
        # round to the nearest tile size and scale 
        cmzmin = int(math.floor(((zmin-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        cmzmax = int(math.floor(((zmax-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        ytile = ymin / settings.TILESIZE
        ztile = cmzmin / settings.TILESIZE
        cuboid_args = (ytile, ztile, zmin, zdim, tmin)
      
      self.addCuboid(cuboid, res, cuboid_args)
      logger.warning ("Load suceeded for {}".format(cuboidurl))
    
    finally:
      # release the fetch lock
      self.ds.db.fetchrelease(cuboidurl)


  def checkDirHier(self, res, time=None):
    """Ensure that the directories for caching exist"""

    try:
      os.stat("{}/{}".format(settings.CACHE_DIR, self.dataset_name))
    except:
      os.makedirs("{}/{}".format(settings.CACHE_DIR, self.dataset_name))

    if time is None:
      try:
        os.stat("{}/{}/r{}".format(settings.CACHE_DIR, self.dataset_name, res))
      except:
        os.makedirs("{}/{}/r{}".format(settings.CACHE_DIR, self.dataset_name, res))
    else:
      try:
        os.stat("{}/{}/t{}/r{}".format(settings.CACHE_DIR, self.dataset_name, time, res))
      except:
        os.makedirs("{}/{}/t{}/r{}".format(settings.CACHE_DIR, self.dataset_name, time, res))


  def checkSliceDir(self, res, slice_no, time=None):
    """Ensure that the directories for caching exist"""

    if time is None:
      try:
        os.stat("{}/{}/r{}/sl{}".format(settings.CACHE_DIR, self.dataset_name, res,slice_no))
      except:
        os.makedirs("{}/{}/r{}/sl{}".format(settings.CACHE_DIR, self.dataset_name, res, slice_no))
    else:
      try:
        os.stat("{}/{}/t{}/r{}/sl{}".format(settings.CACHE_DIR, self.dataset_name, time, res,slice_no))
      except:
        os.makedirs("{}/{}/t{}/r{}/sl{}".format(settings.CACHE_DIR, self.dataset_name, time, res, slice_no))


  def addCuboid( self, cuboid, res, (tile1,tile2,mini,dim,time)):
    """Add the cutout to cache"""
    
    self.checkDirHier(res, time=time)
    # counter of how many new tiles we get
    newtiles = 0

    if time is None:
      # number of tiles
      numtiles = cuboid.shape[1]
      
      for index, channel_name in enumerate(self.channels):
        ch = self.ds.getChannelObj(channel_name)
        cuboid[index,:] = window(cuboid[index,:], ch)

      # add each image slice to memcache
      for value in range(numtiles):

        self.checkSliceDir(res, value+mini)
        tilefname = '{}/{}/r{}/sl{}/{}{}{}{}.png'.format(settings.CACHE_DIR, self.dataset_name, res, value+mini,self.slice_type[1], tile2, self.slice_type[0], tile1)
        if self.slice_type == 'xy':
          img = self.tile2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[:,value,:,:] )
        elif self.slice_type == 'xz':
          img = self.tile2WebPNG ( cuboid.shape[3], cuboid.shape[1], cuboid[:,:,value,:] )
        elif self.slice_type == 'yz':
          img = self.tile2WebPNG ( cuboid.shape[2], cuboid.shape[1], cuboid[:,:,:,value] )

        fobj = open(tilefname, "w")
        img.save(fobj, "PNG")
        try:
          self.ds.db.insert(tilekey.tileKey(self.ds.dsid, res, tile1, tile2, value+mini), tilefname) 
          newtiles += 1 
        except MySQLdb.Error, e: 
          # ignore duplicate entries
          if e.args[0] != 1062:  
            raise
    
    else: 
      # number of tiles
      numtiles = cuboid.shape[2]
      
      for index, channel_name in enumerate(self.channels):
        ch = self.ds.getChannelObj(channel_name)
        cuboid[index,:] = window(cuboid[index,:], ch)

      # add each image slice to memcache
      for value in range(numtiles):

        self.checkSliceDir(res, value+mini, time=time)
        tilefname = '{}/{}/t{}/r{}/sl{}/{}{}{}{}.png'.format(settings.CACHE_DIR, self.dataset_name, time, res, value+mini,self.slice_type[1], tile2, self.slice_type[0], tile1)
        if self.slice_type == 'xy':
          img = self.tile2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[:,:,value,:,:] )
        elif self.slice_type == 'xz':
          img = self.tile2WebPNG ( cuboid.shape[3], cuboid.shape[1], cuboid[:,:,:,value,:] )
        elif self.slice_type == 'yz':
          img = self.tile2WebPNG ( cuboid.shape[2], cuboid.shape[1], cuboid[:,:,:,:,value] )

        fobj = open(tilefname, "w")
        img.save(fobj, "PNG")
        try:
          self.ds.db.insert(tilekey.tileKey(self.ds.dsid, res, tile1, tile2, value+mini), tilefname) 
          newtiles += 1 
        except MySQLdb.Error, e: 
          # ignore duplicate entries
          if e.args[0] != 1062:  
            raise

    self.ds.db.increase(newtiles)
    self.harvest()
  
  def tile2WebPNG(self, xdim, ydim, tile):
    """Create PNG Images and write to cache for the specified tile"""
    
    # Check if it is mcfc tile
    if self.colors is not None:
      return mcfcPNG(tile, self.colors, enhancement=4.0)

    # If it is not a mcfc tile
    else:
      ch = self.ds.getChannelObj(self.channels[0])
      # write it as a png file
      if ch.channel_type in IMAGE_CHANNELS+TIMESERIES_CHANNELS:

        if ch.channel_datatype in DTYPE_uint8:
          return Image.frombuffer ( 'L', [xdim,ydim], tile.flatten(), 'raw', 'L', 0, 1 )
        elif ch.channel_datatype in DTYPE_uint16:
          outimage = Image.frombuffer ( 'I;16', [xdim,ydim], tile.flatten(), 'raw', 'I;16', 0, 1)
          return outimage.point(lambda i:i*(1./256)).convert('L')
        elif ch.channel_datatype in DTYPE_uint32 :
          return Image.fromarray( tile[0,:,:], 'RGBA')

      elif ch.channel_type in ANNOTATION_CHANNELS:
        tile = tile[0,:]
        ndlib.recolor_ctype(tile, tile)
        return Image.frombuffer ( 'RGBA', [xdim,ydim], tile.flatten(), 'raw', 'RGBA', 0, 1 )

      else :
        logger.warning("Datatype not yet supported".format(ch.channel_type))

  def harvest ( self ):
    """Get rid of tiles to respect cache limits"""

    cachesize = int(settings.CACHE_SIZE) * 0x01 << 20

    # determine tht current cache size
    numtiles = self.ds.db.size()
    currentsize = numtiles * settings.TILESIZE * settings.TILESIZE 

    # if we are greater than 95% full.
    if (cachesize - currentsize)*20 < cachesize:
      # start a reclaim process
      from tasks import reclaim
      reclaim.delay()
    else:
      logger.warning("Not harvesting cache of {} tiles. Capacity {}".format(numtiles,cachesize/512/512))
