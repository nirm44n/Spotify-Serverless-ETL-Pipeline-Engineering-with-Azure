import azure.functions as func
import os
import logging

from spotifyextract import register_spotify_ingestion
from spotifytransform import register_spotify_transformation

app = func.FunctionApp()

register_spotify_ingestion(app)
register_spotify_transformation(app)