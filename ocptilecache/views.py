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

# Create your views here.

import re
import django

import tile

def getTile ( request, webargs ):
  """Return a tile or load the cache"""

  # Parse the tile request and turn it into an OCP request
  #p = re.compile("(\w+)/(\d+)/(\d+)_(\d+)_(\d+)\.png$")
  p = re.compile("(\w+)/(\w+)/(?:([\w,-]+)/)?(\d+)/(\d+)_(\d+)_(\d+)\.png$")
  m = p.match ( webargs )

  token = m.group(1)
  slicetype = m.group(2)
  channels = m.group(3)
  if slicetype == 'xy':
    zvalue = int(m.group(4)) 
    yvalue = int(m.group(5)) 
    xvalue = int(m.group(6)) 
  elif slicetype == 'xz':
    yvalue = int(m.group(4))
    zvalue = int(m.group(5)) 
    xvalue = int(m.group(6)) 
  elif slicetype == 'yz':
    yvalue = int(m.group(6))
    zvalue = int(m.group(5)) 
    xvalue = int(m.group(4)) 
  res = int(m.group(7))

  try:
    t = tile.Tile ( token, slicetype, res, xvalue, yvalue, zvalue, channels )
    tiledata = t.fetch()
    return django.http.HttpResponse(tiledata,mimetype='image/png')
  except Exception, e:
    raise
#    return django.http.HttpResponseNotFound(e)
