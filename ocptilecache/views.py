# Create your views here.

import re
import django

import tile

def getTile ( request, webargs ):
  """Return a tile or load the cache"""

  # Parse the tile request and turn it into an OCP request
#  p = re.compile("(\w+)/(\d+)/(\d+)_(\d+)_(\d+)\.png$")
  p = re.compile("(\w+)/(?:([\w,-]+)/)?(\d+)/(\d+)_(\d+)_(\d+)\.png$")
  m = p.match ( webargs )

  token = m.group(1) 
  channels = m.group(2)
  zslice = int(m.group(3)) 
  ytile = int(m.group(4)) 
  xtile = int(m.group(5)) 
  res = int(m.group(6))

  try:
    t = tile.Tile ( token, res, xtile, ytile, zslice, channels )
    tiledata = t.fetch()
    return django.http.HttpResponse(tiledata,mimetype='image/png')
  except Exception, e:
    raise
#    return django.http.HttpResponseNotFound(e)
