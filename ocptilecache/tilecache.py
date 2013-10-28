import os
import zlib
import cStringIO
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

import logging
logger=logging.getLogger("ocpcatmaid")

class TileCache:

  def __init__ (self, token):
    """Setup the state for this cache request"""

    self.token = token

    self.db = cachedb.CacheDB (  )

    url = 'http://{}/ocpca/{}/info/'.format(settings.SERVER,self.token)
    try:
      f = urllib2.urlopen ( url )
    except urllib2.URLError, e:
      raise

    self.info = json.loads ( f.read() )


  def loadData (self, cuboidurl):
    """Load a cube of data into the cache"""

    p = re.compile('^http://.*/ocpca/\w+/npz/(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+),(\d+).*$')
    m = p.match(cuboidurl)
    if m == None:
      logger.error("Failed to parse url {}".format(url))
      raise Exception ("Failed to parse url {}".format(url))

    [ res, xmin, xmax, ymin, ymax, zmin, zmax ] = map(int, m.groups())

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

      ximagesize, yimagesize = self.info['dataset']['imagesize']['{}'.format(res)]
      zimagesize = self.info['dataset']['slicerange'][1]+1

      cubedata=np.load(pagefobj)

      # cube at a time
      zdim = self.info['dataset']['cube_dimension']['{}'.format(res)][2]

      # Check to see is this is a partial cutout if so pad the space
      if xmax==ximagesize or ymax==yimagesize or zmax==zimagesize:
        cuboid = np.zeros ( (zdim,settings.TILESIZE,settings.TILESIZE), dtype=cubedata.dtype)
        cuboid[0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = cubedata
      else:
        cuboid = cubedata

      xtile = xmin / settings.TILESIZE
      ytile = ymin / settings.TILESIZE

      self.addCuboid( cuboid, res, xtile, ytile, zmin, zdim )

      logger.warning ("Load suceeded for %s" % (cuboidurl))
    
    finally:

      # release the fetch lock
      self.db.fetchrelease(cuboidurl)


  def checkDirHier ( self, res ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token )
      # when making the directory, create a dataset
      try:
        self.db.addDataset ( self.token )
      except MySQLdb.Error, e:
        logger.warning ("Failed to create dataset.  Already exists in database, but not cache. {}:{}.".format(e.args[0], e.args[1]))


    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token + "/r" + str(res) )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token + "/r" + str(res) )


  def checkZDirHier ( self, res, zslice ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token + "/r" + str(res) + '/z' + str(zslice) )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token + "/r" + str(res) + '/z' + str(zslice) )



  def addCuboid ( self, cuboid, res, xtile, ytile, zmin, zdim ):
    """Add the cutout to the cache"""

    # will create the dataset if it doesn't exist
    self.checkDirHier(res)

    # get the dataset id for this token
    dsid = self.db.getDatasetKey ( self.token )

    # counter of how many new tiles we get
    newtiles = 0

    # add each image slice to memcache
    for z in range(cuboid.shape[0]):
      self.checkZDirHier(res,z+zmin)
      tilefname = '{}/{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,res,z+zmin,ytile,xtile)
      fobj = open ( tilefname, "w" )
      img = self.tile2WebPNG ( cuboid[z,:,:] )
      img.save ( fobj, "PNG" )
      try:
        self.db.insert ( tilekey.tileKey(dsid,res,xtile,ytile,z+zmin), tilefname )
        newtiles += 1
      except MySQLdb.Error, e:
        # ignore duplicate entries
        if e.args[0] != 1062:  
          raise

    self.db.increase ( newtiles )
    self.harvest()


  # Put false color back in later.
  #def tile2WebPNG ( self, tile, color, brightness ):
  def tile2WebPNG ( self, tile ):
    """Create PNG Images and write to cache for the specified tile"""

    # write it as a png file
    if tile.dtype==np.uint8:
      return Image.frombuffer ( 'L', [settings.TILESIZE,settings.TILESIZE], tile.flatten(), 'raw', 'L', 0, 1 )
    elif tile.dtype==np.uint32:
      recolor_cy (tile, tile)
      return Image.frombuffer ( 'RGBA', [settings.TILESIZE,settings.TILESIZE], tile.flatten(), 'raw', 'RGBA', 0, 1 )
    elif tile.dtype==np.uint16:
      outimage = Image.frombuffer ( 'I;16', [settings.TILESIZE,settings.TILESIZE], tile.flatten(), 'raw', 'I;16', 0, 1)
      outimage = outimage.point(lambda i:i*(1./256)).convert('L')
      return outimage


  def harvest ( self ):
    """Get rid of tiles to respect cache limits"""

    cachesize = int(settings.CACHE_SIZE) * 0x01 << 20

    # determine the current cache size
    numtiles = self.db.size()

    currentsize = numtiles * settings.TILESIZE * settings.TILESIZE 

    # if we are greater than 90% full.
    if (cachesize - currentsize)*10 < cachesize:

      # start a reclaim process
      from ocptilecache.tasks import reclaim
      reclaim.delay ( )

