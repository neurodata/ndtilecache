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
# limitations under the License.i

import numpy as np

# OCP Version
OCP_VERSION = '0.6'
SCHEMA_VERSION = '0.6'

OCP_channeltypes = {0:'image', 1:'annotation', 2:'probmap', 3:'timeseries'}

# channeltype groups
IMAGE_CHANNELS = ['image', 'probmap', 'oldchannel']
TIMESERIES_CHANNELS = ['timeseries']
ANNOTATION_CHANNELS = ['annotation']

# datatype groups
DTYPE_uint8 = ['uint8']
DTYPE_uint16 = ['uint16']
DTYPE_uint32 = ['rgb32','uint32']
DTYPE_uint64 = ['rgb64']
DTYPE_float32 = ['probability']
OCP_dtypetonp = {'uint8':np.uint8, 'uint16':np.uint16, 'uint32':np.uint32, 'rgb32':np. uint32, 'rgb64':np.uint64, 'probability':np.float32}

# SCALING OPTIONS
ZSLICES = 0
ISOTROPIC = 1
OCP_scalingtoint = {'zslices':ZSLICES, 'xyz':ISOTROPIC}
