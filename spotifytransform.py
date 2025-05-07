import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
from datetime import datetime
import azure.functions as func
import io
import pandas as pd
from azure.storage.blob import BlobServiceClient, ContentSettings

app = func.FunctionApp()
# Get environment variables
CLIENT_ID = os.environ.get('CLIENT_ID')
SECRET_ID = os.environ.get('CLIENT_SECRET')
STORAGE_CONNECTION_STRING = os.environ.get('AzureWebJobsStorage')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', "raw")

def make_csv_buffer(df):
    """Convert DataFrame to CSV string buffer for uploading"""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_content = csv_buffer.getvalue()
    return csv_content

def make_album(data):
    """Extract album data from Spotify API response"""
    album_df_list = []
    for song in data['items']:
        album_id = song['track']['album']['id']
        album_name = song['track']['album']['name']
        release_date = song['track']['album']['release_date']
        total_tracks = song['track']['album']['total_tracks']
        album_url = song['track']['album']['external_urls']['spotify']
        row_data = [album_id, album_name, release_date, total_tracks, album_url]
        album_df_list.append(row_data)
    return album_df_list

def make_artist(data):
    """Extract artist data from Spotify API response"""
    artist_df_list = []
    for song in data['items']:
        artist_id = song['track']['artists'][0]['id']
        artist_name = song['track']['artists'][0]['name']
        artist_url = song['track']['artists'][0]['external_urls']['spotify']
        row_data = [artist_id, artist_name, artist_url]
        artist_df_list.append(row_data)
    return artist_df_list
    
def make_song(data):
    """Extract song data from Spotify API response"""
    song_df_list = []
    for song in data['items']:
        song_id = song['track']['id']
        song_name = song['track']['name']
        duration_ms = song['track']['duration_ms']
        url = song['track']['external_urls']['spotify']
        popularity = song['track']['popularity']
        song_added = song['added_at']
        album_id = song['track']['album']['id']
        artist_id = song['track']['artists'][0]['id']
        row_data = [song_id, song_name, duration_ms, url, popularity, song_added, album_id, artist_id]
        song_df_list.append(row_data)
    return song_df_list

def register_spotify_transformation(app):
    @app.blob_trigger(arg_name="myblob", path="raw/to_be_processed/{name}", connection="AzureWebJobsStorage")
    def TransformSpotifyData(myblob: func.InputStream):
        """
        Azure Function triggered when a new JSON file is added to the 'raw/to_be_processed' container.
        Transforms Spotify playlist data into structured CSV files for songs, artists, and albums.
        """
        logging.info(f"Python blob trigger function processed blob\n"
                    f"Name: {myblob.name}\n"
                    f"Blob Size: {myblob.length} bytes")
        
        try:
            # Process the triggered blob
            raw_data = json.loads(myblob.read().decode('utf-8'))
            
            # Create the BlobServiceClient
            blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)

            # Process the triggered data
            album_df_list = make_album(raw_data)
            artist_df_list = make_artist(raw_data)
            song_df_list = make_song(raw_data)

            # Create and clean dataframes
            song_df = pd.DataFrame(song_df_list, columns=['song_id', 'name', 'duration_ms', 'url', 'popularity', 'added_date', 'album_id', 'artist_id'])
            song_df['added_date'] = pd.to_datetime(song_df['added_date'])
            
            artist_df = pd.DataFrame(artist_df_list, columns=['artist_id', 'name', 'url'])
            artist_df.drop_duplicates(subset='artist_id', keep='first', inplace=True, ignore_index=True)
            
            album_df = pd.DataFrame(album_df_list, columns=['album_id', 'name', 'release_date', 'total_tracks', 'url'])
            album_df.drop_duplicates(subset='album_id', keep='first', inplace=True, ignore_index=True)
            album_df['release_date'] = pd.to_datetime(album_df['release_date'])
            
            # Generate output paths with timestamps
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            song_key = f'transformed_data/song_data/song_transformed_{timestamp}.csv'
            album_key = f'transformed_data/album_data/album_transformed_{timestamp}.csv'
            artist_key = f'transformed_data/artist_data/artist_transformed_{timestamp}.csv'
            
            # Upload transformed CSV files with content type for CSV
            content_settings = ContentSettings(content_type='text/csv')
            
            try:
                container_client.upload_blob(
                    name=song_key, 
                    data=make_csv_buffer(song_df),
                    content_settings=content_settings,
                    overwrite=True
                )
                
                container_client.upload_blob(
                    name=album_key, 
                    data=make_csv_buffer(album_df),
                    content_settings=content_settings,
                    overwrite=True
                )
                
                container_client.upload_blob(
                    name=artist_key, 
                    data=make_csv_buffer(artist_df),
                    content_settings=content_settings,
                    overwrite=True
                )
                
                logging.info(f"Transformed data uploaded to {song_key}, {album_key}, {artist_key}")
            except Exception as e:
                logging.error(f"Error uploading transformed data: {str(e)}")
                raise
            
            # Move processed file to 'processed' folder
            try:
                # Get the source blob name from the trigger
                file_name = myblob.name.split('/')[-1]
                source_path = f"to_be_processed/{file_name}"
                target_path = f"processed/{file_name}"
                
                # Get the content from the source blob
                source_blob_client = container_client.get_blob_client(source_path)
                file_content = source_blob_client.download_blob().readall()
                
                # Upload to processed folder
                processed_blob_client = container_client.get_blob_client(target_path)
                processed_blob_client.upload_blob(file_content, overwrite=True)
                
                # Delete the original file
                source_blob_client.delete_blob()
                
                logging.info(f"Moved {source_path} to {target_path}")
            except Exception as e:
                logging.error(f"Error moving processed file: {str(e)}")
                # Continue anyway as the transformation was successful
                
            logging.info('Spotify ETL transformation function completed successfully')
        except Exception as e:
            logging.error(f"Error in Spotify ETL transformation: {str(e)}")
            raise