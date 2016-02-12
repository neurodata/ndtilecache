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

import re
import boto3
import blosc
import numpy as np
from operator import add, sub, mul, div, mod

import ndlib
from ndtype import ND_dtypetonp

from ndtilecacheerror import NDTILECACHEError
import logging
logger=logging.getLogger("ndtilecache")

class S3IO:

  def __init__(self, ds, channels):
    """Connect to the s3 backend"""
    
    self.ds = ds
    self.channels = channels
    self.client = boto3.client('s3')
  

  def getCutout(self, cuboid_url):
    """Return a cutout based on the cuboid_url"""
    
    try:
      # argument of the form /ca/token/channel/blosc/cutoutargs
      m = re.match("^http://.*/ca/\w+/(?:[\w+,]+/)?blosc/(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+),(\d+)/(\d+)?,?(\d+)?/?$", cuboid_url)
      [res, xmin, xmax, ymin, ymax, zmin, zmax, tmin, tmax] = [int(i) if i is not None else None for i in m.groups()]
    except Exception, e:
      logger.error("Failed to parse url {}".format(cuboid_url))
      raise NDTILECACHEError("Failed to parse url {}".format(cuboid_url))
    

    # get the size of the image and cube
    [ xsupercubedim, ysupercubedim, zsupercubedim ] = supercubedim = self.ds.supercubedim [ res ] 
    corner = [xmin, ymin, zmin]
    dim = map(sub, [xmax, ymax, zmax], [xmin, ymin, zmin])

    # Round to the nearest larger cube in all dimensions
    [ xstart, ystart, zstart ] = start = map(div, corner, supercubedim)

    znumsupercubes = (corner[2] + dim[2] + zsupercubedim - 1) / zsupercubedim - zstart
    ynumsupercubes = (corner[1] + dim[1] + ysupercubedim - 1) / ysupercubedim - ystart
    xnumsupercubes = (corner[0] + dim[0] + xsupercubedim - 1) / xsupercubedim - xstart

    ch = self.ds.getChannelObj(self.channels[0])
    outcube = np.zeros([len(self.channels), znumsupercubes*zsupercubedim, ynumsupercubes*ysupercubedim, xnumsupercubes*xsupercubedim], dtype= ND_dtypetonp[ch.getDataType()])
                                        
    # Build a list of indexes to access
    listofidxs = []
    for z in range ( znumsupercubes ):
      for y in range ( ynumsupercubes ):
        for x in range ( xnumsupercubes ):
          mortonidx = ndlib.XYZMorton ( [x+xstart, y+ystart, z+zstart] )
          listofidxs.append ( mortonidx )

    # Sort the indexes in Morton order
    listofidxs.sort()
    
    # xyz offset stored for later use
    lowxyz = ndlib.MortonXYZ ( listofidxs[0] )
    
    for channel_index, channel_name in enumerate(self.channels):
      
      ch = self.ds.getChannelObj(channel_name)
      super_cuboids = self.getSuperCubes(ch, res, listofidxs)

      # use the batch generator interface
      for idx, data in super_cuboids:

        #add the query result cube to the bigger cube
        curxyz = ndlib.MortonXYZ(int(idx))
        offset = [ curxyz[0]-lowxyz[0], curxyz[1]-lowxyz[1], curxyz[2]-lowxyz[2] ]
        
        # add it to the output cube
        [xoffset, yoffset, zoffset] = new_offset = map(mul, offset, data.shape[::-1])
        outcube[ channel_index, zoffset:zoffset+data.shape[0], yoffset:yoffset+data.shape[1], xoffset:xoffset+data.shape[2] ] = data[:,:,:]
        
    return outcube
    # if map(mod, dim, supercubedim) == [0,0,0] and map(mod, corner, supercubedim) == [0,0,0]:
      # return outcube
    # else:
      # [ztrim_offset, ytrim_offset, xtrim_offset] = trim_offset = map(mod, corner, supercubedim)
      # return outcube[ztrim_offset:ztrim_offset+dim[2], ytrim_offset:ytrim_offset+dim[1], xtrim_offset:xtrim_offset+dim[0]]


  def getSuperCubes(self, ch, res, super_listofidxs):
    """Get SuperCubes"""
    
    from s3util import generateS3BucketName, generateS3Key
    for super_zidx in super_listofidxs:
      super_cube = self.client.get_object(Bucket=generateS3BucketName(ch.getProjectName(), ch.getChannelName()), Key=generateS3Key(super_zidx, res)).get('Body').read()
      yield (super_zidx, blosc.unpack_array(super_cube))
