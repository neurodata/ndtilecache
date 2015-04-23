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


from django.conf import settings

import MySQLdb
import os

from ocpcatmaiderror import OCPCATMAIDError
import logging
logger=logging.getLogger("ocpcatmaid")


class CacheDB:
  """MySQL interface for cache management"""

  def __init__(self):

    try:
      self.conn = MySQLdb.connect (host = 'localhost', user = settings.USER, passwd = settings.PASSWD, db = settings.DBNAME )
    except MySQLdb.Error, e:
      logger.error("Failed to connect to database: {}, {}".format(settings.DBNAME, e))
      raise OCPCATMAIDError("Failed to connect to database: {}, {}".format(settings.DBNAME, e))


# Some technique to make sure we don't fetch the same thing twice concurrently?
  def fetchlock ( self, url ):
    """Indicate that we are actively fetching a url.  Raise an Exception if it is already happening"""
    cursor = self.conn.cursor()

    sql = "INSERT INTO fetching (url) VALUE ('{}')".format(url)
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      if e.args[0] != 1062:
        logger.warning ("Unknown error in fetchlock.  Check configuration. {}:{}. sql={}".format(e.args[0], e.args[1], sql))
      raise

    self.conn.commit()

  def fetchrelease ( self, url ):
    """We are no longer fetching the url"""

    cursor = self.conn.cursor()

    sql = "DELETE FROM fetching WHERE url='{}'".format(url)
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Unknown error in fetchrelease. {}:{}. sql={}".format(e.args[0], e.args[1], sql))

    self.conn.commit()

  def touch(self, tkey):
    """Update the reference time on a tile"""

    cursor = self.conn.cursor()

    sql = "UPDATE contents SET reftime=NOW() WHERE highkey={} AND lowkey={}".format(tkey[0],tkey[1])
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to touch tilekey %s.  Error %d: %s. sql=%s" % (tkey, e.args[0], e.args[1], sql))
      raise

    self.conn.commit()


  def insert(self, tkey, filename):
    """Add a tile to the cache contents.  Remove from prefetch queue.
        This routine returns MySQLError with e.args[0] == 1062. For duplicate tiles."""

    cursor = self.conn.cursor()
    
    sql = "INSERT INTO contents (highkey,lowkey,filename,reftime) VALUES ({},{},'{}', NOW());".format(tkey[0],tkey[1],filename)

    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      # ignore duplicate entries
      if e.args[0] != 1062:
        logger.warning ("Failed to add tile to contents. key=%s. file=%s.  Error= %d: %s. sql=%s" % (tkey, filename, e.args[0], e.args[1], sql))
      raise

    self.conn.commit()


  def size ( self ):
    """Return the size of the cache in nunmber of tiles"""

    cursor = self.conn.cursor()

    # determine the current cache size
    sql = "SELECT numtiles FROM metadata;"
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to query cache size %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

    return int(cursor.fetchone()[0])

#    # RB testing check against the number of tiles
#
#    metadatasize = int(cursor.fetchone()[0])
#    
#    sql = "SELECT count(*) FROM contents";
#    try:
#      cursor.execute ( sql )
#    except MySQLdb.Error, e:
#      logger.warning ("Failed to query cache size (count*) %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
#      raise
#
#    countsize = int(cursor.fetchone()[0])
#
#    if countsize != metadatasize:
#      logger.warning("Cache size and metadatasize not consistent.  {} v {}".format(countsize,metadatasize))
#
#    return countsize


  def increase ( self, numtiles ):
    """Add tiles to the cache"""

    cursor = self.conn.cursor()

    # determine the current cache size
    sql = "UPDATE metadata SET numtiles=numtiles+{}".format(numtiles)
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to query cache size %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise
   
    self.conn.commit()

  def decrease ( self, numtiles ):
    """Remove tiles from the cache"""

    cursor = self.conn.cursor()

    # determine the current cache size
    sql = "UPDATE metadata SET numtiles=numtiles-{}".format(numtiles)
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to query cache size %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise
   
    self.conn.commit()


  def reclaim ( self ):
    """Reduce the cache size to a target"""

    # CACHE SIZE is in MB
    cachesize = int(settings.CACHE_SIZE) * 0x01 << 20

    # determine the current cache size
    numtiles = self.size()
    currentsize = numtiles * settings.TILESIZE * settings.TILESIZE 

    # if we are bigger than 95% of the cache go down to 90%
    if (cachesize - currentsize)*20 < cachesize:
      numitems = (currentsize-int(0.9*cachesize))/(settings.TILESIZE*settings.TILESIZE)
    else:
      logger.warning ( "Not reclaiming cache of {} tiles.  Capacity {}.".format(numtiles,cachesize/512/512))
      return

    cursor = self.conn.cursor()

    logger.warning ("Cache has {} tiles.  Capacity of {} tiles.  Reclaiming {}".format(numtiles,cachesize/512/512,numitems))

    sql = "SELECT highkey, lowkey, filename FROM contents ORDER BY reftime ASC LIMIT {}".format(numitems)

    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to query cache for reclamation s%d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

    result = cursor.fetchall()
    tilekeys = [(int(item[0]),int(item[1])) for item in result]
    files = [item[2] for item in result]

    # Delete the files
    for fname in files:
      # remove the file but don't quit
      try:
        os.remove ( fname )
      except Exception, e:
        logger.error("Failed to remove file %s. Error %s" % ( fname, e ))

    sql = "DELETE FROM contents WHERE (highkey,lowkey) IN (%s)"
    in_p=', '.join(map(lambda x: str(x), tilekeys))
    sql = sql % in_p
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to remove items from cache %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

    self.decrease ( numitems )
    self.conn.commit()

  def removeProject ( self, prefix ):
    """Remove all cache entries for a given project"""

    cursor = self.conn.cursor()

    sql = "SELECT highkey, lowkey, filename FROM contents WHERE filename LIKE '{}%'".format(prefix)
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to query cache for token %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

    result = cursor.fetchall()
    tilekeys = [(int(item[0]),int(item[1])) for item in result]
    files = [item[2] for item in result]

    # only process if there are things to do
    if not files:
      return

    # how many items are we removing
    numitems = len(files)

    # Delete the files
    for fname in files:
      # remove the file but don't quit
      try:
        os.remove ( fname )
      except Exception, e:
        logger.error("Failed to remove file %s. Error %s" % ( fname, e ))


    sql = "DELETE FROM contents WHERE (highkey,lowkey) IN (%s)"
    in_p=', '.join(map(lambda x: str(x), tilekeys))
    sql = sql % in_p
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to remove items from cache %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

    self.decrease ( numitems )
    self.conn.commit()


  def getDataset(self, ds):

    cursor = self.conn.cursor()

    sql = "SELECT datasetid, ximagesz, yimagesz, zimagesz, xoffset, yoffset, zoffset, xvoxelres, yvoxelres, zvoxelres, scalingoption, scalinglevels FROM datasets WHERE dataset = '{}';".format(ds.dataset_name)
    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to fetch dataset {}: {}. sql={}".format(e.args[0], e.args[1], sql))
      raise OCPCATMAIDError("Failed to fetch dataset {}: {}. sql={}".format(e.args[0], e.args[1], sql))

    # 0 is no dataset.  It will never match in the cache. 
    # The dataset will get created on fetch.
    r = cursor.fetchone()
    cursor.close()
    if r is not None:
      (ds.dsid, ds.ximagesz, ds.yimagesz, ds.zimagesz, ds.xoffset, ds.yoffset, ds.zoffset, ds.xvoxelres, ds.yvoxelres, ds.zvoxelres, ds.scalingoption, ds.scalinglevels) = r
    else:
      raise Exception("Dataset not found")
    


  def addDataset (self, ds):
    """Add a dataset to the list of cacheable datasets"""
    
    cursor = self.conn.cursor()

    try:
      sql = "INSERT INTO datasets (dataset, ximagesz, yimagesz, zimagesz, xoffset, yoffset, zoffset, xvoxelres, yvoxelres, zvoxelres, scalingoption, scalinglevels) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}');".format(ds.dataset_name, ds.ximagesz, ds.yimagesz, ds.zimagesz, ds.xoffset, ds.yoffset, ds.zoffset, ds.xvoxelres, ds.yvoxelres, ds.zvoxelres, ds.scalingoption, ds.scalinglevels)
      cursor.execute (sql)

      for ch in ds.channel_list:
        sql = "INSERT INTO channels (channel_name, dataset, channel_type, channel_datatype, startwindow, endwindow) VALUES ('{}','{}','{}','{}','{}','{}');".format(ch.channel_name, ch.dataset, ch.channel_type, ch.channel_datatype, ch.startwindow, ch.endwindow)
        cursor.execute (sql)

      self.conn.commit()
    
    except MySQLdb.Error, e:
      logger.warning ("Failed to insert dataset/channel {}: {}. sql={}".format(e.args[0], e.args[1], sql))
      raise OCPCATMAIDError("Failed to insert dataset/channel {}: {}. sql={}".format(e.args[0], e.args[1], sql))
      self.conn.rollback()
    
    finally:
      cursor.close()


  def removeDataset(self, datasetname):

    cursor = self.conn.cursor()

    sql = "SELECT highkey, lowkey FROM contents WHERE filename LIKE '{}/{}/%';".format(settings.CACHE_DIR,datasetname)

    try:
      cursor.execute(sql)
    except MySQLdb.Error, e:
      logger.warning ("Failed to query cache for dataset. %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

    result = cursor.fetchall()

    if result == ():
      logger.warning("Found no cache entries for dataset {}.".format(datasetname))
      return

    tilekeys = [(int(item[0]),int(item[1])) for item in result]

    numitems = len(tilekeys)

    sql = "DELETE FROM contents WHERE (highkey,lowkey) IN (%s)"
    in_p=', '.join(map(lambda x: str(x), tilekeys))
    sql = sql % in_p
    try:
      cursor.execute(sql)
    except MySQLdb.Error, e:
      logger.warning ("Failed to remove items from cache {}: {}. sql={}".format(e.args[0], e.args[1], sql))
      raise

    self.decrease(numitems)
    self.conn.commit()


  def addChannel(self, ch):
    """Add a channel to the channels table"""

    cursor = self.conn.cursor()

    sql = "INSERT INTO channels (channel_name, dataset, channel_type, channel_datatype, startwindow, endwindow) VALUES ('{}','{}','{}','{}','{}','{}');".format(ch.channel_name, ch.dataset, ch.channel_type, ch.channel_datatype, ch.startwindow, ch.endwindow)
    
    try:
      cursor.execute (sql)
    except MySQLdb.Error, e:
      logger.warning ("Failed to insert channel {}: {}. sql={}".format(e.args[0], e.args[1], sql))
      raise OCPCATMAIDError("Failed to insert channel {}: {}. sql={}".format(e.args[0], e.args[1], sql))

    self.conn.commit()
    cursor.close()


  def getChannel(self, ds):
    """Get a channel from the channels table"""

    cursor = self.conn.cursor()

    sql = "SELECT channel_name, dataset, channel_type, channel_datatype, startwindow, endwindow FROM channels where dataset='{}';".format(ds.dataset_name)

    try:
      cursor.execute (sql)
      from dataset import Channel
      for row in cursor:
        ds.channel_list.append(Channel(*row))

    except MySQLdb.Error, e:
      logger.warning ("Failed to fetch channel {}: {}. sql={}".format(e.args[0], e.args[1], sql))
      raise OCPCATMAIDError("Failed to fetch channel {}: {}. sql={}".format(e.args[0], e.args[1], sql))

    cursor.close()
