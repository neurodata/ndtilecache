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

  def __init__(self, token, slicetype, res, xvalue, yvalue, zvalue, channels):

    import cachedb
    # do the fetch in the background
    self.db = cachedb.CacheDB()

    self.token = token
    self.slicetype = slicetype
    self.res = res
    self.xvalue = xvalue
    self.yvalue = yvalue
    self.zvalue = zvalue
    self.channels = channels

    if self.channels == None:
      self.filename = '{}/{}/{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.slicetype, self.res,self.zvalue,self.yvalue,self.xvalue)
    else:
      self.filename = '{}/{}{}/{}/r{}/z{}/y{}x{}.png'.format(settings.CACHE_DIR,self.token,self.channels,self.slicetype,self.res,self.zvalue,self.yvalue,self.xvalue)

    # cutout a a tilesize region
    self.tilesize = settings.TILESIZE

    # get the dataset is for this token
    if self.channels == None:
      datasetname = self.slicetype + self.token
    else: 
      datasetname = self.slicetype + self.token + self.channels
    self.dsid = self.db.getDatasetKey ( datasetname )
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
    self.zimagesize = self.tc.info['dataset']['slicerange'][1]+1

    # these are relative to the cuboids in the server

    if self.slicetype == 'xy':
      self.zslab = (self.zvalue-self.zoffset)/self.zdim
      self.zoff = (self.zvalue-self.zoffset)%self.zdim
      self.xmin = self.xvalue*self.tilesize
      self.xmax = min ((self.xvalue+1)*self.tilesize,self.ximagesize)
      self.ymin = self.yvalue*self.tilesize
      self.ymax = min ((self.yvalue+1)*self.tilesize,self.yimagesize)
      self.zmin = (self.zslab)*self.zdim+self.zoffset
      self.zmax = min ((self.zslab+1)*self.zdim+self.zoffset,self.zimagesize)

    elif self.slicetype == 'xz':
      self.yslab = (self.yvalue)/self.ydim
      self.xmin = self.xvalue*self.tilesize
      self.xmax = min ((self.xvalue+1)*self.tilesize,self.ximagesize)
      self.ymin = self.yslab*self.ydim
      self.ymax = min ((self.yslab+1)*self.ydim,self.yimagesize)
      self.zmin = (self.zvalue)*self.tilesize+self.zoffset
      self.zmax = min ((self.zvalue+1)*self.tilesize+self.zoffset,self.zimagesize)

    # Build the URLs
    if self.channels == None:
      cutout = '{}/{},{}/{},{}/{},{}'.format(self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
      self.cuboidurl = "http://{}/ca/{}/npz/{}/".format(server,self.token,cutout)
      self.tileurl = "http://{}/catmaid/{}/{}/512/{}/{}/{}/{}/".format(server,self.token,self.slicetype,self.res,self.xvalue,self.yvalue,self.zvalue)
    else:
      cutout = '{}/{}/{},{}/{},{}/{},{}'.format(self.channels,self.res,self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
      self.cuboidurl = "http://{}/ca/{}/npz/{}/".format(server,self.token,cutout)
      self.tileurl = "http://{}/catmaid/mcfc/{}/{}/512/{}/{}/{}/{}/{}/".format(server,self.token,self.slicetype,self.channels,self.res,self.xvalue,self.yvalue,self.zvalue)


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
      fetchurl.delay ( self.token, self.slicetype, self.channels, self.cuboidurl )
      #fetchurl ( self.token, self.slicetype, self.channels, self.cuboidurl )

      logger.warning("CATMAID tile fetch {}".format(self.tileurl))
      try:
        f = urllib2.urlopen ( self.tileurl )
      except urllib2.URLError, e:
        raise

      return f.read()


