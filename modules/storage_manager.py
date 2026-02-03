"""
Storage Manager Module
- Handles file uploads, retrievals, and deletions with Supabase Storage
"""
import os
import mimetypes
from typing import Optional, List, Dict, Union
from supabase import create_client, Client

class StorageManager:
    """Class for managing Supabase Storage operations"""
    
    BUCKET_NAME = "product-dev-images"
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            # Try loading from Streamlit secrets
            try:
                import streamlit as st
                url = st.secrets["SUPABASE_URL"]
                key = st.secrets["SUPABASE_KEY"]
            except:
                pass

        if not url or not key:
            print("Warning: SUPABASE_URL or SUPABASE_KEY not found.")
            self.supabase: Optional[Client] = None
        else:
            self.supabase: Client = create_client(url, key)
            
    def upload_file(self, file_obj, path: str, content_type: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Supabase Storage
        
        Args:
            file_obj: File-like object or bytes
            path: Destination path in the bucket (e.g., 'folder/filename.jpg')
            content_type: MIME type of the file
            
        Returns:
            Public URL of the uploaded file or None if failed
        """
        if not self.supabase:
            return None
            
        try:
            # Ensure bucket exists (optional, usually created manually)
            # self.supabase.storage.create_bucket(self.BUCKET_NAME, options={'public': True})
            
            # Prepare file options
            file_options = {"upsert": "true"}
            if content_type:
                file_options["content-type"] = content_type
            
            # Read bytes if it's a Streamlit UploadedFile
            if hasattr(file_obj, "getvalue"):
                data = file_obj.getvalue()
            elif hasattr(file_obj, "read"):
                data = file_obj.read()
            else:
                data = file_obj
                
            # Upload
            self.supabase.storage.from_(self.BUCKET_NAME).upload(
                path=path,
                file=data,
                file_options=file_options
            )
            
            # Get public URL
            return self.get_public_url(path)
            
        except Exception as e:
            print(f"Storage Upload Error: {e}")
            return None
            
    def get_public_url(self, path: str) -> str:
        """Get the public URL for a file"""
        if not self.supabase:
            return ""
            
        return self.supabase.storage.from_(self.BUCKET_NAME).get_public_url(path)
        
    def list_files(self, folder: str) -> List[Dict]:
        """List files in a folder"""
        if not self.supabase:
            return []
            
        try:
            return self.supabase.storage.from_(self.BUCKET_NAME).list(folder)
        except Exception as e:
            print(f"Storage List Error: {e}")
            return []
            
    def delete_file(self, path: str) -> bool:
        """Delete a file"""
        if not self.supabase:
            return False
            
        try:
            self.supabase.storage.from_(self.BUCKET_NAME).remove([path])
            return True
        except Exception as e:
            print(f"Storage Delete Error: {e}")
            return False

    def get_file_bytes(self, path: str) -> Optional[bytes]:
        """Download file content as bytes"""
        if not self.supabase:
            return None

        try:
            return self.supabase.storage.from_(self.BUCKET_NAME).download(path)
        except Exception as e:
            print(f"Storage Download Error: {e}")
            return None
