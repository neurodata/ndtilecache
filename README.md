ocpcatmaid
==========

Caching gateway to connect a CATMAID server to the Open Connectome Project Web Services




  ** setup **
  
  Using mysql we need to creat the following tables.  The must be reabable by django, i.e. configure with the same database user used in django. 

  create database ocpcatmaid;
  use ocpcatmaid
  CREATE TABLE prefetch ( id int NOT NULL AUTO_INCREMENT PRIMARY KEY, url varchar(255) ); 
  CREATE TABLE contents ( url varchar(255), reftime TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (reftime, url)); 
