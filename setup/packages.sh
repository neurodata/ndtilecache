#!/bin/bash

apt-get update && apt-get upgrade -y

apt-get -y install nginx git bash-completion python-virtualenv libxslt1dev libhdf5-dev libmemcached-dev g++ libjpeg-dev virtualenvwrapper libxslt python-dev mysql-server-5.6 libmysqlclient-devi xfsprogs supervisor rabbitmq-server uwsgi uwsgi-plugin-python

pip install cython numpy django pytest posix_ipc boto3 nibabel networkx requests lxml h5py pylibmc pillow blosc django-registration django-registration-redux django-celery mysql-python libtiff

