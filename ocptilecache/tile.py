import urllib2
from django.conf import settings
import logging
import tilekey

import logging
logger=logging.getLogger("ocpcatmaid")

from django.db import models
from ocptilecache.models import ProjectServer

class Tile:
  """Information specific to a given tile in the tilecache"""

  def __init__(self, token, res, xtile, ytile, zslice, channels):

    import cachedb
    # do the fetch in the background
    self.db = cachedb.CacheDB()

    self.token = token
    self.res = res
    self.xtile = xtile
    self.ytile = ytile
    self.zslice = zslice
    self.channels = channels

    if self.channels == None:
      self.filename = '{}/{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.res,self.zslice,self.ytile,self.xtile)
    else:
      self.filename = '{}/{}{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.channels,self.res,self.zslice,self.ytile,self.xtile)

    # cutout a a tilesize region
    self.xdim = settings.TILESIZE
    self.ydim = settings.TILESIZE

    # get the dataset is for this token
    if self.channels == None:
      datasetname = self.token
    else: 
      datasetname = self.token + self.channels
    self.dsid = self.db.getDatasetKey ( datasetname )
    self.tkey = tilekey.tileKey ( self.dsid, self.res, self.xtile, self.ytile, self.zslice )


  def initForFetch ( self ):
    """Configure the database when you need to get data from remote site"""

    import tilecache
    self.tc = tilecache.TileCache(self.token,self.channels)

    # Check for a server for this token
    projserver = ProjectServer.objects.filter(project=token)
    if projserver.exists():
      server = projserver[0].server
    else:
      server = settings.SERVER
  
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
    if self.channels == None:
      cutout = '{}/{},{}/{},{}/{},{}'.format(self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
      self.cuboidurl = "http://{}/ca/{}/npz/{}/".format(server,self.token,cutout)
      self.tileurl = "http://{}/catmaid/{}/512/{}/{}/{}/{}/".format(server,self.token,self.res,self.xtile,self.ytile,self.zslice)
    else:
      cutout = '{}/{}/{},{}/{},{}/{},{}'.format(self.channels,self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
      self.cuboidurl = "http://{}/ca/{}/npz/{}/".format(server,self.token,cutout)
      self.tileurl = "http://{}/catmaid/mcfc/{}/512/{}/{}/{}/{}/{}/".format(server,self.token,self.channels,self.res,self.xtile,self.ytile,self.zslice)


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
      fetchurl.delay ( self.token, self.channels, self.cuboidurl )

      logger.warning("CATMAID tile fetch {}".format(self.tileurl))
      try:
        f = urllib2.urlopen ( self.tileurl )
      except urllib2.URLError, e:
        raise

      return f.read()


