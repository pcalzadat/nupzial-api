from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import os
import uuid
from typing import Optional, Tuple, Union
from fastapi import HTTPException

def upload_to_blob_storage(
    file_path: str,
    content_type: str,
    filename: str,
    folder: str = "",
    generate_sas: bool = False
) -> Tuple[str, str]:
    """
    Uploads a file to Azure Blob Storage and returns its ID and public URL.
    
    Args:
        file_path: Path to the file to upload
        content_type: MIME type of the file (e.g. 'image/jpeg', 'video/mp4')
        folder: Optional folder name within the container
        generate_sas: Whether to generate a SAS token for private containers
    
    Returns:
        Tuple containing (file_id, public_url)
    """

    print("Uploading file to blob storage:", file_path)
    try:
        # Get connection string from environment
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            raise HTTPException(status_code=500, detail="Missing AZURE_STORAGE_CONNECTION_STRING")

        # Generate unique file ID
        #file_id = uuid.uuid4().hex
        
        # Create blob name with optional folder
        blob_name = f"{folder}/{filename}" if folder else filename
        
        # Add file extension from content type
        if content_type == "image/jpeg":
            blob_name += ".jpg"
        elif content_type == "image/png":
            blob_name += ".png"
        elif content_type == "video/mp4":
            blob_name += ".mp4"
        
        # Get container name
        container = os.getenv("AZURE_BLOB_CONTAINER", "public-data")
        
        # Create blob client
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        blob_client = blob_service.get_blob_client(container=container, blob=blob_name)

        # Upload file with content settings
        with open(file_path, "rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )

        # Generate base URL
        public_url = f"{blob_service.url}{container}/{blob_name}"

        # Add SAS token if requested
        if generate_sas:
            account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
            if account_key:
                sas = generate_blob_sas(
                    account_name=blob_service.account_name,
                    container_name=container,
                    blob_name=blob_name,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=24)
                )
                public_url = f"{public_url}?{sas}"

        return filename, public_url

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading to blob storage: {str(e)}")

def upload_bytes_to_blob_storage(
    video_content: bytes,
    content_settings: Union[ContentSettings, dict],
    filename: str,
    folder: str,
    generate_sas: bool = False
) -> Tuple[str, str]:
    """
    Upload raw bytes to Azure Blob Storage and return (file_id, public_url).

    Args:
        video_content: Raw bytes to upload.
        content_settings: ContentSettings instance or dict with content metadata (must include content_type).
        folder: Optional folder within the container.
        generate_sas: Whether to generate a SAS token for the returned URL.
    """
    try:
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            raise HTTPException(status_code=500, detail="Missing AZURE_STORAGE_CONNECTION_STRING")

        #file_id = uuid.uuid4().hex
        blob_name = f"{folder}/{filename}" if folder else filename

        # Normalize ContentSettings
        if isinstance(content_settings, dict):
            try:
                cs = ContentSettings(**content_settings)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid content_settings dict: {e}")
        else:
            cs = content_settings  # assume ContentSettings

        # Try to append extension based on content_type when possible
        ctype = getattr(cs, "content_type", None)
        if ctype == "image/jpeg":
            blob_name += ".jpg"
        elif ctype == "image/png":
            blob_name += ".png"
        elif ctype == "video/mp4":
            blob_name += ".mp4"

        container = os.getenv("AZURE_BLOB_CONTAINER", "public-data")
        blob_service = BlobServiceClient.from_connection_string(conn_str)
        blob_client = blob_service.get_blob_client(container=container, blob=blob_name)

        # Upload raw bytes
        blob_client.upload_blob(
            video_content,
            overwrite=True,
            content_settings=cs
        )

        public_url = f"{blob_service.url}{container}/{blob_name}"

        if generate_sas:
            account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
            if account_key:
                sas = generate_blob_sas(
                    account_name=blob_service.account_name,
                    container_name=container,
                    blob_name=blob_name,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=24)
                )
                public_url = f"{public_url}?{sas}"

        return filename, public_url

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading bytes to blob storage: {str(e)}")