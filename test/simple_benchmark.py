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

import time
import urllib2
import multiprocessing

fetch_list = []
min_slice = 1
max_slice = 100
server_name = 'localhost:8080'

def getURL(url):
  req = urllib2.Request(url)
  start = time.time()
  urllib2.urlopen(req)
  print time.time()-start

def main():
  for slice_number in range(min_slice, max_slice):
    fetch_list.append('http://{}/tilecache/kasthuri11/image/xy/{}/0_0_5.png'.format(server_name, slice_number))
  
  p = multiprocessing.Pool(1)
  p.map(getURL, fetch_list)


if __name__ == '__main__':
  main()