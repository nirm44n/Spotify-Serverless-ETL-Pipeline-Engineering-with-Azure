import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
from datetime import datetime
import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()
# Get environment variables
CLIENT_ID = os.environ.get('CLIENT_ID')
SECRET_ID = os.environ.get('CLIENT_SECRET')
STORAGE_CONNECTION_STRING = os.environ.get('AzureWebJobsStorage')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', "raw")


def register_spotify_ingestion(app):
    """
    Register the Spotify data ingestion function with the Azure Functions app.
    
    This function extracts data from Spotify API and stores it in Azure Blob Storage.
    
    Args:
        app: The Azure Functions app instance
    """
    @app.route(route="spotify", methods=["GET"])
    def spotify_http_trigger(req: func.HttpRequest) -> func.HttpResponse:
        """
        HTTP-triggered Azure Function that extracts data from Spotify API.
        
        Extracts playlist data from Spotify and uploads raw JSON to Azure Blob Storage
        in the to_be_processed folder for later transformation.
        
        Args:
            req: HTTP request object
            
        Returns:
            HTTP response indicating success or failure
        """
        logging.info('Spotify data extraction function triggered via HTTP')
        
        try:
            # Verify environment variables
            if not CLIENT_ID or not SECRET_ID:
                logging.error("Missing Spotify API credentials")
                return func.HttpResponse(
                    "Please configure Spotify API credentials in application settings.",
                    status_code=500
                )

            if not STORAGE_CONNECTION_STRING:
                logging.error("Missing Azure Storage connection string")
                return func.HttpResponse(
                    "Please configure Azure Storage settings in application settings.",
                    status_code=500
                )
            
            # Set up Spotify client
            try:
                client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=SECRET_ID)
                sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                logging.info("Successfully connected to Spotify API")
            except Exception as e:
                logging.error(f"Failed to initialize Spotify client: {str(e)}")
                return func.HttpResponse(
                    f"Error connecting to Spotify API: {str(e)}",
                    status_code=500
                )
            
            # Use a reliable playlist ID - Global Top 50
            try:
                top50_playlist_url = "https://open.spotify.com/playlist/6UeSakyzhiEt4NB3UAd6NQ"
                data = sp.playlist_tracks(top50_playlist_url)
                logging.info(f"Successfully retrieved playlist data with {len(data.get('items', []))} tracks")
            except Exception as e:
                logging.error(f"Failed to retrieve playlist data: {str(e)}")
                return func.HttpResponse(
                    f"Error retrieving playlist data: {str(e)}",
                    status_code=500
                )
            
            # Upload data to Azure Blob Storage
            try:
                # Create the BlobServiceClient
                blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
                
                # Get container client
                container_client = blob_service_client.get_container_client(CONTAINER_NAME)
                
                # Create the blob name (path)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f'spotify_raw_{timestamp}.json'
                blob_path = f'to_be_processed/{file_name}'
                
                # Get the blob client
                blob_client = container_client.get_blob_client(blob_path)
                
                # Upload data - ensure proper JSON serialization
                json_data = json.dumps(data, indent=2)
                blob_client.upload_blob(json_data, overwrite=True)
                
                logging.info(f"Successfully uploaded data to {blob_path}")
            except Exception as e:
                logging.error(f"Failed to upload data to Azure Blob Storage: {str(e)}")
                return func.HttpResponse(
                    f"Error uploading data to storage: {str(e)}",
                    status_code=500
                )
            
            # Return success response
            return func.HttpResponse(
                body=f"Data successfully uploaded to {blob_path}",
                mimetype="text/plain",
                status_code=200
            )
        except Exception as e:
            error_message = str(e)
            logging.error(f"Unexpected error in Spotify data extraction: {error_message}")
            return func.HttpResponse(
                body=f"Error processing request: {error_message}",
                mimetype="text/plain",
                status_code=500
            )