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


def tileKey(dataset_name, resolution, x, y, z, time=None):
  """Make a 64 bit key from a tile"""

  # Adding time to res. this seems like a stop-gap measure to accomodate time
  resolution = resolution + int(time or 0)
  # 8 bits for r and 8 bits for project id
  highkey = (resolution & 0XFFFF) + (dataset_name << 16)
  lowkey = (x & 0XFFFFF) + ((y & 0xFFFFF) << 20) + ((z & 0xFFFFF) << 40) 
  return (highkey,lowkey)
