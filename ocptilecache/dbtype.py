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

 # dbtype enumerations
IMAGES_8bit = 1
ANNOTATIONS = 2
CHANNELS_16bit = 3
CHANNELS_8bit = 4
PROBMAP_32bit = 5
BITMASK = 6
ANNOTATIONS_64bit = 7
IMAGES_16bit = 8
RGB_32bit = 9
RGB_64bit = 10
TIMESERIES_4d_8bit = 11
TIMESERIES_4d_16bit = 12

# dbtype groups
CHANNEL_DATASETS = [ CHANNELS_8bit, CHANNELS_16bit ]
TIMESERIES_DATASETS = [ TIMESERIES_4d_8bit, TIMESERIES_4d_16bit ]
ANNOTATION_DATASETS = [ ANNOTATIONS, ANNOTATIONS_64bit ]
RGB_DATASETS = [ RGB_32bit, RGB_64bit ]
DATASETS_8bit = [ IMAGES_8bit, CHANNELS_8bit, TIMESERIES_4d_8bit ]
DATASETS_16bit = [ IMAGES_8bit, CHANNELS_16bit, TIMESERIES_4d_16bit ]
DATSETS_32bit = [ RGB_32bit, ANNOTATIONS, PROBMAP_32bit ]
COMPOSITE_DATASETS = CHANNEL_DATASETS + TIMESERIES_DATASETS
