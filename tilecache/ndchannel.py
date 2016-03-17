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

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from models import Channel

from ndtilecacheerror import NDTILECACHEError
import logging
logger=logging.getLogger("ndtilecache")

class NDChannel:

  def __init__(self, channel_name, dataset_name):
    """Constructor for a channel"""

    try:
      self.ch = Channel.objects.get(channel_name = channel_name, dataset_id=dataset_name)
    except ObjectDoesNotExist as e:
      logger.error("Channel {} does not exist. {}".format(channel_name, e))
      raise NDTILECACHEError("Channel {} does not exist. {}".format(channel_name, e))

  # def __init__(self, channel_name, dataset, channel_type, channel_datatype, startwindow, endwindow):
    # """Intialize the channel"""

    # self.ch.channel_name = channel_name
    # self.ch.dataset = dataset
    # self.ch.channel_type = channel_type
    # self.ch.channel_datatype = channel_datatype
    # self.ch.startwindow = startwindow
    # self.ch.endwindow = endwindow

  def getWindowRange(self):
    return [self.ch.startwindow, self.ch.endwindow]
  
  def getChannelType(self):
    return self.ch.channel_type
  
  def getDataType(self):
    return self.ch.channel_datatype
  
  def getChannelName(self):
    return self.ch.channel_name
  
  def getDataset(self):
    return self.ch.dataset
  
  def getResolution(self):
    return self.ch.resolution
