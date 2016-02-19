# Copyright 2014 NeuroData (http://neurodata.io)
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
import time
import argparse

def userExperienceTest(result):
  """2k frame rate test"""
  
  for zvalue in range(17,10*16+1,16):
    for i in range(0,16):
      range_args = (xvalue, yvalue, zvalue) = (i/4,i%4,zvalue)
      generateURL(result.host, result.token, result.channel, result.resolution, *range_args)

def cacheTest(result):
  """Warm Cache Test"""

  range_args = (xvalue, yvalue, zvalue) = (0,0,5)
  generateURL(result.host, result.token, result.channel, result.resolution, *range_args)

def generateURL(host, token, channel, resolution, xvalue, yvalue, zvalue):
  """Construct a url"""

  url = 'http://{}/tilecache/{}/{}/xy/{}/{}_{}_{}.png'.format(host, token, channel, zvalue, xvalue, yvalue, resolution)
  getURL(url)

def getURL(url):
  """Fetch the url"""
  
  try:
    req = urllib2.Request(url)
    start = time.time()
    #response = urllib2.urlopen(req)
    print url, time.time()-start
  except urllib2.URLError, e:
    print "Failed URL {}, Error {}".format(url, e)

def main():
  
  parser = argparse.ArgumentParser(description="Benchmark test")
  parser.add_argument('host', action='store', help='Host Name')
  parser.add_argument('token', action='store', help='Project Token')
  parser.add_argument('channel', action='store', help='Channel Name')
  parser.add_argument('resolution', action='store', help='Channel Name')
  result = parser.parse_args()

  cacheTest(result)
  cacheTest(result)
  userExperienceTest(result)
  userExperienceTest(result)

if __name__ == "__main__":
  main()
