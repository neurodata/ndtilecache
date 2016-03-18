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

from __future__ import absolute_import
import re
import posix_ipc

from celery import task
from django.conf import settings

from .cachedb import CacheDB
from .tilecache import TileCache

import logging
logger=logging.getLogger("ndtilecache")


@task(queue='prefetch')
def fetchcube ( token, slice_type, channels, colors, url, cube_data=None):
  """Fetch the requested url."""

  logger.warning ("Fetching url {}".format(url))
  tc = TileCache(token, slice_type, channels, colors)
  tc.loadCube(url, cube_data)

# automatic routing not working in django.  No big deal.  Specify the queue explicitly.
@task(queue='reclaim')
def reclaim ( ):
  """Reclaim space from the database"""

  # only one reclaiming process at a time!
  # if a reclamation is in process, return
  reclsem = posix_ipc.Semaphore ( "/nd_reclaim", flags=posix_ipc.O_CREAT, initial_value=1 )
  try:
    # get the semaphore right away.
    reclsem.acquire(0)

    try:
      # reclaim
      db = CacheDB()
      db.reclaim ()
    except Exception, e:
      logger.error("Error in reclamation {}".format(e))

  except:
    # do nothing if it's not available
    logger.warning("Another reclaimer")

  finally:
    # always release and close
    reclsem.release()
    reclsem.close()
