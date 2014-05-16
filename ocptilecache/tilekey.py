# Copyright 2014 Open Connectome Project (http;//openconnecto.me)
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


# key to make an integer index 

def tileKey ( dsid, r, x, y, z ):
  """Make a 64 bit key from a tile"""

  # 8 bits for r and 8 bits for project id
  highkey = (r & 0XFFFF) + (dsid << 16)
  lowkey = (x & 0XFFFFF) + ((y & 0xFFFFF) << 20) + ((z & 0xFFFFF) << 40) 
  return (highkey,lowkey)

