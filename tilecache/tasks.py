from celery import Celery
from django.conf import settings
import re

import tilecache

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

  
  

  



