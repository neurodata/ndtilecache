# Create your views here.

import re
import django

import tilecache

def getTile ( request, webargs ):
  """Return a tile or load the cache"""

  # Parse the tile request and turn it into an OCP request
#  p = re.compile("(\w+)/(\d+)/(\d+\_)(d+\_)(d+\_)\.jpg$")
  p = re.compile("(\w+)/(\d+)/(\d+)_(\d+)_(\d+)\.jpg$")
  m = p.match ( webargs )

  token = m.group(1) 
  zslice = int(m.group(2)) 
  ytile = int(m.group(3)) 
  xtile = int(m.group(4)) 
  res = int(m.group(5))

  try:
    t = tilecache.TileCache ( token, res, xtile, ytile, zslice )
    t.fetch()
    return django.http.HttpResponse(t.fetch(),mimetype='image/png')
  except Exception, e:
    raise
#    return django.http.HttpResponseNotFound(e)
