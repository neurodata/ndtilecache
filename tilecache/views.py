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

from ocptilecacheerror import OCPTILECACHEError
import logging
logger=logging.getLogger("ocptilecache")

def getTile(request, webargs):
  """Return a tile or load the cache"""
  
  # Parse the tile request and turn it into an OCP request
  try:
    # argument of format /mcfc(optional)/token/channel_list/slice_type/time(optional)/z/y_x_res.png
    m = re.match("(?P<mcfc>mcfc/)?(\w+)/([\w+,:]+)/(\w+)/(\d/)?(\d+)/(\d+)_(\d+)_(\d+).png$", webargs)
    [mcfc, token, channels, slice_type] = [i for i in m.groups()[:4]]
  except Exception, e:
    logger.warning("Incorrect arguments {}. {}".format(webargs, e))
    raise OCPTILECACHEError("Incorrect arguments {}. {}".format(webargs, e))

  if mcfc is not None:
    # arguments of the form channel:color,channel:color  OR channel,channel
    channels, colors = zip(*re.findall("(\w+)[:]?(\w)?", channels))
    orignal_colors = ('C','M','Y','R','G','B')
    # checking for a non-empty list
    if not not filter(None, colors):
      # if it is a mixed then replace the missing ones with the existing schema
      colors = [ b if a is u'' else a for a,b in zip(colors, orignal_colors)]
    else:
      colors = orignal_colors
  else:
    try:
      # only a single channel if not mcfc cutout
      channels = re.match("(\w+)$", channels).groups()
      colors = None
    except Exception, e:
      logger.warning("Incorrect channel {} for simple cutout. {}".format(channels, e))
      raise OCPTILECACHEError("Incorrect channel {} for simple cutout. {}".format(channels, e))

  if slice_type == 'xy':
    [tvalue, zvalue, yvalue, xvalue, res] = [int(i.strip('/')) if i is not None else None for i in m.groups()[4:]]
  elif slice_type == 'xz':
    [tvalue, yvalue, zvalue, xvalue, res] = [int(i.strip('/')) if i is not None else None for i in m.groups()[4:]]
  elif slice_type == 'yz':
    [tvalue, xvalue, zvalue, yvalue, res] = [int(i.strip('/')) if i is not None else None for i in m.groups()[4:]]

  try:
    t = tile.Tile(token, slice_type, res, xvalue, yvalue, zvalue, tvalue, channels, colors)
    tiledata = t.fetch()
    return django.http.HttpResponse(tiledata, content_type='image/png')
  except Exception, e:
    raise
    return django.http.HttpResponseNotFound(e)
