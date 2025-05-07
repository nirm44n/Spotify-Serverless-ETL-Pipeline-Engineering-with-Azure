# Spotify Serverless ETL Pipeline with Azure

A serverless ETL (Extract, Transform, Load) pipeline for Spotify playlist data using Azure Functions and Azure Blob Storage. This project demonstrates how to build a cloud-native data pipeline that extracts playlist information from Spotify, transforms it into structured formats, and loads it into Azure Blob Storage for further analysis.

## Architecture Overview

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Spotify API │────►│  Extract        │────►│ Azure Blob       │────►│ Transform      │
│              │     │  Function       │     │ Storage (Raw)    │     │ Function       │
└──────────────┘     └─────────────────┘     └──────────────────┘     └────────┬───────┘
                                                                               │
                                                                               ▼
                                                                      ┌────────────────┐
                                                                      │ Azure Blob     │
                                                                      │ Storage (CSV)  │
                                                                      └────────────────┘
```

## Features

- **HTTP-Triggered Extraction**: On-demand data extraction from Spotify's Global Top 50 playlist
- **Automated Transformation**: Blob-triggered function that transforms JSON data to structured CSVs
- **Data Organization**: Separate storage for raw and processed data
- **Error Handling**: Comprehensive error logging and handling
- **Serverless Architecture**: No infrastructure to manage, pay only for what you use

## Components

### 1. Extract Function (HTTP Triggered)

- Connects to Spotify API using client credentials
- Retrieves playlist data
- Stores raw JSON in Azure Blob Storage

### 2. Transform Function (Blob Triggered)

- Triggered when new files arrive in the "to_be_processed" folder
- Transforms JSON into structured CSV files for:
  - Songs
  - Artists
  - Albums
- Moves processed files to "processed" folder

## Prerequisites

- Azure subscription
- Azure Functions Core Tools
- Python 3.8+ installed
- Spotify Developer account with registered application

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Spotify-Serverless-ETL-Pipeline-Engineering-with-Azure.git
cd Spotify-Serverless-ETL-Pipeline-Engineering-with-Azure
```

### 2. Create Spotify Developer Application

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Note your Client ID and Client Secret

### 3. Set Up Local Development Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
cd SpotifyETL
pip install -r requirements.txt
```

### 4. Configure Local Settings

Create a `local.settings.json` file in the SpotifyETL directory:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "STORAGE_CONNNECTION_STRING": "YOUR_STORAGE_CONNECTION_STRING",
    "CLIENT_ID": "YOUR_SPOTIFY_CLIENT_ID",
    "CLIENT_SECRET": "YOUR_SPOTIFY_CLIENT_SECRET",
    "CONTAINER_NAME": "raw"
  }
}
```

### 5. Create Azure Resources

#### Storage Account

```bash
# Create resource group
az group create --name SpotifyETLGroup --location eastus

# Create storage account
az storage account create --name spotifyetlstorage --resource-group SpotifyETLGroup --location eastus --sku Standard_LRS

# Get connection string
az storage account show-connection-string --name spotifyetlstorage --resource-group SpotifyETLGroup --query connectionString --output tsv
```

#### Create Storage Containers

```bash
# Create containers
az storage container create --name raw --account-name spotifyetlstorage --auth-mode key

# Create subfolders by uploading empty placeholders
az storage blob upload --account-name spotifyetlstorage --container-name raw --name to_be_processed/.placeholder --file .placeholder --auth-mode key
az storage blob upload --account-name spotifyetlstorage --container-name raw --name processed/.placeholder --file .placeholder --auth-mode key
az storage blob upload --account-name spotifyetlstorage --container-name raw --name transformed_data/song_data/.placeholder --file .placeholder --auth-mode key
az storage blob upload --account-name spotifyetlstorage --container-name raw --name transformed_data/album_data/.placeholder --file .placeholder --auth-mode key
az storage blob upload --account-name spotifyetlstorage --container-name raw --name transformed_data/artist_data/.placeholder --file .placeholder --auth-mode key
```

#### Deploy Function App

```bash
# Create Function App
az functionapp create --name spotify-etl-functions --storage-account spotifyetlstorage --consumption-plan-location eastus --resource-group SpotifyETLGroup --runtime python --runtime-version 3.9 --functions-version 4

# Configure App Settings
az functionapp config appsettings set --name spotify-etl-functions --resource-group SpotifyETLGroup --settings "CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID" "CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET" "CONTAINER_NAME=raw"

# Deploy the functions
func azure functionapp publish spotify-etl-functions
```

## Local Development

```bash
# Start the function app locally
func start
```

## Usage

### Trigger Extract Function

Send a GET request to the extract function endpoint:

```
https://spotify-etl-functions.azurewebsites.net/api/spotify
```

This will:
1. Connect to Spotify API
2. Extract the Global Top 50 playlist data
3. Store raw JSON in the `raw/to_be_processed` container

### Automatic Transformation

When a new file is added to `raw/to_be_processed`:
1. The transform function is automatically triggered
2. Data is transformed into three CSV files (songs, artists, albums)
3. CSVs are stored in the `transformed_data` folder
4. Original file is moved to the `processed` folder

## Data Structure

### Raw JSON Format
```json
{
  "items": [
    {
      "track": {
        "id": "...",
        "name": "...",
        "duration_ms": 123456,
        "popularity": 90,
        "artists": [...],
        "album": {...}
      },
      "added_at": "2023-01-01T12:00:00Z"
    }
  ]
}
```

### Transformed CSV Structure

#### Songs Table
- song_id
- name
- duration_ms
- url
- popularity
- added_date
- album_id
- artist_id

#### Artists Table
- artist_id
- name
- url

#### Albums Table
- album_id
- name
- release_date
- total_tracks
- url

## Project Structure

```
Spotify-Serverless-ETL-Pipeline-Engineering-with-Azure/
├── SpotifyETL/
│   ├── function_app.py          # Function app initialization
│   ├── spotifyextract.py        # Extract function
│   ├── spotifytransform.py      # Transform function
│   ├── requirements.txt         # Python dependencies
│   └── local.settings.json      # Local settings (not committed to git)
├── .gitignore
├── LICENSE
└── README.md
```

## Monitoring and Debugging

- View function logs in Azure Portal
- Use Application Insights for monitoring
- Check Storage Explorer for data verification

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b new-feature`
3. Make your changes
4. Run tests locally
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Spotify Web API](https://developer.spotify.com/documentation/web-api)
- [Azure Functions Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [Spotipy Library](https://spotipy.readthedocs.io/)
