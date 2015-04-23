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
