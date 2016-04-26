#!/bin/bash

# Installation script for ntilecache backend
# Maintainer: Kunal Lillaney <lillaney@jhu.edu>

# update and upgrade the sys packages 
apt-get update && apt-get upgrade -y

# apt-get install mysql packages
echo "mysql-server-5.6 mysql-server/root_password password neur0data" | sudo debconf-set-selections
echo "mysql-server-5.6 mysql-server/root_password_again password neur0data" | sudo debconf-set-selections
#sudo apt-get -y install mysql-client-core-5.6 libhdf5-serial-dev mysql-client-5.6

# apt-get install packages
sudo apt-get -y install nginx git bash-completion python-virtualenv libxslt1-dev libhdf5-dev libmemcached-dev g++ libjpeg-dev virtualenvwrapper python-dev mysql-server-5.6 libmysqlclient-dev xfsprogs supervisor rabbitmq-server uwsgi uwsgi-plugin-python wget memcached

# create the log directory
sudo mkdir /var/log/neurodata
sudo mkdir /var/log/neurodata/ndtilecache.log
sudo chown -R www-data:www-data /var/log/neurodata
sudo chmod -R 777 /var/log/neurodata

# add group and user neurodata
sudo addgroup neurodata
sudo useradd -m -p neur0data -g neurodata -s /bin/bash neurodata

# switch user to neurodata and clone the repo with sub-modules
cd /home/neurodata
sudo -u neurodata git clone https://github.com/neurodata/ndtilecache
cd /home/neurodata/ndtilecache
sudo -u neurodata git submodule init
sudo -u neurodata git submodule update

# pip install the python packages
pip install cython numpy django pytest posix_ipc boto3 nibabel networkx requests lxml h5py pylibmc pillow blosc django-registration django-registration-redux django-celery mysql-python libtiff

# switch user to neurodata and make ctypes functions
cd /home/neurodata/ndtilecache/ndlib/c_version
sudo -u neurodata make -f makefile_LINUX

# configure mysql
sudo service mysql start
mysql -u root -pneur0data -i -e "create user 'neurodata'@'localhost' identified by 'neur0data';" && mysql -u root -pneur0data -i -e "grant all privileges on *.* to 'neurodata'@'localhost' with grant option;" && mysql -u neurodata -pneur0data -i -e "CREATE DATABASE ndtilecache_django;"

# configure django settings
cd /home/neurodata/ndtilecache/ndtilecache
sudo -u neurodata cp settings.py.example settings.py
sudo -u neurodata ln -s /home/neurodata/ndtilecache/setup/docker_config/django docker_settings_secret.py settings_secret.py

# create the necessary database and tables
#python create_database.py

# migrate the database and create the superuser
sudo chmod -R 777 /var/log/neurodata/
cd /home/neurodata/ndtilecache/
sudo -u neurodata python manage.py migrate
echo "from django.contrib.auth.models import User; User.objects.create_superuser('neurodata', 'abc@xyz.com', 'neur0data')" | python manage.py shell
sudo -u neurodata python manage.py collectstatic --noinput

# move the nginx config files and start service
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /home/neurodata/ndtilecache/setup/docker_config/nginx/neurodata.conf /etc/nginx/sites-enabled/default

# move uwsgi config files and start service
sudo rm /etc/uwsgi/apps-available/ndtilecache.ini
sudo ln -s /home/neurodata/ndtilecache/setup/docker_config/uwsgi/ndtilecache.ini /etc/uwsgi/apps-available/
sudo rm /etc/uwsgi/apps-enabled/ndtilecache.ini
sudo ln -s /home/neurodata/ndtilecache/setup/docker_config/uwsgi/ndtilecache.ini /etc/uwsgi/apps-enabled/

# move celery config files and start service
sudo rm /etc/supervisor/conf.d/prefetch.conf
sudo ln -s /home/neurodata/ndtilecache/setup/docker_config/celery/prefetch.conf /etc/supervisor/conf.d/prefetch.conf
sudo rm /etc/supervisor/conf.d/reclaim.conf
sudo ln -s /home/neurodata/ndtilecache/setup/docker_config/celery/reclaim.conf /etc/supervisor/conf.d/reclaim.conf

# starting all the services
sudo service nginx restart
sudo service uwsgi restart
sudo service supervisor restart
sudo service rabbitmq-server restart
sudo service memcached restart
