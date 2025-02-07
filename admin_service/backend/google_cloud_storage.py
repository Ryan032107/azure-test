from google.cloud import storage
import magic
import os
from dotenv import load_dotenv

load_dotenv()

class GoogleCloudStorage:
    def __init__(self, bucket_name, folder):
        self.bucket_name = bucket_name
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.folder = folder
    def upload_file(self, source_file, destination_blob_name, folder_name=None):
        if folder_name:
            destination_blob_name = self.folder + '/' + folder_name + '/' + destination_blob_name
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_file(source_file)

    def delete_file(self, blob_name, folder_name=None):
        if folder_name:
            blob_name = self.folder + '/' + folder_name + '/' + blob_name
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
        
    def download_file(self, source_blob_name):
        bucket = self.bucket
        source_blob_name = self.folder + '/' + source_blob_name
        blob = bucket.blob(source_blob_name)

        # Fetch the content type
        content_type = blob.content_type
        
        # Download the contents of the blob as bytes
        file_data = blob.download_as_bytes()

        # Determine the content type if it is not set
        if content_type is None:
            mime = magic.Magic(mime=True)
            content_type = mime.from_buffer(file_data)
        return content_type, file_data

    def get_bucket_size(self, folder_name):
         total_size_byte = 0
         for blob in self.bucket.list_blobs(prefix=folder_name):
             total_size_byte += blob.size
         total_size_gb = total_size_byte / (1024 ** 3)

         return round(total_size_gb, 4)