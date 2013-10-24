import os
import zlib
import cStringIO
import urllib2
import django
import numpy as np
import json
import re
from PIL import Image

from django.conf import settings

import cachedb
import MySQLdb

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

    [ res, xmin, xmax, ymin, ymax, zmin, zmax ] = map(int, m.groups())

    # otherwise load a cube
    logger.warning ("Loading cache for %s" % (cuboidurl))

    # need to restrict the cutout to the project size.
    #  do this based on JSON version of projinfo

    # Get cube in question
    try:
      f = urllib2.urlopen ( cuboidurl )
    except urllib2.URLError, e:
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

    self.db.load ( cuboidurl )

    logger.warning ("Load suceeded for %s" % (cuboidurl))


  def checkDirHier ( self, res ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token )

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

    self.checkDirHier(res)

    # add each image slice to memcache
    for z in range(cuboid.shape[0]):
      self.checkZDirHier(res,z+zmin)
      tilefname = '{}/{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,res,z+zmin,ytile,xtile)
      fobj = open ( tilefname, "w" )
      img = self.tile2WebPNG ( cuboid[z,:,:] )
      img.save ( fobj, "PNG" )


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

