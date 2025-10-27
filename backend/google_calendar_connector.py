"""
Google Calendar Connector
Integration with Google Calendar API using existing Google OAuth infrastructure
"""
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarConnector:
    """Wrapper around Google Calendar API for calendar operations"""

    def __init__(self):
        self.service_cache = {}  # Cache Calendar service instances by access token
        logging.info("GoogleCalendarConnector initialized")

    def _get_calendar_service(self, access_token: str):
        """Get or create Google Calendar API service instance"""
        if access_token not in self.service_cache:
            credentials = Credentials(token=access_token)
            self.service_cache[access_token] = build('calendar', 'v3', credentials=credentials)
        return self.service_cache[access_token]

    async def create_event(
        self,
        access_token: str,
        title: str,
        start_date: str,
        end_date: str,
        description: str = "",
        attendees: List[str] = None,
        location: str = "",
        recurrence: List[str] = None
    ) -> Dict[str, Any]:
        """Create a calendar event with attendees"""

        try:
            service = self._get_calendar_service(access_token)

            # Detect timezone from datetime string
            # If no timezone specified, default to UTC
            def detect_timezone(dt_string):
                if 'Z' in dt_string:
                    return 'UTC'
                elif '+' in dt_string or dt_string.count('-') > 2:  # Has timezone offset like +05:30
                    # Google Calendar will use the offset from the dateTime string
                    return None  # Let Google infer from the string
                else:
                    # No timezone specified - default to UTC
                    return 'UTC'

            start_tz = detect_timezone(start_date)
            end_tz = detect_timezone(end_date)

            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_date,
                },
                'end': {
                    'dateTime': end_date,
                }
            }
            
            # Only add timeZone if explicitly needed
            if start_tz:
                event['start']['timeZone'] = start_tz
            if end_tz:
                event['end']['timeZone'] = end_tz

            if location:
                event['location'] = location

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            if recurrence:
                event['recurrence'] = recurrence

            created_event = service.events().insert(calendarId='primary', body=event).execute()

            return {
                'id': created_event['id'],
                'title': created_event['summary'],
                'start': created_event['start']['dateTime'],
                'end': created_event['end']['dateTime'],
                'description': created_event.get('description', ''),
                'attendees': [attendee['email'] for attendee in created_event.get('attendees', [])],
                'meeting_link': created_event.get('hangoutLink', ''),
                'recurrence': created_event.get('recurrence', []),
                'status': 'created'
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to create calendar event: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error creating calendar event: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }

    async def list_events(
        self,
        access_token: str,
        max_results: int = 10,
        time_min: str = None
    ) -> Dict[str, Any]:
        """List upcoming calendar events"""

        try:
            service = self._get_calendar_service(access_token)

            # Default to now if no time_min provided
            if not time_min:
                time_min = datetime.now(timezone.utc).isoformat()

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                formatted_events.append({
                    'id': event['id'],
                    'title': event['summary'],
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': [attendee['email'] for attendee in event.get('attendees', [])],
                    'meeting_link': event.get('hangoutLink', ''),
                    'status': event['status']
                })

            return {
                'events': formatted_events,
                'total_count': len(formatted_events),
                'status': 'success'
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to list calendar events: {str(e)}",
                'events': [],
                'total_count': 0,
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error listing calendar events: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'events': [],
                'total_count': 0,
                'status': 'error'
            }

    async def get_event(
        self,
        access_token: str,
        event_id: str
    ) -> Dict[str, Any]:
        """Get a specific calendar event by ID"""

        try:
            service = self._get_calendar_service(access_token)

            event = service.events().get(calendarId='primary', eventId=event_id).execute()

            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            return {
                'id': event['id'],
                'title': event['summary'],
                'start': start,
                'end': end,
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'attendees': [attendee['email'] for attendee in event.get('attendees', [])],
                'meeting_link': event.get('hangoutLink', ''),
                'recurrence': event.get('recurrence', []),
                'status': event['status'],
                'event_status': 'found'
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to get calendar event: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error getting calendar event: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }

    async def search_events(
        self,
        access_token: str,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Search calendar events by query"""

        try:
            service = self._get_calendar_service(access_token)

            events_result = service.events().list(
                calendarId='primary',
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                formatted_events.append({
                    'id': event['id'],
                    'title': event['summary'],
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': [attendee['email'] for attendee in event.get('attendees', [])],
                    'meeting_link': event.get('hangoutLink', ''),
                    'recurrence': event.get('recurrence', []),
                    'status': event['status']
                })

            return {
                'events': formatted_events,
                'total_count': len(formatted_events),
                'status': 'success'
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to search calendar events: {str(e)}",
                'events': [],
                'total_count': 0,
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error searching calendar events: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'events': [],
                'total_count': 0,
                'status': 'error'
            }

    async def find_free_slots(
        self,
        access_token: str,
        time_min: str,
        time_max: str,
        duration_minutes: int = 60,
        attendees: List[str] = None
    ) -> Dict[str, Any]:
        """Find free time slots for scheduling"""

        try:
            service = self._get_calendar_service(access_token)

            # Include own calendar and attendees
            calendar_ids = ['primary']
            if attendees:
                calendar_ids.extend(attendees)

            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "timeZone": "UTC",
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }

            freebusy_result = service.freebusy().query(body=body).execute()

            # Parse free/busy to find free slots
            # This is a simplified version - in practice, you'd need more complex logic
            busy_periods = []
            for cal_id, cal_data in freebusy_result.get('calendars', {}).items():
                busy_periods.extend(cal_data.get('busy', []))

            # Sort busy periods
            busy_periods.sort(key=lambda x: x['start'])

            # Find gaps between busy periods
            from datetime import datetime, timedelta
            free_slots = []
            current_time = datetime.fromisoformat(time_min.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(time_max.replace('Z', '+00:00'))

            for busy in busy_periods:
                busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))

                if busy_start > current_time:
                    gap_duration = (busy_start - current_time).total_seconds() / 60
                    if gap_duration >= duration_minutes:
                        free_slots.append({
                            'start': current_time.isoformat(),
                            'end': busy_start.isoformat(),
                            'duration_minutes': gap_duration
                        })

                current_time = max(current_time, busy_end)

            # Check final gap
            if end_time > current_time:
                gap_duration = (end_time - current_time).total_seconds() / 60
                if gap_duration >= duration_minutes:
                    free_slots.append({
                        'start': current_time.isoformat(),
                        'end': end_time.isoformat(),
                        'duration_minutes': gap_duration
                    })

            return {
                'free_slots': free_slots[:10],  # Limit to 10 suggestions
                'total_slots': len(free_slots),
                'status': 'success'
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to find free slots: {str(e)}",
                'free_slots': [],
                'total_slots': 0,
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error finding free slots: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'free_slots': [],
                'total_slots': 0,
                'status': 'error'
            }

    async def update_event(
        self,
        access_token: str,
        event_id: str,
        title: str = None,
        start_date: str = None,
        end_date: str = None,
        description: str = None,
        attendees: List[str] = None,
        location: str = None,
        recurrence: List[str] = None
    ) -> Dict[str, Any]:
        """Update an existing calendar event"""

        try:
            service = self._get_calendar_service(access_token)

            # First, get the existing event
            event = service.events().get(calendarId='primary', eventId=event_id).execute()

            # Update only provided fields
            if title is not None:
                event['summary'] = title
            
            if start_date is not None:
                # Detect timezone
                def detect_timezone(dt_string):
                    if 'Z' in dt_string:
                        return 'UTC'
                    elif '+' in dt_string or dt_string.count('-') > 2:
                        return None
                    else:
                        return 'UTC'

                start_tz = detect_timezone(start_date)
                event['start'] = {'dateTime': start_date}
                if start_tz:
                    event['start']['timeZone'] = start_tz
            
            if end_date is not None:
                def detect_timezone(dt_string):
                    if 'Z' in dt_string:
                        return 'UTC'
                    elif '+' in dt_string or dt_string.count('-') > 2:
                        return None
                    else:
                        return 'UTC'

                end_tz = detect_timezone(end_date)
                event['end'] = {'dateTime': end_date}
                if end_tz:
                    event['end']['timeZone'] = end_tz
            
            if description is not None:
                event['description'] = description
            
            if location is not None:
                event['location'] = location
            
            if attendees is not None:
                event['attendees'] = [{'email': email} for email in attendees]
            
            if recurrence is not None:
                event['recurrence'] = recurrence

            # Update the event
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()

            return {
                'id': updated_event['id'],
                'title': updated_event['summary'],
                'start': updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                'end': updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                'description': updated_event.get('description', ''),
                'attendees': [attendee['email'] for attendee in updated_event.get('attendees', [])],
                'meeting_link': updated_event.get('hangoutLink', ''),
                'recurrence': updated_event.get('recurrence', []),
                'status': 'updated'
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to update calendar event: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error updating calendar event: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }

    async def delete_event(
        self,
        access_token: str,
        event_id: str
    ) -> Dict[str, Any]:
        """Delete a calendar event"""

        try:
            service = self._get_calendar_service(access_token)

            # Get event details before deleting (for confirmation message)
            try:
                event = service.events().get(calendarId='primary', eventId=event_id).execute()
                event_title = event.get('summary', 'Untitled Event')
            except:
                event_title = 'Event'

            # Delete the event
            service.events().delete(calendarId='primary', eventId=event_id).execute()

            return {
                'id': event_id,
                'title': event_title,
                'status': 'deleted',
                'message': f"Successfully deleted event: {event_title}"
            }

        except HttpError as e:
            logging.error(f"Google Calendar API error: {e}")
            return {
                'error': f"Failed to delete calendar event: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logging.error(f"Unexpected error deleting calendar event: {e}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }