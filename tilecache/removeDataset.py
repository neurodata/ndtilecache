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

import os
import sys
import argparse

# Make it so that you can get settings from django
sys.path += [os.path.abspath('../')]
import ocptilecache.settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'ndtilecache.settings'
from django.conf import settings

from dataset import Dataset

import logging
logger=logging.getLogger("ndtilecache")

def main():

  parser = argparse.ArgumentParser(description='Remove a dataset from the cache')
  parser.add_argument('dataset_name', action="store")

  result = parser.parse_args()
  ds = Dataset(result.dataset_name)
  ds.removeDataset()

if __name__ == "__main__":
  main()
