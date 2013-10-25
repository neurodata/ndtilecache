from celery import Celery
from django.conf import settings
import re
import posix_ipc

import tilecache
import cachedb

import logging
logger=logging.getLogger("ocpcatmaid")


celery = Celery('tasks', broker='amqp://guest@localhost//')

@celery.task(name='tasks.fetchurl')
def fetchurl ( url, info ):
  """Fetch the requested url."""

  logger.warning ("Fetching url {}".format(url))
  p = re.compile('^http://.*/ocpca/(\w+)/.*$')
  m = p.match(url)
  token = m.group(1)
  tc = tilecache.TileCache ( token )
  tc.loadData(url)

@celery.task(name='tasks.reclaim')
def reclaim ( numitems ):
  """Reclaim numitems from the database"""

  # only one reclaiming process at a time!
  # if a reclamation is in process, return
  reclsem = posix_ipc.Semaphore ( "/ocpreclaim", flags=posix_ipc.O_CREAT, initial_value=1 )
  try:
    # get the semaphore right away.
    reclsem.acquire(0)

    # reclaim
    db = cachedb.CacheDB()
    db.reclaim ( numitems )

  except:
    # do nothing if it's not available
    logger.warning("Another reclaimer")
  finally:
    # always release
    reclsem.release()


  
  


  



