"""
Enhanced Notes Agent with Google Docs integration
Intelligent note-taking with Google Docs operations using LLM
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timezone
from openai import AsyncAzureOpenAI

from google_docs_connector import GoogleDocsConnector


class EnhancedNotesAgent:
    def __init__(self):
        # Use Azure OpenAI like other agents
        from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        
        self.llm = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment_name = AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        self.system_message = "You are an enhanced Notes Agent that creates ALL notes and documents in Google Docs. Every note request - whether simple notes, detailed documents, reminders, or checklists - gets created as a Google Docs document with intelligent categorization and cross-referencing."
        self.model = self.deployment_name
        self.docs_connector = GoogleDocsConnector()

    async def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process notes requests with Google Docs integration"""
        user_message = state["user_request"]
        context = state.get("context", {})
        conversation_history = state.get("conversation_history", [])

        # Always use LLM to parse - no hardcoding, fully dynamic
        history_text = "\n".join(conversation_history) if conversation_history else "No previous conversation."
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_time = datetime.now(timezone.utc).strftime("%H:%M")
        
        extraction_prompt = f"""
        You are a notes assistant that creates ALL notes and documents in Google Docs. Every user request for notes - whether simple notes, detailed documents, reminders, checklists, or ideas - should be handled as a Google Docs document creation.
        
        IMPORTANT: All notes go to Google Docs. There are no other services available.
        
        Current date: {current_date}
        Current time: {current_time}
        User request: '{user_message}'
        Context from other agents: {context}
        Recent conversation: {history_text}

        CRITICAL INSTRUCTIONS:
        1. Service is ALWAYS "google_docs" - all notes and documents go to Google Docs
        2. Action types: "create", "update", "delete", "view_all", "view_specific", "search"
        3. For CREATE: Extract title and content. If no title provided, generate one based on content
        4. For UPDATE: Extract document identifier (title/query or ID) and new content to add/append
        5. For DELETE: Extract the document identifier (title/query or ID)
        6. For VIEW_SPECIFIC: Extract document identifier to view content
        7. For SEARCH: Extract search query to find documents
        8. Content can be notes, meeting summaries, ideas, plans, reminders, checklists, etc. - ALL go to Google Docs

        EXAMPLES:
        - "take notes about our meeting" → service: "google_docs", action: "create", title: "Meeting Notes", content: "meeting discussion content"
        - "write a detailed report about the project" → service: "google_docs", action: "create", title: "Project Report", content: "detailed project analysis"
        - "add to my project notes" → service: "google_docs", action: "update", document_query: "project notes", content: "additional content"
        - "show me my meeting notes" → service: "google_docs", action: "view_specific", document_query: "meeting notes"
        - "delete old notes" → service: "google_docs", action: "delete", document_query: "old notes"
        - "find my project documents" → service: "google_docs", action: "search", search_query: "project"

        Return ONLY valid JSON:
        {{
            "service": "google_docs",
            "action": "create|update|delete|view_all|view_specific|search",
            "document_details": {{
                "title": "extracted or generated document title",
                "content": "note content or content to add",
                "append_content": true/false
            }},
            "document_query": "for view_specific/update/delete: search term or document ID",
            "search_query": "for search action: search terms",
            "collaboration_needed": []
        }}
        """

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a notes management expert. Extract document operations from user requests precisely."},
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
            service = parsed_response.get("service", "google_docs")  # All notes go to Google Docs
            action = parsed_response.get("action", "create")

            import logging
            logging.info(f"📝 Notes Agent - Service: {service}, Action: {action}")

        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"❌ Failed to parse notes response as JSON: {str(e)}. Response: {response_text}",
                "collaboration_data": {}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Error in notes processing: {str(e)}",
                "collaboration_data": {}
            }

        # Now handle the action based on service
        if action == "create":
            document_details = parsed_response.get("document_details", {})
            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": f"❌ {service.replace('_', ' ').title()} access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            # Generate content using LLM if not provided
            content = document_details.get("content", "")
            if not content and user_message:
                service_name = "Google Docs"
                content_prompt = f"""
                Generate comprehensive notes from: '{user_message}'
                Context: {context}
                Conversation: {history_text}
                
                Create well-structured, detailed notes suitable for {service_name}.
                """

                content_response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional note-taker. Create detailed, well-organized notes."},
                        {"role": "user", "content": content_prompt}
                    ]
                )
                content = content_response.choices[0].message.content

            # Use appropriate connector based on service
            if service == "google_docs":
                result = await self.docs_connector.create_document(
                    access_token=access_token,
                    title=document_details.get("title", "New Notes"),
                    content=content
                )
                service_name = "Google Docs"

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to create document: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            collaboration_needed = parsed_response.get("collaboration_needed", [])
            
            # Create a detailed message with the actual content
            content_preview = content[:500] if len(content) > 500 else content
            message_parts = [
                f"📝 **Document Created in {service_name}**",
                f"**Title:** {result['title']}",
                f"**URL:** {result.get('url', 'N/A')}",
                f"\n**Content:**",
                content_preview
            ]
            
            if len(content) > 500:
                message_parts.append("\n... (content truncated)")
            
            return {
                "status": "success",
                "result": {
                    **result,
                    "content": content,  # Include full content in result
                    "content_preview": content_preview
                },
                "message": "\n".join(message_parts),
                "collaboration_data": {
                    "document_url": result.get("url", ""),
                    "document_id": result.get("id", ""),
                    "document_title": result.get("title", ""),
                    "content": content,
                    "next_agents": collaboration_needed
                }
            }

        elif action == "view_specific":
            document_query = parsed_response.get("document_query", "")
            if not document_query:
                return {
                    "status": "error",
                    "message": "❌ No document query provided for specific lookup.",
                    "collaboration_data": {}
                }

            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": f"❌ {service.replace('_', ' ').title()} access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            # Search for document based on service
            if service == "google_docs":
                result = await self.docs_connector.search_documents(
                    access_token=access_token,
                    query=document_query
                )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to search documents: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            documents = result.get('documents', [])
            if not documents:
                return {
                    "status": "error",
                    "message": f"❌ No documents found matching '{document_query}'",
                    "collaboration_data": {}
                }

            # Get the first matching document
            doc = documents[0]
            doc_id = doc.get('id')
            
            # Get full content based on service
            if service == "google_docs":
                content_result = await self.docs_connector.get_document_content(
                    access_token=access_token,
                    document_id=doc_id
                )

            if content_result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to get document content: {content_result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            return {
                "status": "success",
                "result": {
                    "document": doc,
                    "content": content_result.get('content', '')
                },
                "message": f"📖 Found document '{doc.get('title', 'Untitled')}' in {service.replace('_', ' ').title()}",
                "collaboration_data": {
                    "document_url": doc.get("url", ""),
                    "document_id": doc_id
                }
            }

        elif action == "view_all":
            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": f"❌ {service.replace('_', ' ').title()} access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            # List all documents based on service
            if service == "google_docs":
                result = await self.docs_connector.list_documents(access_token=access_token)

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to list documents: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            documents = result.get('documents', [])

            return {
                "status": "success",
                "result": {"documents": documents},
                "message": f"📚 Found {len(documents)} documents in {service.replace('_', ' ').title()}",
                "collaboration_data": {}
            }

        elif action == "search":
            search_query = parsed_response.get("search_query", "")
            if not search_query:
                return {
                    "status": "error",
                    "message": "❌ No search query provided.",
                    "collaboration_data": {}
                }

            access_token = state.get("access_token")
            if not access_token:
                return {
                    "status": "error",
                    "message": f"❌ {service.replace('_', ' ').title()} access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }

            # Use appropriate connector based on service
            if service == "google_docs":
                result = await self.docs_connector.search_documents(access_token=access_token, query=search_query)
                item_type = "document"

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to search documents: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            documents = result.get('documents', [])
            return {
                "status": "success",
                "result": {"documents": documents},
                "message": f"🔍 Found {len(documents)} {item_type}(s) matching '{search_query}'",
                "collaboration_data": {}
            }

        elif action == "update":
            document_query = parsed_response.get("document_query", "")
            access_token = state.get("access_token")
            
            if not access_token:
                return {
                    "status": "error",
                    "message": f"❌ {service.replace('_', ' ').title()} access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }
            
            if not document_query:
                return {
                    "status": "error",
                    "message": "❌ No document identifier provided for update. Please specify which document to update.",
                    "collaboration_data": {}
                }

            # STEP 1: Find the document
            import logging
            logging.info(f"🔍 Searching for documents to update with query: '{document_query}'")
            
            search_result = await self.docs_connector.search_documents(
                access_token=access_token,
                query=document_query,
                max_results=10
            )

            if search_result.get('status') == 'error' or not search_result.get('documents'):
                return {
                    "status": "error",
                    "message": f"❌ No documents found matching '{document_query}'. Please check the document name.",
                    "collaboration_data": {}
                }

            # STEP 2: Let LLM match user intent with actual documents
            documents_list = search_result['documents']
            documents_summary = "\n".join([
                f"- ID: {doc['id']}, Title: '{doc['title']}', Modified: {doc['modified_time']}"
                for doc in documents_list[:10]
            ])

            matching_prompt = f"""
            User wants to update a document. Here are the ACTUAL documents from their Google Drive:
            
            {documents_summary}
            
            User's request: "{user_message}"
            User's query: "{document_query}"
            
            Your task: Find the BEST matching document from the list above.
            
            Return ONLY valid JSON:
            {{
                "matched_document_id": "document ID from list above",
                "confidence": 0.0-1.0,
                "reason": "why this document matches"
            }}
            
            If NO good match exists, return: {{"matched_document_id": null, "confidence": 0.0, "reason": "no match found"}}
            """

            match_response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a document matching expert. Match user requests to actual Google Docs."},
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
                document_id = match_result.get("matched_document_id")
                confidence = match_result.get("confidence", 0.0)
                
                logging.info(f"📊 Document matching - ID: {document_id}, Confidence: {confidence}")

                if not document_id or confidence < 0.5:
                    return {
                        "status": "error",
                        "message": f"❌ Could not find a matching document for '{document_query}'. Reason: {match_result.get('reason', 'Low confidence match')}. Please check the document name and try again.",
                        "collaboration_data": {}
                    }

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse matching result: {e}")
                return {
                    "status": "error",
                    "message": "❌ Failed to match document. Please try with more specific document details.",
                    "collaboration_data": {}
                }

            # STEP 3: Get update details and update the document
            document_details = parsed_response.get("document_details", {})
            content = document_details.get("content", "")
            append_content = document_details.get("append_content", True)
            
            # Generate content using LLM if not provided
            if not content and user_message:
                content_prompt = f"""
                Generate content to add to document from: '{user_message}'
                Context: {context}
                Conversation: {history_text}
                
                Create well-structured content to append to the existing document.
                """
                
                content_response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional note-taker. Create content to add to existing documents."},
                        {"role": "user", "content": content_prompt}
                    ]
                )
                content = content_response.choices[0].message.content

            result = await self.docs_connector.update_document(
                access_token=access_token,
                document_id=document_id,
                title=document_details.get("title"),
                content=content,
                append_content=append_content
            )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to update document: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            return {
                "status": "success",
                "result": result,
                "message": f"✅ Successfully updated document '{result['title']}'",
                "collaboration_data": {}
            }

        elif action == "delete":
            document_query = parsed_response.get("document_query", "")
            access_token = state.get("access_token")
            
            if not access_token:
                return {
                    "status": "error",
                    "message": "❌ Google Docs access requires authentication. Please sign in with Google.",
                    "collaboration_data": {}
                }
            
            if not document_query:
                return {
                    "status": "error",
                    "message": "❌ No document identifier provided for deletion. Please specify which document to delete.",
                    "collaboration_data": {}
                }

            # STEP 1: Find the document
            import logging
            logging.info(f"🔍 Searching for documents to delete with query: '{document_query}'")
            
            search_result = await self.docs_connector.search_documents(
                access_token=access_token,
                query=document_query,
                max_results=10
            )

            if search_result.get('status') == 'error' or not search_result.get('documents'):
                return {
                    "status": "error",
                    "message": f"❌ No documents found matching '{document_query}'. Please check the document name.",
                    "collaboration_data": {}
                }

            # STEP 2: Let LLM match user intent with actual documents
            documents_list = search_result['documents']
            documents_summary = "\n".join([
                f"- ID: {doc['id']}, Title: '{doc['title']}', Modified: {doc['modified_time']}"
                for doc in documents_list[:10]
            ])

            matching_prompt = f"""
            User wants to delete a document. Here are the ACTUAL documents from their Google Drive:
            
            {documents_summary}
            
            User's request: "{user_message}"
            User's query: "{document_query}"
            
            Your task: Find the BEST matching document from the list above.
            
            Return ONLY valid JSON:
            {{
                "matched_document_id": "document ID from list above",
                "confidence": 0.0-1.0,
                "reason": "why this document matches"
            }}
            
            If NO good match exists, return: {{"matched_document_id": null, "confidence": 0.0, "reason": "no match found"}}
            """

            match_response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a document matching expert. Match user requests to actual Google Docs."},
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
                document_id = match_result.get("matched_document_id")
                confidence = match_result.get("confidence", 0.0)
                
                logging.info(f"📊 Document matching - ID: {document_id}, Confidence: {confidence}")

                if not document_id or confidence < 0.5:
                    return {
                        "status": "error",
                        "message": f"❌ Could not find a matching document for '{document_query}'. Reason: {match_result.get('reason', 'Low confidence match')}. Please check the document name and try again.",
                        "collaboration_data": {}
                    }

                # Find the matched document details for confirmation
                matched_doc = next((d for d in documents_list if d['id'] == document_id), None)
                doc_title = matched_doc['title'] if matched_doc else 'Document'

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse matching result: {e}")
                return {
                    "status": "error",
                    "message": "❌ Failed to match document. Please try with more specific document details.",
                    "collaboration_data": {}
                }

            # STEP 3: Delete the document
            result = await self.docs_connector.delete_document(
                access_token=access_token,
                document_id=document_id
            )

            if result.get('status') == 'error':
                return {
                    "status": "error",
                    "message": f"❌ Failed to delete document: {result.get('error', 'Unknown error')}",
                    "collaboration_data": {}
                }

            return {
                "status": "success",
                "result": result,
                "message": f"🗑️ Successfully deleted document '{doc_title}'",
                "collaboration_data": {}
            }

        else:
            return {
                "status": "error",
                "message": f"❌ Unknown notes action: {action}",
                "collaboration_data": {}
            }
