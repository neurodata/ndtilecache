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

#    from celery.contrib import rdb; rdb.set_trace()

import os
import zlib
import cStringIO
import math
import urllib2
import django
import numpy as np
import json
import re
from PIL import Image
import MySQLdb

from django.conf import settings

from cachedb import CacheDB
from dataset import Dataset
from util import getURL
import tilekey
import dbtype
import ocplib
from util import getURL, postURL
from mcfc import mcfcPNG
from windowcutout import windowCutout

from ocpcatmaiderror import OCPCATMAIDError
import logging
logger=logging.getLogger("ocpcatmaid")

from django.db import models
from ocptilecache.models import ProjectServer


class TileCache:

  def __init__ (self, token, slice_type, channels, colors=None):
    """Setup the state for this cache request"""

    self.token = token
    self.slice_type = slice_type
    self.channels = channels
    self.colors = colors

    ## Check for a server for this token
    #projserver = ProjectServer.objects.filter(project=token)
    ##if projserver.exists():
    #  server = projserver[0].server
    #else:
    self.server = settings.SERVER
    
    # set the datasetname
    self.datasetname = "{}_{}_{}".format(self.token, ','.join(self.channels), self.slice_type)
    self.ds = Dataset(self.datasetname)


  def loadData (self, cuboidurl):
    """Load a cube of data into the cache"""

    try:
      m = re.match("^http://.*/ca/\w+/(?:[\w+,]+/)?npz/(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+),(\d+)/$", cuboidurl)
      [res, xmin, xmax, ymin, ymax, zmin, zmax] = [int(i) for i in m.groups()]
    except Exception, e:
      logger.error("Failed to parse url {}".format(cuboidurl))
      raise OCPCATMAIDError("Failed to parse url {}".format(cuboidurl))

    # otherwise load a cube
    logger.warning ("Loading cache for {}".format(cuboidurl))

    # ensure only one requester of a cube at a time
    try:
      self.ds.db.fetchlock(cuboidurl)
    except Exception, e:
      logger.warning("Already fetching {}. Returning.".format(cuboidurl))
      return

    # try block to ensure that we call fetchrelease
    try:

      try:
        # Get cube in question
        f = getURL(cuboidurl)
      except urllib2.URLError, e:
        # release the fetch lock
        self.ds.db.fetchrelease(cuboidurl)
        raise

      zdata = f.read()
      # get the data out of the compressed blob
      pagestr = zlib.decompress(zdata[:])
      pagefobj = cStringIO.StringIO(pagestr)

      # get the cutout data
      cubedata = np.load(pagefobj)

      # properties
      ximagesize, yimagesize, zimagesize = self.ds.imagesz[res]
      (xdim, ydim, zdim) = self.ds.cubedim[res]
      xoffset, yoffset, zoffset = self.ds.offset[res]
      scale = self.ds.scale[res][self.slice_type]

      if xmax == ximagesize or ymax == yimagesize or zmax == zimagesize:
        if self.mcfc:
          # 3d cutout if not a channel database
          cuboid = np.zeros ((zdim,settings.TILESIZE, settings.TILESIZE), dtype = cubedata.dtype)
          cuboid[0:(zmax-zmin), 0:(ymax-ymin), 0:(xmax-xmin)] = cubedata
        else:
          # multi-channel cutout.  turn into false color
          # Check to see is this is a partial cutout if so pad the space
          cuboid = np.zeros((cubedata.shape[0], zdim, settings.TILESIZE, settings.TILESIZE), dtype=cubedata.dtype)
          cuboid[:, 0:(zmax-zmin), 0:(ymax-ymin), 0:(xmax-xmin)] = cubedata
      else:
        cuboid = cubedata

      if self.slice_type == 'xy':
        xtile = xmin / settings.TILESIZE
        ytile = ymin / settings.TILESIZE
        cuboid_args = (xtile, ytile, xmin, xdim)

      elif self.slice_type == 'xz':
        # round to the nearest tile size and scale 
        cmzmin = int(math.floor(((zmin-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        cmzmax = int(math.ceil(((zmax-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        xtile = xmin / settings.TILESIZE
        ztile = cmzmin / settings.TILESIZE
        cuboid_args = (xtile, ztile, zmin, zdim)

      elif self.slice_type == 'yz':
        # round to the nearest tile size and scale 
        cmzmin = int(math.floor(((zmin-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        cmzmax = int(math.floor(((zmax-zoffset)*scale+1)/settings.TILESIZE))*settings.TILESIZE
        ytile = ymin / settings.TILESIZE
        ztile = cmzmin / settings.TILESIZE
        cuboid_args = (ytile, ztile, ymin, ydim)
      
      self.addCuboid(cuboid, res, cuboid_args)
      logger.warning ("Load suceeded for {}".format(cuboidurl))
    
    finally:
      # release the fetch lock
      self.ds.db.fetchrelease(cuboidurl)


  def checkDirHier ( self, res ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" + self.datasetname )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.datasetname )
      # when making the directory, create a dataset

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.datasetname + "/r" + str(res) )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" + self.datasetname + "/r" + str(res) )


  def checkSliceDir ( self, res, sliceno ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.datasetname + "/r" + str(res) + '/sl' + str(sliceno) )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.datasetname + "/r" + str(res) + '/sl' + str(sliceno) )


  def addCuboid( self, cuboid, res, (tile1,tile2,mini,dim)):
    """Add the cutout to cache"""

    self.checkDirHier(res)
    # counter of how many new tiles we get
    newtiles = 0

    # number of tiles
    numtiles = cuboid.shape[0]

    # windodcutout function if window is non-zero
    #if endwindow !=0:
        #windowCutout ( cuboid, (startwindow,endwindow) )

    # add each image slice to memcache
    for value in range(numtiles):

      self.checkSliceDir(res, value+mini)
      tilefname = '{}/{}/r{}/sl{}/{}{}{}{}.png'.format(settings.CACHE_DIR, self.datasetname, res, value+mini,self.slice_type[1], tile2, self.slice_type[0], tile1)
      if self.slice_type == 'xy':
        img = self.tile2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[:,value,:,:] )

      elif self.slice_type == 'xz':
        img = self.tile2WebPNG ( cuboid.shape[3], cuboid.shape[1], cuboid[:,:,value,:] )
      
      elif self.slice_type == 'yz':
        img = self.tile2WebPNG ( cuboid.shape[2], cuboid.shape[1], cuboid[:,:,:,value] )

      import pdb; pdb.set_trace()
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


  #def addXYCuboid ( self, cuboid, res, xtile, ytile, zmin, zdim ):
    #"""Add the cutout to the cache"""

    ## will create the dataset if it doesn't exist
    #self.checkDirHier(res)

    ## get the dataset id for this token
    #(dsidstr,ximagesz,yimagesz,zoffset,zmaxslice,zscale) = self.db.getDataset ( self.datasetname )
    #dsid = int(dsidstr)

    ## counter of how many new tiles we get
    #newtiles = 0

    ## number of tiles
    #if self.channels == None:
      #numtiles = cuboid.shape[0]
    #else:
      #numtiles = cuboid.shape[1]

    ## get the dataset window range
    #startwindow, endwindow = self.info['dataset']['windowrange']

    ## windodcutout function if window is non-zero
    #if endwindow !=0:
        #windowCutout ( cuboid, (startwindow,endwindow) )

    ## add each image slice to memcache
    #for z in range(numtiles):

      #self.checkSliceDir(res,z+zmin)
      #tilefname = '{}/{}/r{}/sl{}/y{}x{}.png'.format(settings.CACHE_DIR,self.datasetname,res,z+zmin,ytile,xtile)
      #if self.channels == None:
        #img = self.tile2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[z,:,:] )
      #else:
        #img = self.channels2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[:,z,:,:] )

      #fobj = open ( tilefname, "w" )
      #img.save ( fobj, "PNG" )
      #try:
        #self.db.insert ( tilekey.tileKey(dsid,res,xtile,ytile,z+zmin), tilefname ) 
        #newtiles += 1 
      #except MySQLdb.Error, e: # ignore duplicate entries
        #if e.args[0] != 1062:  
          #raise

    #self.db.increase ( newtiles )
    #self.harvest()


  #def addXZCuboid ( self, cuboid, res, xtile, ztile, ymin, ydim ):
    #""" Add the cutout to the cache """

    ## will create the dataset if it doesn't exist
    #self.checkDirHier(res)

    ## get the dataset id for this token
    #(dsidstr,ximagesz,yimagesz,zoffset,zmaxslice,zscale) = self.db.getDataset ( self.datasetname )
    #dsid = int(dsidstr)

    ## counter of how many new tiles we get
    #newtiles = 0

    ## number of tiles
    #if self.channels == None:
      #numtiles = cuboid.shape[1]
    #else:
      #numtiles = cuboid.shape[2]

    ## get the dataset window range
    #startwindow, endwindow = self.info['dataset']['windowrange']

    ## windodcutout function if window is non-zero
    #if endwindow !=0:
        #windowCutout ( cuboid, (startwindow,endwindow) )

    ## need to make channels take shape arguments

    ## add each image slice to memcache
    #for y in range(numtiles):

      #self.checkSliceDir(res,y+ymin)
      #tilefname = '{}/{}/r{}/sl{}/z{}x{}.png'.format(settings.CACHE_DIR,self.datasetname,res,y+ymin,ztile,xtile)
      #if self.channels == None:
        #img = self.tile2WebPNG ( cuboid.shape[2], cuboid.shape[0], cuboid[:,y,:] )
      #else:
        ## looks good to here
        #img = self.channels2WebPNG ( cuboid.shape[3], cuboid.shape[1], cuboid[:,:,y,:] )

      ## convert into a catmaid perspective tile.
      #img = img.resize ( [settings.TILESIZE,settings.TILESIZE] )

      #fobj = open ( tilefname, "w" )
      #img.save ( fobj, "PNG" )
      #try:
        #self.db.insert ( tilekey.tileKey(dsid,res,xtile,y+ymin,ztile), tilefname ) 
        #newtiles += 1 
      #except MySQLdb.Error, e: # ignore duplicate entries
        #if e.args[0] != 1062:  
          #raise

    #self.db.increase ( newtiles )
    #self.harvest()


  #def addYZCuboid ( self, cuboid, res, ytile, ztile, xmin, xdim ):
    #""" Add the cutout to the cache """


    ## will create the dataset if it doesn't exist
    #self.checkDirHier(res)

    ## get the dataset id for this token
    #(dsidstr,ximagesz,yimagesz,zoffset,zmaxslice,zscale) = self.db.getDataset ( self.datasetname )
    #dsid = int(dsidstr)

    ## counter of how many new tiles we get
    #newtiles = 0

    ## number of tiles
    #if self.channels == None:
      #numtiles = cuboid.shape[2]
    #else:
      #numtiles = cuboid.shape[3]

    ## get the dataset window range
    #startwindow, endwindow = self.info['dataset']['windowrange']

    ## windodcutout function if window is non-zero
    #if endwindow !=0:
        #windowCutout ( cuboid, (startwindow,endwindow) )

    ## add each image slice to memcache
    #for x in range(numtiles):

      #self.checkSliceDir(res,x+xmin)
      #tilefname = '{}/{}/r{}/sl{}/z{}y{}.png'.format(settings.CACHE_DIR,self.datasetname,res,x+xmin,ztile,ytile)
      #if self.channels == None:
        #img = self.tile2WebPNG ( cuboid.shape[1], cuboid.shape[0], cuboid[:,:,x] )
      #else:
        #img = self.channels2WebPNG ( cuboid.shape[2], cuboid.shape[1], cuboid[:,:,:,x] )

      ## convert into a catmaid perspective tile.
      #img = img.resize ( [settings.TILESIZE,settings.TILESIZE] )

      #fobj = open ( tilefname, "w" )
      #img.save ( fobj, "PNG" )
      #try:
        #self.db.insert ( tilekey.tileKey(dsid,res,x+xmin,ytile,ztile), tilefname ) 
        #newtiles += 1 
      #except MySQLdb.Error, e: # ignore duplicate entries
        #if e.args[0] != 1062:  
          #raise

    #self.db.increase ( newtiles )
    #self.harvest()
  
  
  
  def tile2WebPNG(self, xdim, ydim, tile):
    """Create PNG Images and write to cache for the specified tile"""

    import pdb; pdb.set_trace()
    # Check if it is mcfc tile
    if self.colors is not None:
      return mcfcPNG(tile, self.colors, enhancement=4.0)

    # If it is not a mcfc tile
    else:
      ch = self.ds.channel_list[0]
      # write it as a png file
      if ch.channel_type in dbtype.IMAGE_CHANNELS:

        if ch.channel_datatype in dbtype.DTYPE_uint8:
          return Image.frombuffer ( 'L', [xdim,ydim], tile.flatten(), 'raw', 'L', 0, 1 )
        elif ch.channel_datatype in dbtype.DTYPE_uint16:
          outimage = Image.frombuffer ( 'I;16', [xdim,ydim], tile.flatten(), 'raw', 'I;16', 0, 1)
          return outimage.point(lambda i:i*(1./256)).convert('L')
        elif ch.channel_datatype in dbtype.DTYPE_uint32 :
          return Image.fromarray( tile, 'RGBA')

      elif ch.channel_datatype in dbtype.ANNOTATION_CHANNELS :
        ocplb.recolor_ctype(tile,tile)
        return Image.frombuffer ( 'RGBA', [xdim,ydim], tile.flatten(), 'raw', 'RGBA', 0, 1 )

      else :
        logger.warning ( "Datatype not yet supported".format(self.dbtype) )


  def channels2WebPNG ( self, xdim, ydim, chantile ):
    """generate a false color image from multiple channels"""

    chanlist = self.channels.split(',')
    chanlist = self.channelsToInt ( chanlist )
    
    # get the dataset window range
    startwindow, endwindow = self.info['dataset']['windowrange']
    
    combined_img = np.zeros ((ydim, xdim), dtype=np.uint32 )

    # reduction factor
    if chantile.dtype == np.uint8:
      scaleby = 1
    elif chantile.dtype == np.uint16 and ( startwindow==0 and endwindow==0 ):
      scaleby = 1.0/256 
    elif chantile.dtype == np.uint16 and ( endwindow!=0 ):
      scaleby = 1 
    else:
      assert 0 #RBTODO error

    for i in range(chantile.shape[0]):

      # don't add the zero channels
      if chanlist[i] == 0:
        continue
    
      #data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )

      # First channel is cyan
      if i == 0:
        data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )
        combined_img = np.left_shift(data32,8) + np.left_shift(data32,16)
      # Second is Magenta
      elif i == 1:
        data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )
        combined_img +=  np.left_shift(data32,16) + data32
      # Third is yellow
      elif i == 2:
        data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )
        combined_img +=  np.left_shift(data32,8) + data32
      # Fourth is Red
      elif i == 3:
        data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )
        combined_img +=  data32
      # Fifth is Green
      elif i == 4:
        data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )
        combined_img += np.left_shift(data32,8)
      # Sixth is Blue
      elif i == 5:
        data32 = np.array ( chantile[i] * scaleby, dtype=np.uint32 )
        combined_img +=  np.left_shift(data32,16)
      else:
        assert 0  #RBTODO good error
    
    # Set the alpha channel only for non-zero pixels
    combined_img = np.where ( combined_img > 0, combined_img + 0xFF000000, 0 )
    outimage =  Image.frombuffer ( 'RGBA', (xdim,ydim), combined_img.flatten(), 'raw', 'RGBA', 0, 1 )

    # Enhance the image
    if startwindow==0 and endwindow==0:
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(outimage)
        outimage = enhancer.enhance(4.0)

    return outimage


  def harvest ( self ):
    """Get rid of tiles to respect cache limits"""

    cachesize = int(settings.CACHE_SIZE) * 0x01 << 20

    # determine tht current cache size
    numtiles = self.ds.db.size()

    currentsize = numtiles * settings.TILESIZE * settings.TILESIZE 

    # if we are greater than 95% full.
    if (cachesize - currentsize)*20 < cachesize:

      # start a reclaim process
      from ocptilecache.tasks import reclaim
      reclaim.delay ( )

    else:
      logger.warning ( "Not harvesting cache of {} tiles.  Capacity {}.".format(numtiles,cachesize/512/512))
