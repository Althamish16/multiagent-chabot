"""
Enhanced Calendar Agent with coordination capabilities
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from openai import AsyncAzureOpenAI

from google_calendar_connector import GoogleCalendarConnector


class EnhancedCalendarAgent:
    def __init__(self):
        # Use Azure OpenAI like other agents
        from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        self.system_message = "You are an enhanced Calendar Agent with coordination capabilities. Schedule meetings, manage attendees, and collaborate with notes agents."
        self.model = self.deployment_name
        self.calendar_connector = GoogleCalendarConnector()

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process calendar requests with enhanced collaboration"""
        user_message = state["user_request"]
        context = state.get("context", {})
        conversation_history = state.get("conversation_history", [])

        # Always use LLM to parse - no hardcoding, fully dynamic
        history_text = "\n".join(conversation_history) if conversation_history else "No previous conversation."
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_time = datetime.now(timezone.utc).strftime("%H:%M")
        
        extraction_prompt = f"""
        You are a calendar assistant. Extract meeting/event details from the user's request.
        
        Current date: {current_date}
        Current time: {current_time}
        User request: '{user_message}'
        Context from other agents: {context}
        Recent conversation: {history_text}

        CRITICAL INSTRUCTIONS:
        1. If user mentions BOTH a reminder time AND a meeting time, the MEETING TIME is the actual event time.
           Example: "reminder at 10:30 for meeting at 11" → Event starts at 11:00, NOT 10:30
        2. Extract the actual event title from user's words (e.g., "standup meeting", "client call", "doctor appointment")
        3. TIMEZONE HANDLING:
           - If user specifies timezone (IST, PST, EST, etc.), include it as offset in ISO format
           - IST (Indian Standard Time) = UTC+05:30 → use format: YYYY-MM-DDTHH:MM:SS+05:30
           - PST (Pacific) = UTC-08:00 → use format: YYYY-MM-DDTHH:MM:SS-08:00
           - If NO timezone mentioned, use format without offset: YYYY-MM-DDTHH:MM:SS (Google will use user's default)
        4. If only date mentioned, assume reasonable business hours (9 AM - 6 PM)
        5. Default duration is 30 minutes if not specified
        6. For attendees, extract email addresses if mentioned
        7. Action types: "create", "update", "delete", "view_all", "view_specific", "find_free_slots"
        8. For UPDATE: Extract what to change and identify the event (by title/query or ID)
        9. For DELETE: Extract the event identifier (title/query or ID)

        EXAMPLES:
        - "meeting at 11 AM IST on Oct 28" → "2025-10-28T11:00:00+05:30"
        - "call at 3 PM tomorrow" → "2025-10-25T15:00:00" (no timezone)
        - "appointment at 2 PM PST" → "2025-10-24T14:00:00-08:00"
        - "update standup meeting to 12 PM" → action: "update", event_query: "standup meeting"
        - "delete client call" → action: "delete", event_query: "client call"

        Return ONLY valid JSON:
        {{
            "action": "create|update|delete|view_all|view_specific|find_free_slots",
            "event_details": {{
                "title": "extracted event name from user request",
                "start_date": "YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SS+HH:MM",
                "end_date": "YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SS+HH:MM",
                "description": "any additional context or notes",
                "recurrence": []
            }},
            "attendees": ["email@example.com"],
            "event_query": "for view_specific: search term or event ID",
            "time_range": {{"start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS", "duration_minutes": 60}},
            "collaboration_needed": []
        }}
        """

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a calendar scheduling expert. Extract event details precisely from user requests. Distinguish reminder times from actual event times."},
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0.1
        )
        response_text = response.choices[0].message.content

        try:
            # Clean up response if it has markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            parsed_response = json.loads(response_text)
            action = parsed_response.get("action", "view_all")

            if action == "create":
                event_details = parsed_response.get("event_details", {})
                attendees = parsed_response.get("attendees", [])
                recurrence = event_details.get("recurrence", [])
                
                # Log the parsed dates for debugging
                import logging
                logging.info(f"📅 Calendar Agent - Parsed event details:")
                logging.info(f"   Title: {event_details.get('title')}")
                logging.info(f"   Start: {event_details.get('start_date')}")
                logging.info(f"   End: {event_details.get('end_date')}")
                logging.info(f"   Description: {event_details.get('description')}")

        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"❌ Failed to parse calendar response as JSON: {str(e)}. Response: {response_text}",
                "collaboration_data": {}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error in calendar processing: {str(e)}",
                "collaboration_data": {}
            }

        # Now handle the action (shared code)
        if action == "create_event" or action == "create":
            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Calendar access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            result = await self.calendar_connector.create_event(
                access_token=access_token,
                title=event_details.get("title", "New Meeting"),
                start_date=event_details.get("start_date", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()),
                end_date=event_details.get("end_date", (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()),
                description=event_details.get("description", ""),
                attendees=attendees,
                recurrence=recurrence if recurrence else None
            )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to create calendar event: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            recurrence_msg = " (recurring)" if recurrence else ""
            collaboration_needed = parsed_response.get("collaboration_needed", [])
            
            return {
                "status": "success",
                "result": result,
                "message": f"📅 Event '{result['title']}' created successfully{' with ' + str(len(attendees)) + ' attendees' if attendees else ''}{recurrence_msg}",
                "collaboration_data": {
                    "meeting_link": result.get("meeting_link", ""),
                    "event_id": result.get("id", ""),
                    "next_agents": collaboration_needed
                }
            }
        elif action == "view_specific":
            event_query = parsed_response.get("event_query", "")
            if not event_query:
                return {
                    "status": "error",
                    "message": "❌ No event query provided for specific lookup.",
                    "collaboration_data": {}
                }

            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Calendar access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            # Try to get by ID first, then search
            result = await self.calendar_connector.get_event(access_token=access_token, event_id=event_query)
            if result.get('status') == 'error':
                # If not an ID, search
                result = await self.calendar_connector.search_events(access_token=access_token, query=event_query, max_results=5)

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to find specific event: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            if 'event_status' in result:  # Single event
                return {
                    "status": "success",
                    "result": result,
                    "message": f"📅 Found event: {result['title']}",
                    "collaboration_data": {}
                }
            else:  # Search results
                events = result.get('events', [])
                return {
                    "status": "success",
                    "result": {"events": events},
                    "message": f"📅 Found {len(events)} event(s) matching '{event_query}'",
                    "collaboration_data": {}
                }
        elif action == "view_all":
            # View calendar functionality
            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Calendar access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            result = await self.calendar_connector.list_events(access_token=access_token)

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to fetch calendar events: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            events = result.get('events', [])
            return {
                "status": "success",
                "result": {"events": events},
                "message": f"📅 Found {len(events)} upcoming calendar event(s)",
                "collaboration_data": {}
            }
        elif action == "find_free_slots":
            time_range = parsed_response.get("time_range", {})
            attendees = parsed_response.get("attendees", [])
            duration = time_range.get("duration_minutes", 60)

            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Calendar access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            # Default time range if not provided
            time_min = time_range.get("start", datetime.now(timezone.utc).isoformat())
            time_max = time_range.get("end", (datetime.now(timezone.utc) + timedelta(days=7)).isoformat())

            result = await self.calendar_connector.find_free_slots(
                access_token=access_token,
                time_min=time_min,
                time_max=time_max,
                duration_minutes=duration,
                attendees=attendees
            )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to find free slots: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            free_slots = result.get('free_slots', [])
            return {
                "status": "success",
                "result": {"free_slots": free_slots},
                "message": f"📅 Found {len(free_slots)} free {duration}-minute slot(s) in the next week",
                "collaboration_data": {}
            }
        elif action == "update":
            event_query = parsed_response.get("event_query", "")
            access_token = state.get("access_token")
            
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Calendar access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }
            
            if not event_query:
                return {
                    "status": "error",
                    "message": "❌ No event identifier provided for update. Please specify which event to update.",
                    "collaboration_data": {}
                }

            # STEP 1: Retrieve actual calendar events (next 30 days)
            import logging
            logging.info(f"🔍 Searching for events to update with query: '{event_query}'")
            
            list_result = await self.calendar_connector.list_events(
                access_token=access_token,
                max_results=50,
                time_min=datetime.now(timezone.utc).isoformat()
            )

            if list_result.get('status') == 'error' or not list_result.get('events'):
                return {
                    "status": "error",
                    "message": f"❌ No upcoming events found in calendar. Please check your calendar.",
                    "collaboration_data": {}
                }

            # STEP 2: Let LLM match user intent with actual events (no hallucination!)
            events_list = list_result['events']
            events_summary = "\n".join([
                f"- ID: {evt['id']}, Title: '{evt['title']}', Start: {evt['start']}, End: {evt['end']}"
                for evt in events_list[:20]  # Limit to 20 for token efficiency
            ])

            matching_prompt = f"""
            User wants to update an event. Here are the ACTUAL events from their calendar:
            
            {events_summary}
            
            User's request: "{user_message}"
            User's query: "{event_query}"
            
            Your task: Find the BEST matching event from the list above.
            
            Return ONLY valid JSON:
            {{
                "matched_event_id": "event ID from list above",
                "confidence": 0.0-1.0,
                "reason": "why this event matches"
            }}
            
            If NO good match exists, return: {{"matched_event_id": null, "confidence": 0.0, "reason": "no match found"}}
            """

            match_response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an event matching expert. Match user requests to actual calendar events. Be precise."},
                    {"role": "user", "content": matching_prompt}
                ],
                temperature=0.1
            )
            match_text = match_response.choices[0].message.content

            # Clean response
            if "```json" in match_text:
                match_text = match_text.split("```json")[1].split("```")[0].strip()
            elif "```" in match_text:
                match_text = match_text.split("```")[1].split("```")[0].strip()

            try:
                match_result = json.loads(match_text)
                event_id = match_result.get("matched_event_id")
                confidence = match_result.get("confidence", 0.0)
                
                logging.info(f"📊 Event matching - ID: {event_id}, Confidence: {confidence}")

                if not event_id or confidence < 0.5:
                    return {
                        "status": "error",
                        "message": f"❌ Could not find a matching event for '{event_query}'. Reason: {match_result.get('reason', 'Low confidence match')}. Please check the event name and try again.",
                        "collaboration_data": {}
                    }

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse matching result: {e}")
                return {
                    "status": "error",
                    "message": "❌ Failed to match event. Please try with more specific event details.",
                    "collaboration_data": {}
                }

            # STEP 3: Get update details from parsed response
            event_details = parsed_response.get("event_details", {})
            
            # STEP 4: Update the event with matched ID
            result = await self.calendar_connector.update_event(
                access_token=access_token,
                event_id=event_id,
                title=event_details.get("title"),
                start_date=event_details.get("start_date"),
                end_date=event_details.get("end_date"),
                description=event_details.get("description"),
                attendees=parsed_response.get("attendees"),
                location=event_details.get("location"),
                recurrence=event_details.get("recurrence")
            )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to update event: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            return {
                "status": "success",
                "result": result,
                "message": f"✅ Successfully updated event '{result['title']}'",
                "collaboration_data": {}
            }
        elif action == "delete":
            event_query = parsed_response.get("event_query", "")
            access_token = state.get("access_token")
            
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Calendar access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }
            
            if not event_query:
                return {
                    "status": "error",
                    "message": "❌ No event identifier provided for deletion. Please specify which event to delete.",
                    "collaboration_data": {}
                }

            # STEP 1: Retrieve actual calendar events (next 30 days)
            import logging
            logging.info(f"🔍 Searching for events to delete with query: '{event_query}'")
            
            list_result = await self.calendar_connector.list_events(
                access_token=access_token,
                max_results=50,
                time_min=datetime.now(timezone.utc).isoformat()
            )

            if list_result.get('status') == 'error' or not list_result.get('events'):
                return {
                    "status": "error",
                    "message": f"❌ No upcoming events found in calendar. Please check your calendar.",
                    "collaboration_data": {}
                }

            # STEP 2: Let LLM match user intent with actual events (no hallucination!)
            events_list = list_result['events']
            events_summary = "\n".join([
                f"- ID: {evt['id']}, Title: '{evt['title']}', Start: {evt['start']}, End: {evt['end']}"
                for evt in events_list[:20]  # Limit to 20 for token efficiency
            ])

            matching_prompt = f"""
            User wants to delete an event. Here are the ACTUAL events from their calendar:
            
            {events_summary}
            
            User's request: "{user_message}"
            User's query: "{event_query}"
            
            Your task: Find the BEST matching event from the list above.
            
            Return ONLY valid JSON:
            {{
                "matched_event_id": "event ID from list above",
                "confidence": 0.0-1.0,
                "reason": "why this event matches"
            }}
            
            If NO good match exists, return: {{"matched_event_id": null, "confidence": 0.0, "reason": "no match found"}}
            """

            match_response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an event matching expert. Match user requests to actual calendar events. Be precise."},
                    {"role": "user", "content": matching_prompt}
                ],
                temperature=0.1
            )
            match_text = match_response.choices[0].message.content

            # Clean response
            if "```json" in match_text:
                match_text = match_text.split("```json")[1].split("```")[0].strip()
            elif "```" in match_text:
                match_text = match_text.split("```")[1].split("```")[0].strip()

            try:
                match_result = json.loads(match_text)
                event_id = match_result.get("matched_event_id")
                confidence = match_result.get("confidence", 0.0)
                
                logging.info(f"📊 Event matching - ID: {event_id}, Confidence: {confidence}")

                if not event_id or confidence < 0.5:
                    return {
                        "status": "error",
                        "message": f"❌ Could not find a matching event for '{event_query}'. Reason: {match_result.get('reason', 'Low confidence match')}. Please check the event name and try again.",
                        "collaboration_data": {}
                    }

                # Find the matched event details for confirmation
                matched_event = next((e for e in events_list if e['id'] == event_id), None)
                event_title = matched_event['title'] if matched_event else 'Event'

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse matching result: {e}")
                return {
                    "status": "error",
                    "message": "❌ Failed to match event. Please try with more specific event details.",
                    "collaboration_data": {}
                }

            # STEP 3: Delete the event with matched ID
            result = await self.calendar_connector.delete_event(
                access_token=access_token,
                event_id=event_id
            )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to delete event: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            return {
                "status": "success",
                "result": result,
                "message": f"🗑️ Successfully deleted event '{event_title}'",
                "collaboration_data": {}
            }
        else:
            return {
                "status": "error",
                "message": f"❌ Unknown calendar action: {action}",
                "collaboration_data": {}
            }