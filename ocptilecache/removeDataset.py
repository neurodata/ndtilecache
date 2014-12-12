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

import re
import urllib2
import json
import MySQLdb
import argparse

import cachedb

# Make it so that you can get settings from django
import os
import sys
sys.path += [os.path.abspath('..')]
os.environ['DJANGO_SETTINGS_MODULE'] = 'ocpcatmaid.settings'

from django.conf import settings

import logging
logger=logging.getLogger("ocpcatmaid")

def main():

  parser = argparse.ArgumentParser(description='Remove a dataset from the cache ')
  parser.add_argument('datasetname', action="store")

  result = parser.parse_args()

  db = cachedb.CacheDB()
  db.removeDataset ( result.datasetname )

  import shutil

  try:
    shutil.rmtree ( settings.CACHE_DIR + "/" + result.datasetname )
  except Exception, e:
    logger.warning ("Failed to remove dataset directories at {}.  Error {}.  Manual cleanup may be necessary.".format(result.datasetname, e))



if __name__ == "__main__":
      main()


