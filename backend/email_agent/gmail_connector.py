"""
Gmail Connector
Integration with Gmail API using existing Google OAuth infrastructure
"""
from typing import Optional, Dict, Any, List
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import EmailDraft, SendResult, EmailMessage


class GmailConnector:
    """Wrapper around Gmail API for email operations"""
    
    def __init__(self):
        self.service_cache = {}  # Cache Gmail service instances by access token
        logging.info("GmailConnector initialized")
    
    def _get_gmail_service(self, access_token: str):
        """Get or create Gmail API service instance"""
        if access_token not in self.service_cache:
            credentials = Credentials(token=access_token)
            self.service_cache[access_token] = build('gmail', 'v1', credentials=credentials)
        return self.service_cache[access_token]
    
    async def send_email(
        self,
        draft: EmailDraft,
        access_token: str
    ) -> SendResult:
        """Send an email via Gmail API"""
        
        try:
            logging.info(f"Sending email draft {draft.id} to {draft.to}")
            
            # Build email message
            message = self._create_message(
                to=draft.to,
                subject=draft.subject,
                body=draft.body,
                cc=draft.cc,
                bcc=draft.bcc
            )
            
            # Send via Gmail API
            service = self._get_gmail_service(access_token)
            sent_message = service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logging.info(f"Email sent successfully: {sent_message['id']}")
            
            return SendResult(
                draft_id=draft.id,
                success=True,
                gmail_message_id=sent_message.get('id'),
                gmail_thread_id=sent_message.get('threadId'),
                sent_at=datetime.utcnow()
            )
            
        except HttpError as e:
            error_msg = f"Gmail API error: {e.reason}"
            logging.error(f"Failed to send email {draft.id}: {error_msg}")
            return SendResult(
                draft_id=draft.id,
                success=False,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(f"Failed to send email {draft.id}: {error_msg}")
            return SendResult(
                draft_id=draft.id,
                success=False,
                error_message=error_msg
            )
    
    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Create email message in Gmail API format"""
        
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        return {'raw': raw_message}
    
    async def get_recent_emails(
        self,
        access_token: str,
        max_results: int = 5,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch recent emails for context (optional feature)"""
        
        try:
            service = self._get_gmail_service(access_token)
            
            # List messages
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query or ''
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch details for each message
            email_list = []
            for msg in messages:
                msg_detail = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_detail.get('payload', {}).get('headers', [])}
                
                email_list.append({
                    'id': msg_detail['id'],
                    'threadId': msg_detail.get('threadId'),
                    'from': headers.get('From'),
                    'to': headers.get('To'),
                    'subject': headers.get('Subject'),
                    'date': headers.get('Date')
                })
            
            return email_list
            
        except HttpError as e:
            logging.error(f"Failed to fetch emails: {e.reason}")
            return []
        except Exception as e:
            logging.error(f"Failed to fetch emails: {str(e)}")
            return []
    
    async def get_thread_messages(
        self,
        access_token: str,
        thread_id: str
    ) -> List[Dict[str, Any]]:
        """Get all messages in a thread for context"""
        
        try:
            service = self._get_gmail_service(access_token)
            
            thread = service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                messages.append({
                    'id': msg['id'],
                    'from': headers.get('From'),
                    'to': headers.get('To'),
                    'subject': headers.get('Subject'),
                    'date': headers.get('Date')
                })
            
            return messages
            
        except HttpError as e:
            logging.error(f"Failed to fetch thread {thread_id}: {e.reason}")
            return []
        except Exception as e:
            logging.error(f"Failed to fetch thread {thread_id}: {str(e)}")
            return []
    
    async def list_emails(
        self,
        access_token: str,
        max_results: int = 5,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List emails from Gmail inbox
        
        Args:
            access_token: OAuth access token
            max_results: Maximum number of emails to fetch (1-100)
            query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
            label_ids: List of label IDs to filter by (default: ['INBOX'])
            page_token: Token for pagination
            
        Returns:
            Dict with emails list, total_count, and next_page_token
        """
        try:
            service = self._get_gmail_service(access_token)
            
            # Build request parameters
            params = {
                'userId': 'me',
                'maxResults': min(max_results, 100)
            }
            
            if query:
                params['q'] = query
            
            if label_ids:
                params['labelIds'] = label_ids
            else:
                params['labelIds'] = ['INBOX']
            
            if page_token:
                params['pageToken'] = page_token
            
            # List messages
            results = service.users().messages().list(**params).execute()
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                try:
                    # Get full message details
                    email_data = await self.get_email(access_token, msg['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logging.warning(f"Failed to fetch email {msg['id']}: {e}")
                    continue
            
            return {
                'emails': emails,
                'total_count': len(emails),
                'next_page_token': results.get('nextPageToken')
            }
            
        except HttpError as e:
            error_msg = f"Gmail API error: {e.reason}"
            logging.error(f"Failed to list emails: {error_msg}")
            return {'emails': [], 'total_count': 0, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(f"Failed to list emails: {error_msg}")
            return {'emails': [], 'total_count': 0, 'error': error_msg}
    
    async def get_email(
        self,
        access_token: str,
        message_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get full details of a specific email
        
        Args:
            access_token: OAuth access token
            message_id: Gmail message ID
            
        Returns:
            Email data dict or None if not found
        """
        try:
            service = self._get_gmail_service(access_token)
            
            # Get full message details
            msg_data = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Parse headers
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            
            # Extract body content
            body = self._extract_body(msg_data['payload'])
            
            # Check if unread
            labels = msg_data.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            
            return {
                'id': msg_data['id'],
                'thread_id': msg_data['threadId'],
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'cc': headers.get('Cc'),
                'subject': headers.get('Subject', '(No Subject)'),
                'date': headers.get('Date', ''),
                'snippet': msg_data.get('snippet', ''),
                'body': body,
                'labels': labels,
                'is_unread': is_unread
            }
            
        except HttpError as e:
            logging.error(f"Gmail API error fetching email {message_id}: {e}")
            return None
            
        except Exception as e:
            logging.error(f"Error fetching email {message_id}: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract text body from email payload
        
        Handles both simple and multipart messages
        """
        body = ""
        
        # Check for parts (multipart message)
        if 'parts' in payload:
            for part in payload['parts']:
                # Prefer text/plain, fallback to text/html
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                # Recursively check nested parts
                elif 'parts' in part:
                    nested_body = self._extract_body(part)
                    if nested_body and not body:
                        body = nested_body
        
        # Simple message (no parts)
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        # Truncate very long bodies
        if len(body) > 5000:
            body = body[:5000] + '\n\n... (content truncated)'
        
        return body
    
    def clear_cache(self):
        """Clear cached Gmail service instances"""
        self.service_cache.clear()


# Global instance
gmail_connector = GmailConnector()


# Import datetime for SendResult
from datetime import datetime
