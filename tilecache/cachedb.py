
from django.conf import settings

import MySQLdb

import logging
logger=logging.getLogger("ocpcatmaid")


class CacheDB:
  """MySQL interface for cache management"""

  def __init__(self):

    try:
      self.conn = MySQLdb.connect (host = 'localhost',
                            user = settings.USER,
                            passwd = settings.PASSWD,
                            db = settings.DBNAME )
    except MySQLdb.Error, e:
      logger.error("Failed to connect to database: %s, %s" % (settings.DBNAME, e))
      raise


#  def enqueue(self, url):
#    """Add a url to the prefetch queue"""
#
#    logger.warning("Enqueuing url {}".format(url))
#
#    cursor = self.conn.cursor()
#    
#    sql = "INSERT INTO prefetch (url) VALUES ('{}');".format(url)
#    print sql
#
#    try:
#      cursor.execute ( sql )
#    except MySQLdb.Error, e:
#      logger.warning ("Failed to enqueue prefetch request %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
#      raise
#
#    self.conn.commit()



  def load(self, url):
    """Add a url to the cache contents.  Remove from prefetch queue."""

    cursor = self.conn.cursor()
    
    sql = "INSERT INTO contents (url,reftime) VALUES ('{}',NOW());".format(url)

    try:
      cursor.execute ( sql )
    except MySQLdb.Error, e:
      logger.warning ("Failed to add url to contents %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
      raise

#    sql = "DELETE FROM prefetch WHERE url='{}';".format(url)
#    print sql
#
#    try:
#      cursor.execute ( sql )
#    except MySQLdb.Error, e:
#      logger.warning ("Failed to enqueue prefetch request %d: %s. sql=%s" % (e.args[0], e.args[1], sql))
#      raise

    self.conn.commit()


 
