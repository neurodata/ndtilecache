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

def getTile(request, webargs):
  """Return a tile or load the cache"""

  import pdb; pdb.set_trace()

  # Parse the tile request and turn it into an OCP request
  #m = re.match("(\w+)/(\w+)/(?:([\w,-]+)/)?(\d+)/(\d+)_(\d+)_(\d+).png$", webargs)
  m = re.match("(?P<mcfc>mcfc/)?(\w+)/(\w+)/(?:([\w,-]+)/)?(\d+)/(\d+)_(\d+)_(\d+).png$", webargs)
  [mcfc, token, channels, slice_type] = [i for i in m.groups()[:4]]

  if mcfc is not None:
    import pdb; pdb.set_trace()
    channels, colors = zip(*re.findall("(\w+)[:]?(\w)?", channels))
    orginal_colors = ('C','M','Y','R','G','B')
    # checking for a non-empty list
    if not not filter(None, colors):
      # if it is a mixed then replace the missing ones with the existing schema
      colors = [ b if a is u'' else a for a,b in zip(colors, orignal_colors)]
    else:
      colors = orginal_colors
  else:
    channels = (channels,)
    colors = None

  if slice_type == 'xy':
    [zvalue, yvalue, xvalue, res] = [int(i) for i in m.groups()[4:]]
  elif slice_type == 'xz':
    [yvalue, zvalue, xvalue, res] = [int(i) for i in m.groups()[4:]]
  elif slice_type == 'yz':
    [xvalue, zvalue, yvalue, res] = [int(i) for i in m.groups()[4:]]

  try:
    t = tile.Tile(token, slice_type, res, xvalue, yvalue, zvalue, channels, colors)
    tiledata = t.fetch()
    import pdb; pdb.set_trace()
    return django.http.HttpResponse(tiledata, content_type='image/png')
  except Exception, e:
    raise
    return django.http.HttpResponseNotFound(e)

