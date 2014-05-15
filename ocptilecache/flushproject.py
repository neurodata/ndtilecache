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



def main():

  parser = argparse.ArgumentParser(description='Remove the cache contents for a project token.')
  parser.add_argument('token', action="store")

  result = parser.parse_args()

  db = cachedb.CacheDB()

  prefix = settings.CACHE_DIR + "/" +  result.token 

  db.removeProject ( prefix )


if __name__ == "__main__":
      main()


