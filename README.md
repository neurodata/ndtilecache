ocpcatmaid
==========

Caching gateway to connect a CATMAID server to the Open Connectome Project Web Services

  ** setup **
  
  Using mysql we need to creat the following tables.  The must be reabable by django, i.e. configure with the same database user used in django. 

    # RBTODO add foreign key constratin on datasets/metadata

    create database ocpcatmaid;
    use ocpcatmaid
    CREATE TABLE contents ( highkey BIGINT, lowkey BIGINT, filename varchar(255), reftime TIMESTAMP, PRIMARY KEY ( highkey, lowkey)); 
    CREATE TABLE datasets ( dataset VARCHAR(255) PRIMARY KEY, datasetid INT UNIQUE AUTO_INCREMENT );
    CREATE TABLE metadata ( numtiles BIGINT);
    CREATE TABLE fetching ( url VARCHAR(255) PRIMARY KEY );
    INSERT INTO metadata (numtiles) VALUES (0);

    # And a database for django

  Make directories for logging. It has to have permission for the Web server (www-data or your user for the development server)

    mkdir /var/log/ocpcatmaid
    chown /var/log/ocpcatmaid www-data
    mkdir /var/log/celery
    chown /var/log/celery www-data

  Starting the celery dev server.  The service uses two queues.  For testing you can start them together.  For deployments, we should have them running separately as daemons.

    python manage.py celery worker --loglevel=info -Q celery,reclaim

  If this works, stop the dev server.

  Follow all of the instructions in the ocpcatmaid/setup directory.  Then:

  Restart all the services
  
    sudo /etc/init.d/uwsgi restart ocpcatmaid
    sudo /etc/init.d/supervisor restart 
    sudo /etc/init.d/nginx restart 

  And check their status

    sudo /etc/init.d/uwsgi status ocpcatmaid
    sudo /etc/init.d/supervisor status 
    sudo /etc/init.d/nginx status 

  If all are running you should be good to go.

  ** Configuring in CATMAID **

  Create a stack to a remote site.  It must have the following properties:
    * Image base = http://localhost/ocpcatmaid/[token]/
    * File extension = png
    * Tile width = 512
    * Tile height = 512
  

