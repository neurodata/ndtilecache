from celery import Celery
from django.conf import settings
import re
import posix_ipc

import tilecache
import cachedb

import logging
logger=logging.getLogger("ocpcatmaid")


celery = Celery('tasks', broker='amqp://guest@localhost//')

@celery.task()
def fetchurl ( token, channels, url ):
  """Fetch the requested url."""

  logger.warning ("Fetching url {}".format(url))
  tc = tilecache.TileCache ( token, channels )
  tc.loadData(url)

# automatic routing not working in django.  No big deal.  Specify the queue explicitly.
@celery.task(queue='reclaim')
def reclaim ( ):
  """Reclaim space from the database"""

  # only one reclaiming process at a time!
  # if a reclamation is in process, return
  reclsem = posix_ipc.Semaphore ( "/ocp_reclaim", flags=posix_ipc.O_CREAT, initial_value=1 )
  try:
    # get the semaphore right away.
    reclsem.acquire(0)

    try:
      # reclaim
      db = cachedb.CacheDB()
      db.reclaim ( )
    except Exception, e:
      logger.error("Error in reclamation {}".format(e))

  except:
    # do nothing if it's not available
    logger.warning("Another reclaimer")

  finally:
    # always release and close
    reclsem.release()
    reclsem.close()


  
  


  



