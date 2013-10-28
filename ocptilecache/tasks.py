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
def fetchurl ( url, info ):
  """Fetch the requested url."""

  logger.warning ("Fetching url {}".format(url))
  p = re.compile('^http://.*/ocpca/(\w+)/.*$')
  m = p.match(url)
  token = m.group(1)
  tc = tilecache.TileCache ( token )
  tc.loadData(url)

# automatic routing not working in django.  No big deal.  Specify the queue explicitly.
@celery.task(queue='reclaim')
def reclaim ( ):
  """Reclaim space from the database"""

  # only one reclaiming process at a time!
  # if a reclamation is in process, return
  reclsem = posix_ipc.Semaphore ( "/ocpreclaim", flags=posix_ipc.O_CREAT, initial_value=1 )
  try:
    # get the semaphore right away.
    reclsem.acquire(0)

    # reclaim
    db = cachedb.CacheDB()
    db.reclaim ( )

  except:
    # do nothing if it's not available
    logger.warning("Another reclaimer")
  finally:
    # always release
    reclsem.release()


  
  


  



