"""
Google Docs Connector
Integration with Google Docs API using existing Google OAuth infrastructure
"""
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


class GoogleDocsConnector:
    """Wrapper around Google Docs API for document operations"""

    def __init__(self):
        self.service_cache = {}  # Cache Docs service instances by access token
        self.drive_service_cache = {}  # Cache Drive service instances by access token
        logging.info("GoogleDocsConnector initialized")

    def _get_docs_service(self, access_token: str):
        """Get or create Google Docs API service instance"""
        if access_token not in self.service_cache:
            credentials = Credentials(token=access_token)
            self.service_cache[access_token] = build('docs', 'v1', credentials=credentials)
        return self.service_cache[access_token]

    def _get_drive_service(self, access_token: str):
        """Get or create Google Drive API service instance"""
        if access_token not in self.drive_service_cache:
            credentials = Credentials(token=access_token)
            self.drive_service_cache[access_token] = build('drive', 'v3', credentials=credentials)
        return self.drive_service_cache[access_token]

    async def create_document(
        self,
        access_token: str,
        title: str,
        content: str = "",
        folder_id: str = None
    ) -> Dict[str, Any]:
        """Create a new Google Doc with content"""

        try:
            docs_service = self._get_docs_service(access_token)
            drive_service = self._get_drive_service(access_token)

            # Create the document
            doc_body = {
                'title': title
            }

            doc = docs_service.documents().create(body=doc_body).execute()
            doc_id = doc.get('documentId')

            # If content is provided, add it to the document
            if content:
                requests = []

                # Insert content at the beginning
                requests.append({
                    'insertText': {
                        'location': {
                            'index': 1
                        },
                        'text': content
                    }
                })

                # Execute the batch update
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()

            # If folder_id is provided, move the document to that folder
            if folder_id:
                # Remove from root
                drive_service.files().update(
                    fileId=doc_id,
                    removeParents='root',
                    fields='id, parents'
                ).execute()

                # Add to specified folder
                drive_service.files().update(
                    fileId=doc_id,
                    addParents=folder_id,
                    fields='id, parents'
                ).execute()

            # Set proper permissions to ensure the document is accessible
            # Make sure the owner has full access and the document is shared properly
            try:
                # First, check if permissions already exist
                existing_permissions = drive_service.permissions().list(fileId=doc_id).execute()
                owner_has_access = False
                
                for perm in existing_permissions.get('permissions', []):
                    if perm.get('type') == 'user' and perm.get('role') in ['owner', 'writer']:
                        owner_has_access = True
                        break
                
                # Only create permission if owner doesn't already have access
                if not owner_has_access:
                    permission = {
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': None  # This will default to the authenticated user
                    }
                    drive_service.permissions().create(
                        fileId=doc_id,
                        body=permission,
                        sendNotificationEmail=False
                    ).execute()
                
                # Ensure the document is marked as shared
                drive_service.files().update(
                    fileId=doc_id,
                    body={'shared': True},
                    fields='shared'
                ).execute()
                
            except Exception as perm_error:
                # Permission might already exist or other issues, log but don't fail
                logging.info(f"Permission setting note (may already exist): {perm_error}")
                # Continue anyway - the document should still be accessible

            # Get the final document details
            doc_details = drive_service.files().get(
                fileId=doc_id,
                fields='id, name, webViewLink, modifiedTime, createdTime, owners(displayName,emailAddress), shared, permissions'
            ).execute()

            return {
                'id': doc_details['id'],
                'title': doc_details['name'],
                'url': doc_details.get('webViewLink', ''),  # Use webViewLink which is valid
                'created_time': doc_details['createdTime'],
                'modified_time': doc_details['modifiedTime'],
                'owner': doc_details.get('owners', [{}])[0].get('displayName', ''),
                'shared': doc_details.get('shared', False),
                'status': 'created'
            }

        except HttpError as e:
            logging.error(f"Google Docs API error: {e}")
            return {
                'error': f"Failed to create document: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error creating document: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }

    async def get_document(
        self,
        access_token: str,
        document_id: str
    ) -> Dict[str, Any]:
        """Get a specific Google Doc by ID"""

        try:
            docs_service = self._get_docs_service(access_token)
            drive_service = self._get_drive_service(access_token)

            # Get document metadata from Drive
            doc_metadata = drive_service.files().get(
                fileId=document_id,
                fields='id, name, webViewLink, modifiedTime, createdTime, owners(displayName,emailAddress), shared, parents'
            ).execute()

            # Get document content from Docs
            doc_content = docs_service.documents().get(documentId=document_id).execute()

            # Extract plain text content
            content_text = self._extract_text_from_doc(doc_content)

            return {
                'id': doc_metadata['id'],
                'title': doc_metadata['name'],
                'url': doc_metadata.get('webViewLink', ''),  # Use webViewLink which is valid
                'content': content_text,
                'created_time': doc_metadata['createdTime'],
                'modified_time': doc_metadata['modifiedTime'],
                'owner': doc_metadata.get('owners', [{}])[0].get('displayName', ''),
                'shared': doc_metadata.get('shared', False),
                'status': 'found'
            }

        except HttpError as e:
            logging.error(f"Google Docs API error: {e}")
            return {
                'error': f"Failed to get document: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error getting document: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }

    def _extract_text_from_doc(self, doc_content: Dict[str, Any]) -> str:
        """Extract plain text from Google Doc content"""
        text_content = []

        if 'body' in doc_content and 'content' in doc_content['body']:
            for element in doc_content['body']['content']:
                if 'paragraph' in element:
                    for paragraph_element in element['paragraph']['elements']:
                        if 'textRun' in paragraph_element:
                            text_content.append(paragraph_element['textRun']['content'])

        return ''.join(text_content)

    async def update_document(
        self,
        access_token: str,
        document_id: str,
        title: str = None,
        content: str = None,
        append_content: bool = False
    ) -> Dict[str, Any]:
        """Update an existing Google Doc"""

        try:
            docs_service = self._get_docs_service(access_token)
            drive_service = self._get_drive_service(access_token)

            requests = []

            # Update title if provided
            if title:
                drive_service.files().update(
                    fileId=document_id,
                    body={'name': title}
                ).execute()

            # Update content if provided
            if content:
                if append_content:
                    # Get current document to find end position
                    doc = docs_service.documents().get(documentId=document_id).execute()
                    end_index = doc['body']['content'][-1]['endIndex'] if doc['body']['content'] else 1

                    requests.append({
                        'insertText': {
                            'location': {
                                'index': end_index - 1
                            },
                            'text': '\n' + content
                        }
                    })
                else:
                    # Replace all content
                    # First, get the current content length
                    doc = docs_service.documents().get(documentId=document_id).execute()
                    end_index = doc['body']['content'][-1]['endIndex'] if doc['body']['content'] else 1

                    # Delete existing content (except the last newline)
                    if end_index > 1:
                        requests.append({
                            'deleteContentRange': {
                                'range': {
                                    'startIndex': 1,
                                    'endIndex': end_index - 1
                                }
                            }
                        })

                    # Insert new content
                    requests.append({
                        'insertText': {
                            'location': {
                                'index': 1
                            },
                            'text': content
                        }
                    })

                # Execute batch update
                if requests:
                    docs_service.documents().batchUpdate(
                        documentId=document_id,
                        body={'requests': requests}
                    ).execute()

            # Get updated document details
            doc_details = drive_service.files().get(
                fileId=document_id,
                fields='id, name, webViewLink, modifiedTime'
            ).execute()

            return {
                'id': doc_details['id'],
                'title': doc_details['name'],
                'url': doc_details.get('webViewLink', ''),  # Use webViewLink which is valid
                'modified_time': doc_details['modifiedTime'],
                'status': 'updated'
            }

        except HttpError as e:
            logging.error(f"Google Docs API error: {e}")
            return {
                'error': f"Failed to update document: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error updating document: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }

    async def list_documents(
        self,
        access_token: str,
        max_results: int = 10,
        query: str = None,
        folder_id: str = None
    ) -> Dict[str, Any]:
        """List Google Docs"""

        try:
            drive_service = self._get_drive_service(access_token)

            # Build query
            mime_type = "application/vnd.google-apps.document"
            search_query = f"mimeType='{mime_type}' and trashed=false"

            if query:
                search_query += f" and name contains '{query}'"

            if folder_id:
                search_query += f" and '{folder_id}' in parents"

            results = drive_service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, webViewLink, modifiedTime, createdTime, owners(displayName,emailAddress), shared)",
                orderBy="modifiedTime desc"
            ).execute()

            files = results.get('files', [])

            formatted_docs = []
            for file in files:
                formatted_docs.append({
                    'id': file['id'],
                    'title': file['name'],
                    'url': file['webViewLink'],
                    'created_time': file['createdTime'],
                    'modified_time': file['modifiedTime'],
                    'owner': file.get('owners', [{}])[0].get('displayName', ''),
                    'shared': file.get('shared', False)
                })

            return {
                'documents': formatted_docs,
                'total_count': len(formatted_docs),
                'status': 'success'
            }

        except HttpError as e:
            logging.error(f"Google Drive API error: {e}")
            return {
                'error': f"Failed to list documents: {str(e)}",
                'documents': [],
                'total_count': 0,
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error listing documents: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'documents': [],
                'total_count': 0,
                'status': 'error'
            }

    async def search_documents(
        self,
        access_token: str,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Google Docs by content or title"""

        try:
            drive_service = self._get_drive_service(access_token)

            # Search by title first
            mime_type = "application/vnd.google-apps.document"
            title_query = f"mimeType='{mime_type}' and trashed=false and name contains '{query}'"

            results = drive_service.files().list(
                q=title_query,
                pageSize=max_results,
                fields="files(id, name, webViewLink, modifiedTime, createdTime, owners(displayName,emailAddress), shared)",
                orderBy="modifiedTime desc"
            ).execute()

            files = results.get('files', [])

            # If not enough results, we could search content, but Drive API doesn't support full-text search
            # For now, just return title matches

            formatted_docs = []
            for file in files:
                formatted_docs.append({
                    'id': file['id'],
                    'title': file['name'],
                    'url': file['webViewLink'],
                    'created_time': file['createdTime'],
                    'modified_time': file['modifiedTime'],
                    'owner': file.get('owners', [{}])[0].get('displayName', ''),
                    'shared': file.get('shared', False)
                })

            return {
                'documents': formatted_docs,
                'total_count': len(formatted_docs),
                'status': 'success'
            }

        except HttpError as e:
            logging.error(f"Google Drive API error: {e}")
            return {
                'error': f"Failed to search documents: {str(e)}",
                'documents': [],
                'total_count': 0,
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error searching documents: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'documents': [],
                'total_count': 0,
                'status': 'error'
            }

    async def delete_document(
        self,
        access_token: str,
        document_id: str
    ) -> Dict[str, Any]:
        """Delete a Google Doc (move to trash)"""

        try:
            drive_service = self._get_drive_service(access_token)

            # Get document details before deleting
            doc_details = drive_service.files().get(
                fileId=document_id,
                fields='name'
            ).execute()
            doc_title = doc_details.get('name', 'Untitled Document')

            # Move to trash (soft delete)
            drive_service.files().update(
                fileId=document_id,
                body={'trashed': True}
            ).execute()

            return {
                'id': document_id,
                'title': doc_title,
                'status': 'deleted',
                'message': f"Successfully moved document '{doc_title}' to trash"
            }

        except HttpError as e:
            logging.error(f"Google Drive API error: {e}")
            return {
                'error': f"Failed to delete document: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error deleting document: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }