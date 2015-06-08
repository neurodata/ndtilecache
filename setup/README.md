### Configuration instructions for OCPTILECACHE


##### MySQL
  
  * Run the python script called install.py. This will install all the necessary tables for you.

  ```shell
  python install.py
  ```

  * Create a database for django.

  ```sql
  create database ocptilecache_django;
  ```

##### Ctype

  * Read the instructions in the ocplib folder to install the ctype acclerations for this service

##### Logging
  
  * Make directories for logging. It has to have permission for the Web server (www-data or your user for the development server)

  ```shell
  mkdir /var/log/ocptilecache
  touch /var/log/ocptilecache/ocptilecache.log
  chown www-data:www-data -R /var/log/ocptilecache 
  mkdir /var/log/celery
  chown www-data:www-data -R /var/log/celery 
  ```

##### Nginx
  
  * Add the portions of default.nginx to /etc/nginx/sites-enabled/default

##### Supervisor

  * Copy celery.conf and reclaim.conf go in /etc/supervisor/conf.d/
  * Change the command and directory path values to the correct path in your system

##### uWSGI
  
  * Copy ocptilecache.ini in /etc/uwsgi/apps-enabled

##### Celery

  * Starting the celery dev server.  The service uses two queues.  For testing you can start them together.  For deployments, we should have them running separately as daemons.

  ```shell
  python manage.py celery worker --loglevel=info -Q celery,reclaim
  ```

  * If this works, stop the dev server.

##### Restart all services
  
  * Restart all the services
  
  ```shell
  sudo /etc/init.d/uwsgi restart ocptilecache
  sudo /etc/init.d/supervisor restart 
  sudo /etc/init.d/nginx restart 
  ```

  * And check their status

  ```shell
  sudo /etc/init.d/uwsgi status ocptilecache
  sudo /etc/init.d/supervisor status 
  sudo /etc/init.d/nginx status 
  ```

  * If all are running you should be good to go.

##### Configuring in CATMAID

  * Create a stack to a remote site.  It must have the following properties:
    * Image base = http://localhost/ocpcatmaid/[token]/
    * File extension = png
    * Tile width = 512
    * Tile height = 512
