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

import cachedb
import tilekey
import dbtype

from ocpca_cy import recolor_cy
from windowcutout import windowCutout

import logging
logger=logging.getLogger("ocpcatmaid")

from django.db import models
from ocptilecache.models import ProjectServer


class TileCache:

  def __init__ (self, token, slicetype, channels):
    """Setup the state for this cache request"""

    self.token = token
    self.slicetype = slicetype
    self.channels = channels

    self.db = cachedb.CacheDB (  )

    ## Check for a server for this token
    #projserver = ProjectServer.objects.filter(project=token)
    ##if projserver.exists():
    #  server = projserver[0].server
    #else:
    server = settings.SERVER

    url = 'http://{}/ocpca/{}/info/'.format(server,self.token)
    try:
      f = urllib2.urlopen ( url )
    except urllib2.URLError, e:
      raise

    self.info = json.loads ( f.read() )
    self.dbtype = self.info['project'].get('projecttype')

    # set the datasetname
    if self.channels == None:
      self.datasetname = self.token + "_" + self.slicetype 
    else:
      self.datasetname = self.token + "_" + self.slicetype + '_' + self.channels


  def loadData (self, cuboidurl):
    """Load a cube of data into the cache"""

    p = re.compile('^http://.*/ca/\w+/npz/(?:([\w,-]+)/)?(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+),(\d+).*$')
    m = p.match(cuboidurl)
    if m == None:
      logger.error("Failed to parse url {}".format(cuboidurl))
      raise Exception ("Failed to parse url {}".format(cuboidurl))

    channels = m.group(1)
    res = int(m.group(2))
    xmin = int(m.group(3))
    xmax = int(m.group(4))
    ymin = int(m.group(5))
    ymax = int(m.group(6))
    zmin = int(m.group(7))
    zmax = int(m.group(8))

    # otherwise load a cube
    logger.warning ("Loading cache for %s" % (cuboidurl))

    # ensure only one requester of a cube at a time
    try:
      self.db.fetchlock(cuboidurl)
    except Exception, e:
      logger.warning("Already fetching {}.  Returning.".format(cuboidurl))
      return

    # try block to ensure that we call fetchrelease
    try:

      # Get cube in question
      try:
        f = urllib2.urlopen ( cuboidurl )
      except urllib2.URLError, e:
        # release the fetch lock
        self.db.fetchrelease(cuboidurl)
        raise

      zdata = f.read ()
      # get the data out of the compressed blob
      pagestr = zlib.decompress ( zdata[:] )
      pagefobj = cStringIO.StringIO ( pagestr )

      # get the cutout data
      cubedata=np.load(pagefobj)

      # image properties
      ximagesize, yimagesize = self.info['dataset']['imagesize']['{}'.format(res)]
      zimagesize = self.info['dataset']['slicerange'][1]+1

      # cube at a time
      ( xdim,ydim,zdim ) = self.info['dataset']['cube_dimension']['{}'.format(res)]

      if self.slicetype == 'xy':

        # 3d cutout if not a channel database
        if self.channels == None:

          # Check to see is this is a partial cutout if so pad the space
          if xmax==ximagesize or ymax==yimagesize or zmax==zimagesize:
            cuboid = np.zeros ( (zdim,settings.TILESIZE,settings.TILESIZE), dtype=cubedata.dtype)
            cuboid[0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
          else:
            cuboid = cubedata

        # multi-channel cutout.  turn into false color
        else:

          # Check to see is this is a partial cutout if so pad the space
          if xmax==ximagesize or ymax==yimagesize or zmax==zimagesize:
            cuboid = np.zeros ( (cubedata.shape[0],zdim,settings.TILESIZE,settings.TILESIZE), dtype=cubedata.dtype)
            cuboid[:,0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
          else:
            cuboid = cubedata

        xtile = xmin / settings.TILESIZE
        ytile = ymin / settings.TILESIZE

        self.addXYCuboid ( cuboid, res, xtile, ytile, zmin, zdim )

      elif self.slicetype == 'xz':

        # translate the cutout into catmaid space (based on scalefactor)
        scalefactor = self.info['dataset']['zscale']['{}'.format(res)]

        # round to the nearest tile size and scale 
        zoffset = self.info['dataset']['slicerange'][0]
        cmzmin = int(math.floor(((zmin-zoffset)*scalefactor+1)/settings.TILESIZE))*settings.TILESIZE
        cmzmax = int(math.floor(((zmax-zoffset)*scalefactor+1)/settings.TILESIZE))*settings.TILESIZE

        # 3d cutout if not a channel database
        if self.channels == None:

          # Check to see is this is a partial cutout if so pad the space
          if (xmax==ximagesize or ymax==yimagesize or cmzmax==zimagesize):
            cuboid = np.zeros ((int(settings.TILESIZE/scalefactor),ydim,settings.TILESIZE), dtype=cubedata.dtype)
            cuboid[0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
          else:
            cuboid = cubedata

        else:
          # Check to see is this is a partial cutout if so pad the space
          if xmax==ximagesize or ymax==yimagesize or cmzmax==zimagesize:
            cuboid = np.zeros((cubedata.shape[0],int(settings.TILESIZE/scalefactor),ydim,settings.TILESIZE), dtype=cubedata.dtype)
            cuboid[:,0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
          else:
            cuboid = cubedata

        xtile = xmin / settings.TILESIZE
        ztile = cmzmin / settings.TILESIZE

        self.addXZCuboid ( cuboid, res, xtile, ztile, ymin, ydim )

      elif self.slicetype == 'yz':

        # translate the cutout into catmaid space (based on scalefactor)
        scalefactor = self.info['dataset']['zscale']['{}'.format(res)]

        # round to the nearest tile size and scale 
        zoffset = self.info['dataset']['slicerange'][0]
        cmzmin = int(math.floor(((zmin-zoffset)*scalefactor+1)/settings.TILESIZE))*settings.TILESIZE
        cmzmax = int(math.floor(((zmax-zoffset)*scalefactor+1)/settings.TILESIZE))*settings.TILESIZE

        # 3d cutout if not a channel database
        if self.channels == None:

          # Check to see is this is a partial cutout if so pad the space
          if (xmax==ximagesize or ymax==yimagesize or cmzmax==zimagesize):
            cuboid = np.zeros ((int(settings.TILESIZE/scalefactor),settings.TILESIZE,xdim), dtype=cubedata.dtype)
            cuboid[0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
          else:
            cuboid = cubedata

        else:
          # Check to see is this is a partial cutout if so pad the space
          if xmax==ximagesize or ymax==yimagesize or cmzmax==zimagesize:

            assert(0) # RB below broke 4 dimensions in wrong place
            cuboid = np.zeros ((int(cubedata.shape[0]/scalefactor),settings.TILESIZE,ydim,settings.TILESIZE), dtype=cubedata.dtype)
            cuboid[:,0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
          else:
            cuboid = cubedata

        ytile = ymin / settings.TILESIZE
        ztile = cmzmin / settings.TILESIZE

        self.addYZCuboid ( cuboid, res, ytile, ztile, xmin, xdim )
      
      logger.warning ("Load suceeded for %s" % (cuboidurl))
    
    finally:

      # release the fetch lock
      self.db.fetchrelease(cuboidurl)


  def checkDirHier ( self, res ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" + self.datasetname )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.datasetname )
      # when making the directory, create a dataset
      try:
        self.db.addDataset ( self.datasetname )
      except MySQLdb.Error, e:
        logger.warning ("Failed to create dataset.  Already exists in database, but not cache. {}:{}.".format(e.args[0], e.args[1]))

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


  def addXYCuboid ( self, cuboid, res, xtile, ytile, zmin, zdim ):
    """Add the cutout to the cache"""

    # will create the dataset if it doesn't exist
    self.checkDirHier(res)

    # get the dataset id for this token
    dsid = self.db.getDatasetKey ( self.datasetname )

    # counter of how many new tiles we get
    newtiles = 0

    # number of tiles
    if self.channels == None:
      numtiles = cuboid.shape[0]
    else:
      numtiles = cuboid.shape[1]

    # get the dataset window range
    startwindow, endwindow = self.info['dataset']['windowrange']

    # windodcutout function if window is non-zero
    if endwindow !=0:
        windowCutout ( cuboid, (startwindow,endwindow) )

    # add each image slice to memcache
    for z in range(numtiles):

      self.checkSliceDir(res,z+zmin)
      tilefname = '{}/{}/r{}/sl{}/y{}x{}.png'.format(settings.CACHE_DIR,self.datasetname,res,z+zmin,ytile,xtile)
      if self.channels == None:
        img = self.tile2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[z,:,:] )
      else:
        img = self.channels2WebPNG ( settings.TILESIZE, settings.TILESIZE, cuboid[:,z,:,:] )

      fobj = open ( tilefname, "w" )
      img.save ( fobj, "PNG" )
      try:
        self.db.insert ( tilekey.tileKey(dsid,res,xtile,ytile,z+zmin), tilefname ) 
        newtiles += 1 
      except MySQLdb.Error, e: # ignore duplicate entries
        if e.args[0] != 1062:  
          raise

    self.db.increase ( newtiles )
    self.harvest()


  def addXZCuboid ( self, cuboid, res, xtile, ztile, ymin, ydim ):
    """ Add the cutout to the cache """

    # will create the dataset if it doesn't exist
    self.checkDirHier(res)

    # get the dataset id for this token
    dsid = self.db.getDatasetKey ( self.datasetname )

    # counter of how many new tiles we get
    newtiles = 0

    # number of tiles
    if self.channels == None:
      numtiles = cuboid.shape[1]
    else:
      numtiles = cuboid.shape[2]

    # get the dataset window range
    startwindow, endwindow = self.info['dataset']['windowrange']

    # windodcutout function if window is non-zero
    if endwindow !=0:
        windowCutout ( cuboid, (startwindow,endwindow) )

    # need to make channels take shape arguments

    # add each image slice to memcache
    for y in range(numtiles):

      self.checkSliceDir(res,y+ymin)
      tilefname = '{}/{}/r{}/sl{}/z{}x{}.png'.format(settings.CACHE_DIR,self.datasetname,res,y+ymin,ztile,xtile)
      if self.channels == None:
        img = self.tile2WebPNG ( cuboid.shape[2], cuboid.shape[0], cuboid[:,y,:] )
      else:
        # looks good to here
        img = self.channels2WebPNG ( cuboid.shape[3], cuboid.shape[1], cuboid[:,:,y,:] )

      # convert into a catmaid perspective tile.
      img = img.resize ( [settings.TILESIZE,settings.TILESIZE] )

      fobj = open ( tilefname, "w" )
      img.save ( fobj, "PNG" )
      try:
        self.db.insert ( tilekey.tileKey(dsid,res,xtile,y+ymin,ztile), tilefname ) 
        newtiles += 1 
      except MySQLdb.Error, e: # ignore duplicate entries
        if e.args[0] != 1062:  
          raise

    self.db.increase ( newtiles )
    self.harvest()


  def addYZCuboid ( self, cuboid, res, ytile, ztile, xmin, xdim ):
    """ Add the cutout to the cache """


    # will create the dataset if it doesn't exist
    self.checkDirHier(res)

    # get the dataset id for this token
    dsid = self.db.getDatasetKey ( self.datasetname )

    # counter of how many new tiles we get
    newtiles = 0

    # number of tiles
    if self.channels == None:
      numtiles = cuboid.shape[2]
    else:
      numtiles = cuboid.shape[3]

    # get the dataset window range
    startwindow, endwindow = self.info['dataset']['windowrange']

    # windodcutout function if window is non-zero
    if endwindow !=0:
        windowCutout ( cuboid, (startwindow,endwindow) )

    # add each image slice to memcache
    for x in range(numtiles):

      self.checkSliceDir(res,x+xmin)
      tilefname = '{}/{}/r{}/sl{}/z{}y{}.png'.format(settings.CACHE_DIR,self.datasetname,res,x+xmin,ztile,ytile)
      if self.channels == None:
        img = self.tile2WebPNG ( cuboid.shape[1], cuboid.shape[0], cuboid[:,:,x] )
      else:
        img = self.channels2WebPNG ( cuboid.shape[2], cuboid.shape[1], cuboid[:,:,:,x] )

      # convert into a catmaid perspective tile.
      img = img.resize ( [settings.TILESIZE,settings.TILESIZE] )

      fobj = open ( tilefname, "w" )
      img.save ( fobj, "PNG" )
      try:
        self.db.insert ( tilekey.tileKey(dsid,res,x+xmin,ytile,ztile), tilefname ) 
        newtiles += 1 
      except MySQLdb.Error, e: # ignore duplicate entries
        if e.args[0] != 1062:  
          raise

    self.db.increase ( newtiles )
    self.harvest()
  
  
  
  def tile2WebPNG ( self, xdim, ydim, tile ):
    """Create PNG Images and write to cache for the specified tile"""

    # write it as a png file
    if self.dbtype == dbtype.IMAGES_8bit :
      return Image.frombuffer ( 'L', [xdim,ydim], tile.flatten(), 'raw', 'L', 0, 1 )
    elif self.dbtype == dbtype.ANNOTATIONS :
      recolor_cy (tile, tile)
      return Image.frombuffer ( 'RGBA', [xdim,ydim], tile.flatten(), 'raw', 'RGBA', 0, 1 )
    elif self.dbtype == dbtype.IMAGES_16bit :
      outimage = Image.frombuffer ( 'I;16', [xdim,ydim], tile.flatten(), 'raw', 'I;16', 0, 1)
      outimage = outimage.point(lambda i:i*(1./256)).convert('L')
    elif self.dbtype == dbtype.RGB_32bit :
      outimage = Image.fromarray( tile, 'RGBA')
    else :
      logger.warning ( "Datatype not yet supported".format(self.dbtype) )

    return outimage


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

    # determine the current cache size
    numtiles = self.db.size()

    currentsize = numtiles * settings.TILESIZE * settings.TILESIZE 

    # if we are greater than 95% full.
    if (cachesize - currentsize)*20 < cachesize:

      # start a reclaim process
      from ocptilecache.tasks import reclaim
      reclaim.delay ( )

    else:
      logger.warning ( "Not harvesting cache of {} tiles.  Capacity {}.".format(numtiles,cachesize/512/512))
  

  def channelsToInt ( self, chanlist ):
    """ Go through the list of channels and rewrite all names to integer identifiers """

    outchannels = []

    for chan in chanlist:
      # integers are kept
      if re.match ('^\d+$', chan):
        outchannels.append( int(chan) )
      # Anything else rewritten
      else:
        outchannels.append( self.info['channels'].get(chan) )

    return outchannels

