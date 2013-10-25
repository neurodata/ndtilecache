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
    INSERT INTO metadata (numtiles) VALUES (0);


    # And a database for django
    

  Make a directory for logging. It has to have permission for the Web server (www-data or your user for the development server)

    mkdir /var/log/ocpcatmaid

