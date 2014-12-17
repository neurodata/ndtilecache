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
from django.conf import settings
import cStringIO
from PIL import Image

import tilekey
import logging
logger=logging.getLogger("ocpcatmaid")

from django.db import models
from django.conf import settings
from ocptilecache.models import ProjectServer

# Out of Bounds exception
class OOBException(Exception):
  pass

class Tile:
  """Information specific to a given tile in the tilecache"""

  def __init__(self, token, slicetype, res, xvalue, yvalue, zvalue, channels):

    import cachedb

    # load a cache
    self.db = cachedb.CacheDB()

    # cutout a a tilesize region
    self.tilesize = settings.TILESIZE

    # take the arguments
    self.token = token
    self.slicetype = slicetype
    self.res = res
    self.xvalue = xvalue
    self.yvalue = yvalue
    self.zvalue = zvalue
    self.channels = channels

    # get the dataset is for this token
    # set the datasetname
    if self.channels == None:
      datasetname = self.token + "_" + self.slicetype 
    else:
      datasetname = self.token + "_" + self.slicetype + '_' + self.channels

    # Try to get the data set
    (self.dsid,self.ximagesize,self.yimagesize,self.zoffset,self.zmaxslice,self.zscale) = self.db.getDataset ( datasetname )

    # if it's not there, you have to make it.
    if self.dsid == None:
      self.initForFetch()
      try:
        self.db.addDataset ( datasetname,self.ximagesize,self.yimagesize,self.zoffset,self.zmaxslice,self.zscale) 
      except MySQLdb.Error, e:
        logger.warning ("Failed to create dataset.  Already exists in database, but not cache. {}:{}.".format(e.args[0], e.args[1]))
      (self.dsid,self.ximagesize,self.yimagesize,self.zoffset,self.zmaxslice,self.zscale) = self.db.getDataset ( datasetname )

    if self.slicetype=='xy':
      if self.channels == None:
        self.filename = '{}/{}_{}/r{}/sl{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype, self.res,self.zvalue,self.yvalue,self.xvalue)
      else:
        self.filename = '{}/{}_{}_{}/r{}/sl{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype,self.channels,self.res,self.zvalue,self.yvalue,self.xvalue)

    elif self.slicetype=='xz':
      if self.channels == None:
        self.filename = '{}/{}_{}/r{}/sl{}/z{}x{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype,self.res,self.yvalue,self.zvalue,self.xvalue)
      else:
        self.filename = '{}/{}_{}_{}/r{}/sl{}/z{}x{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype,self.channels,self.res,self.yvalue,self.zvalue,self.xvalue)
    elif self.slicetype=='yz':
      if self.channels == None:
        self.filename = '{}/{}_{}/r{}/sl{}/z{}y{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype, self.res,self.xvalue,self.zvalue,self.yvalue)
      else:
        self.filename = '{}/{}_{}_{}/sl{}/z{}y{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype,self.channels,self.res,self.xvalue,self.zvalue,self.yvalue)



    self.tkey = tilekey.tileKey ( self.dsid, self.res, self.xvalue, self.yvalue, self.zvalue )


  def initForFetch ( self ):
    """Configure the database when you need to get data from remote site"""

    import tilecache
    self.tc = tilecache.TileCache(self.token, self.slicetype, self.channels)

    # Check for a server for this token
# RB TODO you never implemented a different server per project
#    projserver = ProjectServer.objects.filter(project=token)
#    if projserver.exists():
#      server = projserver[0].server
#    else:
    server = settings.SERVER
  
    # TODO call projinfo to get all the configuration information (use the JSON version)
    (self.xdim,self.ydim,self.zdim) = self.tc.info['dataset']['cube_dimension']['{}'.format(self.res)]
    
    # get max values for the cutout
    self.ximagesize, self.yimagesize = self.tc.info['dataset']['imagesize']['{}'.format(self.res)]
    self.zoffset = self.tc.info['dataset']['slicerange'][0]
    self.zmaxslice = self.tc.info['dataset']['slicerange'][1]
    self.zscale = self.tc.info['dataset']['zscale']['0']

    # these are relative to the cuboids in the server
    if self.slicetype == 'xy':
      self.zslab = (self.zvalue-self.zoffset)/self.zdim
      self.zoff = (self.zvalue-self.zoffset)%self.zdim
      self.xmin = self.xvalue*self.tilesize
      self.xmax = min ((self.xvalue+1)*self.tilesize,self.ximagesize)
      self.ymin = self.yvalue*self.tilesize
      self.ymax = min ((self.yvalue+1)*self.tilesize,self.yimagesize)
      self.zmin = (self.zslab)*self.zdim+self.zoffset
      self.zmax = min ((self.zslab+1)*self.zdim+self.zoffset,self.zmaxslice+1)

    elif self.slicetype == 'xz':
      self.yslab = (self.yvalue)/self.ydim
      self.xmin = self.xvalue*self.tilesize
      self.xmax = min ((self.xvalue+1)*self.tilesize,self.ximagesize)
      self.ymin = self.yslab*self.ydim
      self.ymax = min ((self.yslab+1)*self.ydim,self.yimagesize)
      scalefactor = self.tc.info['dataset']['zscale']['{}'.format(self.res)]
      # scale the z cutout by the scalefactor
      self.zmin = int((self.zvalue*self.tilesize)/scalefactor+self.zoffset)
      self.zmax = min(int((self.zvalue+1)*self.tilesize/scalefactor+self.zoffset),self.zmaxslice+1)

    elif self.slicetype == 'yz':
      self.xslab = (self.xvalue)/self.xdim
      self.xmin = self.xslab*self.xdim
      self.xmax = min ((self.xslab+1)*self.xdim,self.ximagesize)
      self.ymin = self.yvalue*self.tilesize
      self.ymax = min ((self.yvalue+1)*self.tilesize,self.yimagesize)
      scalefactor = self.tc.info['dataset']['zscale']['{}'.format(self.res)]
      # scale the z cutout by the scalefactor
      self.zmin = int((self.zvalue*self.tilesize)/scalefactor+self.zoffset)
      self.zmax = min(int((self.zvalue+1)*self.tilesize/scalefactor+self.zoffset),self.zmaxslice+1)

    # Build the URLs
    if self.channels == None:
      cutout = '{}/{},{}/{},{}/{},{}'.format(self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
      self.cuboidurl = "http://{}/ca/{}/npz/{}/".format(server,self.token,cutout)
      self.tileurl = "http://{}/catmaid/{}/{}/512/{}/{}/{}/{}/".format(server,self.token,self.slicetype,self.res,self.xvalue,self.yvalue,self.zvalue)
    else:
      cutout = '{}/{}/{},{}/{},{}/{},{}'.format(self.channels,self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
      self.cuboidurl = "http://{}/ca/{}/npz/{}/".format(server,self.token,cutout)
      self.tileurl = "http://{}/catmaid/mcfc/{}/{}/512/{}/{}/{}/{}/{}/".format(server,self.token,self.slicetype,self.channels,self.res,self.xvalue,self.yvalue,self.zvalue)


    if self.zmin>=self.zmax or self.ymin>=self.ymax or self.xmin>=self.xmax:
      raise OOBException("Out of bounds request")


  def fetch (self):
    """Retrieve the tile from the cache or load the cache and return"""

    try:

      # open file and return
      f=open(self.filename)
      self.db.touch(self.tkey)
      return f.read()

    except IOError:
      pass

    try:
      self.initForFetch()
    except OOBException:
      logger.warning("OOB request.  Returning black tile.  url={}".format(self.tileurl))
      img = Image.new("L", (512, 512))
      fileobj = cStringIO.StringIO ( )
      img.save ( fileobj, "PNG" )
      fileobj.seek(0)
      return fileobj.read()

    # call the celery process to fetch the url
    from ocptilecache.tasks import fetchurl
    fetchurl.delay ( self.token, self.slicetype, self.channels, self.cuboidurl )
    #fetchurl ( self.token, self.slicetype, self.channels, self.cuboidurl )

    logger.warning("CATMAID tile fetch {}".format(self.tileurl))
    try:
      f = urllib2.urlopen ( self.tileurl )
    except urllib2.URLError, e:
      raise

    return f.read()

  def inRange ( self ):
    """Determine if the requested tile is in the project domain"""

