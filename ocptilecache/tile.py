import urllib2
from django.conf import settings
import logging
import tilekey

import logging
logger=logging.getLogger("ocpcatmaid")

class Tile:
  """Information specific to a given tile in the tilecache"""

  def __init__(self, token, res, xtile, ytile, zslice):

    import cachedb
    # do the fetch in the background
    self.db = cachedb.CacheDB()

    self.token = token
    self.res = res
    self.xtile = xtile
    self.ytile = ytile
    self.zslice = zslice

#  RB can't call before dataset exists
#    self.dsid = self.db.getDatasetKey ( token )

    self.filename = '{}/{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.res,self.zslice,self.ytile,self.xtile)

    # cutout a a tilesize region
    self.xdim = settings.TILESIZE
    self.ydim = settings.TILESIZE

    # get the dataset is for this token
    self.dsid = self.db.getDatasetKey ( token )
    self.tkey = tilekey.tileKey ( self.dsid, self.res, self.xtile, self.ytile, self.zslice )


  def initForFetch ( self ):
    """Configure the database when you need to get data from remote site"""

    import tilecache
    self.tc = tilecache.TileCache(self.token)
  
    # TODO call projinfo to get all the configuration information (use the JSON version)
    self.zdim = self.tc.info['dataset']['cube_dimension']['{}'.format(self.res)][2]

    # get max values for the cutout
    self.ximagesize, self.yimagesize = self.tc.info['dataset']['imagesize']['{}'.format(self.res)]
    self.zoffset = self.tc.info['dataset']['slicerange'][0]
    self.zimagesize = self.tc.info['dataset']['slicerange'][1]+1

    # these are relative to the cuboids in the server
    self.zslab = (self.zslice-self.zoffset)/self.zdim
    self.zoff = (self.zslice-self.zoffset)%self.zdim

    self.xmin = self.xtile*self.xdim
    self.xmax = min ((self.xtile+1)*self.xdim,self.ximagesize)
    self.ymin = self.ytile*self.ydim
    self.ymax = min ((self.ytile+1)*self.ydim,self.yimagesize)
    self.zmin = (self.zslab)*self.zdim+self.zoffset
    self.zmax = min ((self.zslab+1)*self.zdim+self.zoffset,self.zimagesize)

    # Build the URLs
    cutout = '{}/{},{}/{},{}/{},{}'.format(self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
    self.cuboidurl = "http://{}/ocpca/{}/npz/{}/".format(settings.SERVER,self.token,cutout)

    self.tileurl = "http://{}/catmaid/{}/512/{}/{}/{}/{}/".format(settings.SERVER,self.token,self.res,self.xtile,self.ytile,self.zslice)

  def fetch (self):
    """Retrieve the tile from the cache or load the cache and return"""
    
    try:

      # open file and return
      f=open(self.filename)
      self.db.touch(self.tkey)
      return f.read()

    except IOError:

      self.initForFetch()

      # call the celery process to fetch the url
      from ocptilecache.tasks import fetchurl
      fetchurl.delay ( self.cuboidurl, self.tc.info )
     
      logger.warning("CATMAID tile fetch {}".format(self.tileurl))
      try:
        f = urllib2.urlopen ( self.tileurl )
      except urllib2.URLError, e:
        raise

      return f.read()


