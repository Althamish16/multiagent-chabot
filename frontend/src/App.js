import React, { useState, useRef, useEffect } from "react";
import "@/App.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import axios from "axios";
import { 
  Send, 
  Mail, 
  Calendar, 
  FileText, 
  StickyNote, 
  Bot, 
  User, 
  Upload,
  Sparkles,
  Brain
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [processingStep, setProcessingStep] = useState("");
  const [sessionId] = useState(`session-${Date.now()}`);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load chat history on mount
    loadChatHistory();
    // Add welcome message
    setMessages([{
      id: "welcome",
      message: "🤖 Hello! I'm your AI Agents assistant. I can help you with:\n\n📧 **Email** - Send emails to anyone\n📅 **Calendar** - Manage your schedule and events\n📄 **File Summarization** - Analyze and summarize documents\n📝 **Notes** - Take and organize your notes\n\n💡 **Pro Tips:**\n• Use natural language - I'll understand and route to the right agent\n• Upload files for instant AI analysis\n• Try the quick actions on the left\n• Press Ctrl+/ for keyboard shortcuts\n\nWhat would you like to do today?",
      sender: "agent",
      agent_type: "general",
      timestamp: new Date().toISOString()
    }]);

    // Add keyboard shortcuts
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        alert('🚀 Keyboard Shortcuts:\n\n• Enter: Send message\n• Ctrl+U: Upload file\n• Ctrl+E: Quick email\n• Ctrl+C: Check calendar\n• Ctrl+N: Take note');
      }
      if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/chat/${sessionId}`);
      setMessages(response.data || []);
    } catch (error) {
      console.error("Error loading chat history:", error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      message: inputMessage,
      sender: "user",
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    const originalMessage = inputMessage;
    setInputMessage("");
    setIsLoading(true);
    
    // Show processing steps
    setProcessingStep("🔍 Analyzing your request...");
    await new Promise(resolve => setTimeout(resolve, 800));
    
    setProcessingStep("🤖 Routing to appropriate agent...");
    await new Promise(resolve => setTimeout(resolve, 600));

    try {
      const response = await axios.post(`${API}/chat`, {
        message: originalMessage,
        session_id: sessionId
      });

      const agentUsed = response.data.agent_used;
      setCurrentAgent(agentUsed);
      
      // Show agent-specific processing
      const agentNames = {
        'email_agent': '📧 Email Agent',
        'calendar_agent': '📅 Calendar Agent', 
        'file_summarizer_agent': '📄 File Summarizer Agent',
        'notes_agent': '📝 Notes Agent',
        'general': '🤖 AI Assistant'
      };
      
      setProcessingStep(`${agentNames[agentUsed] || '🤖 AI Agent'} is processing...`);
      await new Promise(resolve => setTimeout(resolve, 1000));

      const agentMessage = {
        id: Date.now() + 1,
        message: response.data.response,
        sender: "agent",
        agent_type: response.data.agent_used,
        timestamp: response.data.timestamp
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage = {
        id: Date.now() + 1,
        message: "Sorry, I encountered an error. Please try again.",
        sender: "agent",
        agent_type: "error",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setCurrentAgent(null);
      setProcessingStep("");
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsLoading(true);
    setCurrentAgent("file_summarizer_agent");
    
    const uploadMessage = {
      id: Date.now().toString(),
      message: `📎 Uploading file: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
      sender: "user",
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, uploadMessage]);

    // Show upload progress steps
    setProcessingStep("📤 Uploading file...");
    await new Promise(resolve => setTimeout(resolve, 800));
    
    setProcessingStep("🔍 Analyzing file content...");
    await new Promise(resolve => setTimeout(resolve, 600));
    
    setProcessingStep("📄 File Summarizer Agent is processing...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("session_id", sessionId);

      const response = await axios.post(`${API}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      const summaryMessage = {
        id: Date.now() + 1,
        message: response.data.summary,
        sender: "agent",
        agent_type: "file_summarizer_agent",
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, summaryMessage]);
    } catch (error) {
      console.error("Error uploading file:", error);
      const errorMessage = {
        id: Date.now() + 1,
        message: "Sorry, I couldn't process the file. Please try again.",
        sender: "agent",
        agent_type: "error",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setCurrentAgent(null);
      setProcessingStep("");
      event.target.value = "";
    }
  };

  const getAgentIcon = (agentType) => {
    switch (agentType) {
      case "email_agent": return <Mail className="w-4 h-4" />;
      case "calendar_agent": return <Calendar className="w-4 h-4" />;
      case "file_summarizer_agent": return <FileText className="w-4 h-4" />;
      case "notes_agent": return <StickyNote className="w-4 h-4" />;
      default: return <Brain className="w-4 h-4" />;
    }
  };

  const getAgentColor = (agentType) => {
    switch (agentType) {
      case "email_agent": return "bg-blue-500";
      case "calendar_agent": return "bg-green-500";
      case "file_summarizer_agent": return "bg-purple-500";
      case "notes_agent": return "bg-orange-500";
      default: return "bg-gray-500";
    }
  };

  const getAgentName = (agentType) => {
    switch (agentType) {
      case "email_agent": return "📧 Email Agent";
      case "calendar_agent": return "📅 Calendar Agent";
      case "file_summarizer_agent": return "📄 File Summarizer Agent";
      case "notes_agent": return "📝 Notes Agent";
      default: return "🤖 AI Assistant";
    }
  };

  const quickActions = [
    { text: "Send an email to john@example.com about meeting", icon: <Mail className="w-4 h-4" /> },
    { text: "What's on my calendar today?", icon: <Calendar className="w-4 h-4" /> },
    { text: "Take a note: Remember to follow up on project proposal", icon: <StickyNote className="w-4 h-4" /> },
    { text: "Help me schedule a team meeting for tomorrow", icon: <Calendar className="w-4 h-4" /> }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  AI Agents
                </h1>
                <p className="text-sm text-slate-600">The Future of Automation</p>
              </div>
            </div>
            <div className="flex space-x-2">
              <Badge variant="outline" className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>4 Agents Active</span>
              </Badge>
              {isLoading && currentAgent && (
                <Badge className={`${getAgentColor(currentAgent)} text-white animate-pulse`}>
                  <div className="flex items-center space-x-1">
                    {getAgentIcon(currentAgent)}
                    <span>{getAgentName(currentAgent).replace('🤖 ', '').replace('📧 ', '').replace('📅 ', '').replace('📄 ', '').replace('📝 ', '')} Working</span>
                  </div>
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Agents Panel */}
          <div className="lg:col-span-1">
            <Card className="h-fit border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Bot className="w-5 h-5 text-blue-600" />
                  <span>Available Agents</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center space-x-3 p-3 rounded-xl bg-blue-50 border border-blue-200">
                  <div className="p-2 bg-blue-500 rounded-lg">
                    <Mail className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-blue-900">Email Agent</p>
                    <p className="text-xs text-blue-600">Send & manage emails</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 p-3 rounded-xl bg-green-50 border border-green-200">
                  <div className="p-2 bg-green-500 rounded-lg">
                    <Calendar className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-green-900">Calendar Agent</p>
                    <p className="text-xs text-green-600">Manage schedules</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 p-3 rounded-xl bg-purple-50 border border-purple-200">
                  <div className="p-2 bg-purple-500 rounded-lg">
                    <FileText className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-purple-900">File Summarizer</p>
                    <p className="text-xs text-purple-600">Analyze documents</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 p-3 rounded-xl bg-orange-50 border border-orange-200">
                  <div className="p-2 bg-orange-500 rounded-lg">
                    <StickyNote className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-orange-900">Notes Agent</p>
                    <p className="text-xs text-orange-600">Take & organize notes</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="mt-6 border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {quickActions.map((action, index) => (
                  <Button
                    key={index}
                    variant="ghost"
                    className="w-full text-left justify-start h-auto p-3 text-sm"
                    onClick={() => setInputMessage(action.text)}
                  >
                    <div className="flex items-start space-x-2">
                      {action.icon}
                      <span className="text-wrap">{action.text}</span>
                    </div>
                  </Button>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3">
            <Card className="h-[700px] flex flex-col border-0 shadow-xl bg-white/80 backdrop-blur-sm">
              <CardHeader className="flex-shrink-0 border-b bg-gradient-to-r from-slate-50 to-blue-50">
                <CardTitle className="text-xl flex items-center space-x-2">
                  <Bot className="w-6 h-6 text-blue-600" />
                  <span>AI Assistant</span>
                </CardTitle>
              </CardHeader>

              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                          msg.sender === "user"
                            ? "bg-blue-600 text-white"
                            : "bg-slate-100 text-slate-900"
                        }`}
                      >
                        {msg.sender === "agent" && msg.agent_type && (
                          <div className="flex items-center space-x-2 mb-2 opacity-75">
                            <div className={`p-1 rounded-md ${getAgentColor(msg.agent_type)}`}>
                              {getAgentIcon(msg.agent_type)}
                            </div>
                            <span className="text-xs font-medium capitalize">
                              {msg.agent_type.replace('_agent', '').replace('_', ' ')} Agent
                            </span>
                          </div>
                        )}
                        <div className="whitespace-pre-wrap text-sm leading-relaxed">
                          {msg.message}
                        </div>
                        <div className={`text-xs mt-2 opacity-60`}>
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl px-4 py-3 max-w-[80%]">
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                            {currentAgent && (
                              <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full animate-pulse ${getAgentColor(currentAgent)}`}></div>
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="text-sm font-medium text-blue-900">
                              {processingStep || "AI Agent is thinking..."}
                            </div>
                            {currentAgent && (
                              <div className="text-xs text-blue-600 mt-1">
                                {getAgentName(currentAgent)} is working on your request
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex mt-2 space-x-1">
                          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* Input Area */}
              <div className="flex-shrink-0 border-t bg-slate-50 p-4">
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                    className="flex-shrink-0 hover:bg-blue-50 hover:border-blue-300 transition-colors"
                    title="Upload file (Ctrl+U)"
                  >
                    <Upload className="w-4 h-4" />
                  </Button>
                  <Input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileUpload}
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg"
                  />
                  
                  <Input
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                    placeholder="Ask your AI agents to help with emails, calendar, files, or notes..."
                    className="flex-1 border-0 bg-white shadow-sm focus:ring-2 focus:ring-blue-500 transition-all"
                    disabled={isLoading}
                  />
                  
                  <Button
                    onClick={sendMessage}
                    disabled={!inputMessage.trim() || isLoading}
                    className="flex-shrink-0 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex justify-between items-center mt-2">
                  <p className="text-xs text-slate-500">
                    Upload documents • Press Enter to send • Ctrl+/ for shortcuts
                  </p>
                  {isLoading && (
                    <div className="text-xs text-blue-600 font-medium">
                      {processingStep}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;