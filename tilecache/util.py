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

import urllib2
import dbtype
import numpy as np

def getURL(url):
  """Get the url"""

  try:
    f = urllib2.urlopen(url)
  except urllib2.HTTPError, e:
    raise Exception(e)

  return f

def postURL(url):
  """Post the url"""

  try:
    request = urllib2.Request(url, f.read())
    response = urllib2.urlopen(request)
  except urllib2.HTTPError, e:
    raise Exception(e)

def window(data, ch, window_range=None):
  """Performs a window transformation on the cutout area"""
  
  if window_range is None:
    window_range = ch.getWindowRange()
  
  [startwindow, endwindow] = window_range
  
  if ch.getChannelType() in dbtype.IMAGE_CHANNELS and ch.getDataType() in dbtype.DTYPE_uint16:
    if (startwindow == endwindow == 0):
      return np.uint8(data * 1.0/256)
    elif endwindow!=0:
      windowCutout (data, window_range)
      return np.uint8(data)
  
  return data

def getDatasetName(token, channel_list, colors, slice_type):
  """Return a dataset name given the token, channel, colors and slice_type"""
  
  if colors is not None:
    channel_list = ["{}:{}".format(a,b) for a,b in zip(channel_list, colors)]
  return "{}-{}-{}".format(token, ','.join(channel_list), slice_type)
