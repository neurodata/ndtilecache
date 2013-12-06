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
from django.db import models
from ocptilecache.models import ProjectServer


def prefetch ( token, res, xmin, xmax, ymin, ymax, zmin, zmax ):
  """Script to prefetch a cutout region"""

  import pdb; pdb.set_trace()

  # Check for a server for this token
  projserver = ProjectServer.objects.filter(project=token)
  if projserver.exists():
    server = projserver[0].server
  else:
    server = settings.SERVER
  
  url = 'http://{}/ocpca/{}/info/'.format(server,token)
  try:
    f = urllib2.urlopen ( url )
  except urllib2.URLError, e:
    raise

  info = json.loads ( f.read() )
  
  # cutout a a tilesize region
  xdim = 512
  ydim = 512

  zoffset = info['dataset']['slicerange'][0]
  zimagesize = info['dataset']['slicerange'][1]+1
  maxres = max(info['dataset']['resolutions'])
  for level in range(res,maxres): 

    # get max values for the cutout
    ximagesize, yimagesize = info['dataset']['imagesize']['{}'.format(level)]

    # zdim changes by cube size
    zdim = info['dataset']['cube_dimension']['{}'.format(res)][2]
    zoffset = info['dataset']['slicerange'][0]


    xlow = xmin / (2**(level-res)) / xdim * xdim
    ylow = ymin / (2**(level-res)) / ydim * ydim
    zlow = (zmin-zoffset) / (2**(level-res)) / zdim * zdim + zoffset

    xhigh = (((xmax-1) / (2**(level-res)) / xdim)+1) * xdim
    yhigh = (((ymax-1) / (2**(level-res)) / ydim)+1) * ydim
    zhigh = (((zmax-1-zoffset) / zdim)+1) * zdim + zoffset

    if zlow < 0 or xlow > ximagesize or ylow > yimagesize or xhigh > ((ximagesize-1) / xdim +1 ) * xdim or yhigh > ((yimagesize-1) / ydim +1 ) * ydim:
      raise Exception("Illegal prefetch dimensions")

    for z in range(zlow,zhigh,zdim):
      for y in range(ylow,yhigh,ydim):
        for x in range(xlow,xhigh,xdim):

          if zlow >= zhigh or ylow >= yhigh or xlow >= xhigh:
            continue
        
          # Build the URLs
          cutout = '{}/{},{}/{},{}/{},{}'.format(level,x,min(x+xdim,ximagesize),y,min(y+ydim,yimagesize),z,min(z+zdim,zimagesize))
          cuboidurl = "http://{}/ocpca/{}/npz/{}/".format(settings.SERVER,token,cutout)
          print cuboidurl

          # call the celery process to fetch the url
          from ocptilecache.tasks import fetchurl
          fetchurl.delay ( cuboidurl, info )

def main():

  parser = argparse.ArgumentParser(description='Prefetch a volume  ')
  parser.add_argument('token', action="store")
  parser.add_argument('cutout', action="store", help='Cutout arguments of the form resolution/x1,x2/y1,y2/z1,z2.', default=None)

  result = parser.parse_args()

  p = re.compile('^(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+),(\d+).*$')
  m = p.match(result.cutout)

  [ res, xmin, xmax, ymin, ymax, zmin, zmax ] = map(int, m.groups())

  prefetch ( result.token, res, xmin, xmax, ymin, ymax, zmin, zmax )


if __name__ == "__main__":
      main()


