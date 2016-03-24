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

import argparse
import time
import urllib2
import multiprocessing

def getURL(url):
  
  try:
    start = time.time()
    req = urllib2.Request(url)
    resp = urllib2.urlopen(req)
    print time.time()-start
  except urllib2.URLError, e:
    print "Failed", time.time()-start


def main():
  
  parser = argparse.ArgumentParser(description="Simple Benchmark Test")
  parser.add_argument("token_name", action="store", type=str, help="Token Name")
  parser.add_argument("channel_name", action="store", type=str, help="Channel Name")
  parser.add_argument("res_value", action="store", type=int, help="Resolution")
  parser.add_argument("--server", dest="server_name", action="store", type=str, default="localhost/ndtilecache", help="Server Name")
  parser.add_argument("--min", dest="min_slice", action="store", type=int, default=1, help="Max Slice Number")
  parser.add_argument("--max", dest="max_slice", action="store", type=int, default=1850, help="Max Slice Number")
  parser.add_argument("--x", dest="xtile", nargs=2, action="store", type=int, metavar=('MIN_VAL','MAX_VAL'), default=[0,1], help="X Tile Range")
  parser.add_argument("--y", dest="ytile", nargs=2, action="store", type=int, metavar=('MAX_VAL','MAX_VAL'), default=[0,1], help="Y Tile Range")
  parser.add_argument("--num", dest="number_of_processes", action="store", type=int, default=4, help="Number of Processes")
  
  result = parser.parse_args()

  fetch_list = []
  
  for slice_number in range(result.min_slice, result.max_slice, 1):
    for x_value in range(result.xtile[0], result.xtile[1]+1, 1):
      for y_value in range(result.ytile[0], result.ytile[1]+1, 1):
        fetch_list.append('http://{}/tilecache/{}/{}/xy/{}/{}_{}_{}.png'.format(result.server_name, result.token_name, result.channel_name, slice_number, x_value, y_value, result.res_value))
  
  p = multiprocessing.Pool(result.number_of_processes)
  start = time.time()
  p.map(getURL, fetch_list)
  print "TOTAL TIME:", time.time() - start

  
if __name__ == '__main__':
  main()
