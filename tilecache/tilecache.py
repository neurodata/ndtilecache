import os
import zlib
import cStringIO
import urllib2
import django
import numpy as np
from PIL import Image

from django.conf import settings

class TileCache:

  def __init__ (self, token, res, xtile, ytile, zslice):
    """Setup the state for this cache request"""

    self.zoffset = 1 # for kasthuri11 need to get from projinfo

    # TODO call projinfo to get all the configuration information (use the JSON version)
    self.xdim = 512
    self.ydim = 512
    self.zdim = 16

    self.zslab = zslice/16
    self.zoff = zslice%16

    self.res = res
    self.xtile = xtile
    self.ytile = ytile

    self.token = token

    self.filename = '{}/{}/{}/{}/z{}y{}x{}.png'.format(settings.CACHE_DIR,token,res,self.zslab,self.zoff,ytile,xtile)


  def fetch (self):
    """Retrieve the tile from the cache or load the cache and return"""

    try:

      # open file and return
      f=open(self.filename)
      return f.read()

    except IOError:

      # otherwise load a cube
      print "Loading cache for %s" % (self.filename)

      # Build the URL
      cutout = '{}/{},{}/{},{}/{},{}'.format(self.res,self.xtile*self.xdim,(self.xtile+1)*self.xdim,self.ytile*self.ydim,(self.ytile+1)*self.ydim,(self.zslab+self.zoffset)*self.zdim,(self.zslab+self.zoffset+1)*self.zdim)

      url = "http://openconnecto.me/emca/{}/npz/{}/".format(self.token,cutout)

      # need to restrict the cutout to the project size.
      #  do this based on JSON version of projinfo

      print "Fetching url %s" % (url)

      # Get cube in question
      try:
        f = urllib2.urlopen ( url )
      except urllib2.URLError, e:
        raise

      zdata = f.read ()

      # get the data out of the compressed blob
      pagestr = zlib.decompress ( zdata[:] )
      pagefobj = cStringIO.StringIO ( pagestr )
      cuboid = np.load ( pagefobj )

      # put the data into cache
      self.addCuboid ( cuboid )

      # open file and return
      f=open(self.filename)
      return f.read()


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

##    if color != None:
##      # 16 bit images map down to 8 bits
##      if tile.dtype == np.uint16:
##        tile = np.uint8(tile/256)
##
##      # false color the image
##      if tile.dtype != np.uint8:
##        raise ("Illegal color option for data type %s" % ( tile.dtype ))
##      else:
##        tile = self.falseColor ( tile, color )
##
##      img = Image.frombuffer ( 'RGBA', [self.tilesz,self.tilesz], tile.flatten(), 'raw', 'RGBA', 0, 1 )
##
##      # enhance false color images when requested
##      if brightness != None:
##        # Enhance the image
##        import ImageEnhance
##        enhancer = ImageEnhance.Brightness(img)
##        img = enhancer.enhance(brightness)
##
##      return img
##
##    else:
##
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

