import os
import zlib
import cStringIO
import urllib2
import django
import numpy as np
import json
from PIL import Image
from multiprocessing import Process

from django.conf import settings

import logging
logger=logging.getLogger("ocpcatmaid")

class TileCache:

  def __init__ (self, token, res, xtile, ytile, zslice):
    """Setup the state for this cache request"""

    url = 'http://{}/emca/{}/info/'.format(settings.SERVER,token)
    try:
      f = urllib2.urlopen ( url )
    except urllib2.URLError, e:
      raise

    info = json.loads ( f.read() )
    
    # cutout a a tilesize region
    self.xdim = 512
    self.ydim = 512

    # TODO call projinfo to get all the configuration information (use the JSON version)
    self.zdim = info['dataset']['cube_dimension']['{}'.format(res)][2]

    # get max values for the cutout
    self.xmax, self.ymax = info['dataset']['imagesize']['{}'.format(res)]
    self.zoffset = info['dataset']['slicerange'][0]
    self.zmax = info['dataset']['slicerange'][1]

    self.zslab = (zslice-self.zoffset)/self.zdim
    self.zoff = (zslice-self.zoffset)%self.zdim

    self.res = res
    self.xtile = xtile
    self.ytile = ytile
    self.zslice = zslice

    self.token = token

    self.filename = '{}/{}/{}/{}/z{}y{}x{}.png'.format(settings.CACHE_DIR,token,res,self.zslab,self.zoff,ytile,xtile)

  def loadData (self):
    """Load a cube of data into the cache"""

    # otherwise load a cube
    logger.warning ("Loading cache for %s" % (self.filename))

    xmin = self.xtile*self.xdim
    xmax = min ((self.xtile+1)*self.xdim,self.xmax)
    ymin = self.ytile*self.ydim
    ymax = min ((self.ytile+1)*self.ydim,self.ymax)
    zmin = (self.zslab+self.zoffset)*self.zdim
    zmax = min ((self.zslab+self.zoffset+1)*self.zdim,self.zmax)

    # Build the URL
    cutout = '{}/{},{}/{},{}/{},{}'.format(self.res,xmin,xmax,ymin,ymax,zmin,zmax)

    url = "http://{}/emca/{}/npz/{}/".format(settings.SERVER,self.token,cutout)

    # need to restrict the cutout to the project size.
    #  do this based on JSON version of projinfo

    # Get cube in question
    try:
      f = urllib2.urlopen ( url )
    except urllib2.URLError, e:
      raise

    zdata = f.read ()
    # get the data out of the compressed blob
    pagestr = zlib.decompress ( zdata[:] )
    pagefobj = cStringIO.StringIO ( pagestr )

    # Check to see is this is a partial cutout if so pad the space
    if xmax==self.xmax or ymax==self.ymax or zmax==self.zmax:
      cuboid = np.zeros ( (self.zdim,self.ydim,self.xdim), dtype=np.uint8) 
      cuboid[0:(zmax-zmin),0:(ymax-ymin),0:(xmax-xmin)] = np.load(pagefobj)

    # if not, it's the whole deal
    else:
      cuboid = np.load ( pagefobj )

    # put the data into cache
    self.addCuboid ( cuboid )

    logger.warning ("Cache loaded %s" % (url))


  def fetch (self):
    """Retrieve the tile from the cache or load the cache and return"""
    
    try:

      # open file and return
      f=open(self.filename)
      return f.read()

    except IOError:
      
      # do the fetch in the background
      p = Process(target=self.loadData, args=())
      p.start()

      # get the individual tile from the emca/catmaid service
      # change to openconnecto.me when 
      url = "http://rio.cs.jhu.edu/ocpcatmaid/simple/{}/512/{}/{}/{}/{}/".format(self.token,self.res,self.xtile,self.ytile,self.zslice)
      print "Simple service fetch", url
#      url = "http://{}/ocpcatmaid/simple/{}/{}/{}/{}/{}/{}/".format(settings.SERVER,self.xdim,self.token,self.res,self.xtile,self.ytile,self.zslice)
      try:
        f = urllib2.urlopen ( url )
      except urllib2.URLError, e:
        raise

      return f.read()

#      # open file and return
#      f=open(self.filename)
#      return f.read()

  def checkDirHier ( self ):
    """Ensure that the directories for caching exist"""

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token )

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token + "/" + str(self.res) )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token + "/" + str(self.res) )

    try:
      os.stat ( settings.CACHE_DIR + "/" +  self.token + "/" + str(self.res) + '/' + str(self.zslab) )
    except:
      os.makedirs ( settings.CACHE_DIR + "/" +  self.token + "/" + str(self.res) + '/' + str(self.zslab) )


  def addCuboid ( self, cuboid ):
    """Add the cutout to the cache"""

    self.checkDirHier()

    # add each image slice to memcache
    for z in range(self.zdim):
      tilefname = '{}/{}/{}/{}/z{}y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.res,self.zslab,z,self.ytile,self.xtile)
      fobj = open ( tilefname, "w" )
      img = self.tile2WebPNG ( cuboid[z,:,:] )
      img.save ( fobj, "PNG" )



  # Put false color back in later.
  #def tile2WebPNG ( self, tile, color, brightness ):
  def tile2WebPNG ( self, tile ):
    """Create PNG Images and write to cache for the specified tile"""

    # write it as a png file
    if tile.dtype==np.uint8:
      return Image.frombuffer ( 'L', [self.ydim,self.xdim], tile.flatten(), 'raw', 'L', 0, 1 )
    elif tile.dtype==np.uint32:
      recolor_cy (tile, tile)
      return Image.frombuffer ( 'RGBA', [self.ydim,self.xdim], tile.flatten(), 'raw', 'RGBA', 0, 1 )
    elif tile.dtype==np.uint16:
      outimage = Image.frombuffer ( 'I;16', [self.ydim,self.ydim], tile.flatten(), 'raw', 'I;16', 0, 1)
      outimage = outimage.point(lambda i:i*(1./256)).convert('L')
      return outimage

