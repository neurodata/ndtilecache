from django.db import models

class ProjectServer ( models.Model ):
  project = models.CharField(max_length=255, primary_key=True)
  server = models.CharField(max_length=255)
