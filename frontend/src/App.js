import React, { useState, useRef, useEffect } from "react";
import "@/App.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { AuthProvider, useAuth } from "@/components/AuthProvider_new";
import { LoginButton } from "@/components/LoginButton_new";
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
  Brain,
  Workflow,
  Users,
  Zap,
  Shield,
  Crown
} from "lucide-react";

const BACKEND_URL = 'http://localhost:5000';
const API = `${BACKEND_URL}/api`;

function ChatInterface() {
  const { user, isAuthenticated, loading } = useAuth();
  
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [processingStep, setProcessingStep] = useState("");
  const [sessionId] = useState(`session-${Date.now()}`);
  const [workflowType, setWorkflowType] = useState(null);
  const [agentsInvolved, setAgentsInvolved] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState(null);
  const [useStreaming, setUseStreaming] = useState(false); // Streaming disabled - using normal messages
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChatHistory = async () => {
    // Only load chat history if authenticated
    if (!isAuthenticated) {
      return;
    }
    
    try {
      const token = localStorage.getItem('auth_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const response = await axios.get(`${API}/chat/${sessionId}`, { headers });
      if (response.data && response.data.length > 0) {
        setMessages(response.data);
      }
    } catch (error) {
      // Don't show error to user if it's just a 401/403 (not authenticated)
      if (error.response?.status !== 401 && error.response?.status !== 403) {
        console.error("Failed to load chat history:", error);
      }
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load chat history when authenticated
    if (isAuthenticated) {
      loadChatHistory();
    }
    // Add enhanced welcome message
    const welcomeMessage = isAuthenticated 
      ? `🚀 Welcome back, ${user?.name}! Your Enhanced AI Agents are ready with advanced collaboration capabilities!

🔗 **Multi-Agent Collaboration Features:**

📧 **Smart Email Agent** - Send emails with meeting invites and smart routing
📅 **Intelligent Calendar Agent** - Advanced scheduling with attendee management
📝 **Enhanced Notes Agent** - AI categorization with cross-referencing
📄 **Advanced File Analyzer** - Deep insights with workflow recommendations

🎯 **Enhanced Features:**
• **Conversation Memory** - Remembers context across messages
• **Smart Agent Routing** - Automatically selects the best agent for your task
• **Collaborative Workflows** - Multiple agents work together seamlessly
• **Real-time Streaming** - See responses as they're generated

💡 **Try asking:**
• "Schedule a meeting with john@example.com about the project"
• "Send an email to the team about the new requirements"
• "Take notes about our discussion and categorize them"
• "Analyze this document and create a summary"

Ready to assist! 🤖`
      : `Welcome to the Enhanced AI Agents POC! Please sign in to access all features.`;

    if (messages.length === 0) {
      setMessages([{
        id: "welcome",
        message: welcomeMessage,
        sender: "agent",
        timestamp: new Date().toISOString(),
        agent_type: "system"
      }]);
    }
  }, [isAuthenticated, user, messages.length]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="w-96 text-center">
          <CardContent className="p-8">
            <div className="space-y-4">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                <Shield className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-2xl font-semibold">Authentication Required</h2>
              <p className="text-gray-600">
                Please sign in with your Microsoft Azure AD account to access the enhanced AI agents.
              </p>
              <LoginButton />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const sendStreamingMessage = async () => {
    // Streaming disabled - using normal message sending instead
    return sendMessage();
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
    
    // Enhanced processing steps for authenticated users
    if (isAuthenticated) {
      setProcessingStep("🔍 Analyzing your request with enhanced AI...");
      await new Promise(resolve => setTimeout(resolve, 800));
      
      setProcessingStep("🤖 LangGraph orchestrating multi-agent collaboration...");
      await new Promise(resolve => setTimeout(resolve, 600));
    } else {
      setProcessingStep("🔍 Analyzing your request...");
      await new Promise(resolve => setTimeout(resolve, 800));
      
      setProcessingStep("🤖 Routing to appropriate agent...");
      await new Promise(resolve => setTimeout(resolve, 600));
    }

    try {
      // Use enhanced endpoint for authenticated users
      const endpoint = isAuthenticated ? '/enhanced-chat' : '/chat';
      
      const token = localStorage.getItem('auth_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      
      const response = await axios.post(`${API}${endpoint}`, {
        message: originalMessage,
        session_id: sessionId
      }, { headers });

      const agentUsed = response.data.agent_used;
      const workflowType = response.data.workflow_type;
      const agentsInvolved = response.data.agents_involved || [];
      
      setCurrentAgent(agentUsed);
      setWorkflowType(workflowType);
      setAgentsInvolved(agentsInvolved);
      
      // Enhanced processing indicators
      if (isAuthenticated && agentsInvolved.length > 1) {
        setProcessingStep(`⚡ ${agentsInvolved.length} agents collaborating on multi-step workflow...`);
        await new Promise(resolve => setTimeout(resolve, 1200));
      } else {
        const agentNames = {
          'calendar_agent': '📅 Calendar Agent', 
          'file_summarizer_agent': '📄 File Summarizer Agent',
          'notes_agent': '📝 Notes Agent',
          'enhanced_multi_agent': '⚡ Multi-Agent Collaboration',
          'enhanced_orchestrator': '🚀 Enhanced AI Orchestrator',
          'general': '🤖 AI Assistant'
        };
        
        setProcessingStep(`${agentNames[agentUsed] || '🤖 AI Agent'} processing...`);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      const agentMessage = {
        id: Date.now() + 1,
        message: response.data.response,
        sender: "agent",
        agent_type: response.data.agent_used,
        timestamp: response.data.timestamp,
        enhanced: response.data.enhanced || false,
        workflow_type: workflowType,
        agents_involved: agentsInvolved
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
      setWorkflowType(null);
      setAgentsInvolved([]);
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

    // Enhanced upload processing steps
    setProcessingStep("📤 Uploading file with enhanced security...");
    await new Promise(resolve => setTimeout(resolve, 800));
    
    if (isAuthenticated) {
      setProcessingStep("🔍 Advanced AI analysis with multi-agent collaboration...");
      await new Promise(resolve => setTimeout(resolve, 600));
      
      setProcessingStep("⚡ Enhanced File Analyzer Agent orchestrating workflow...");
    } else {
      setProcessingStep("🔍 Analyzing file content...");
      await new Promise(resolve => setTimeout(resolve, 600));
      
      setProcessingStep("📄 File Summarizer Agent processing...");
    }

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("session_id", sessionId);

      // Use appropriate upload endpoint based on authentication
      const endpoint = isAuthenticated ? '/upload' : '/upload-legacy';
      
      const token = localStorage.getItem('auth_token');
      const headers = {
        "Content-Type": "multipart/form-data",
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      };
      
      const response = await axios.post(`${API}${endpoint}`, formData, {
        headers
      });

      const summaryMessage = {
        id: Date.now() + 1,
        message: response.data.summary,
        sender: "agent",
        agent_type: "file_summarizer_agent",
        timestamp: new Date().toISOString(),
        enhanced: isAuthenticated,
        file_info: {
          filename: response.data.filename,
          size: response.data.size,
          processing_type: response.data.processing_type
        }
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
      case "calendar_agent": return <Calendar className="w-4 h-4" />;
      case "file_summarizer_agent": return <FileText className="w-4 h-4" />;
      case "notes_agent": return <StickyNote className="w-4 h-4" />;
      case "enhanced_multi_agent": return <Workflow className="w-4 h-4" />;
      case "enhanced_orchestrator": return <Sparkles className="w-4 h-4" />;
      default: return <Brain className="w-4 h-4" />;
    }
  };

  const getAgentColor = (agentType) => {
    switch (agentType) {
      case "calendar_agent": return "bg-green-500";
      case "file_summarizer_agent": return "bg-purple-500";
      case "notes_agent": return "bg-orange-500";
      case "enhanced_multi_agent": return "bg-gradient-to-r from-purple-500 to-pink-500";
      case "enhanced_orchestrator": return "bg-gradient-to-r from-blue-500 to-indigo-500";
      default: return "bg-gray-500";
    }
  };

  const getAgentName = (agentType) => {
    switch (agentType) {
      case "calendar_agent": return "📅 Calendar Agent";
      case "file_summarizer_agent": return "📄 File Summarizer Agent";
      case "notes_agent": return "📝 Notes Agent";
      case "enhanced_multi_agent": return "⚡ Multi-Agent Collaboration";
      case "enhanced_orchestrator": return "🚀 Enhanced AI Orchestrator";
      default: return "🤖 AI Assistant";
    }
  };

  const enhancedQuickActions = [
    { text: "Analyze this document and save key insights to my notes", icon: <Zap className="w-4 h-4" />, enhanced: true },
    { text: "Schedule a team meeting and create meeting notes", icon: <Users className="w-4 h-4" />, enhanced: true },
    { text: "Create comprehensive meeting notes with action items", icon: <Crown className="w-4 h-4" />, enhanced: true }
  ];

  const basicQuickActions = [
    { text: "Send an email to john@example.com about meeting", icon: <Mail className="w-4 h-4" /> },
    { text: "What's on my calendar today?", icon: <Calendar className="w-4 h-4" /> },
    { text: "Take a note: Remember to follow up on project proposal", icon: <StickyNote className="w-4 h-4" /> },
    { text: "Help me schedule a team meeting for tomorrow", icon: <Calendar className="w-4 h-4" /> }
  ];

  const quickActions = isAuthenticated ? enhancedQuickActions : basicQuickActions;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Enhanced Header */}
      <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-xl ${isAuthenticated 
                ? 'bg-gradient-to-br from-purple-600 to-indigo-600' 
                : 'bg-gradient-to-br from-blue-600 to-indigo-600'
              }`}>
                {isAuthenticated ? <Sparkles className="w-6 h-6 text-white" /> : <Bot className="w-6 h-6 text-white" />}
              </div>
              <div>
                <h1 className={`text-2xl font-bold bg-gradient-to-r ${isAuthenticated 
                  ? 'from-purple-600 to-indigo-600'
                  : 'from-blue-600 to-indigo-600'
                } bg-clip-text text-transparent`}>
                  {isAuthenticated ? 'Enhanced AI Agents' : 'AI Agents'}
                </h1>
                <p className="text-sm text-slate-600">
                  {isAuthenticated ? 'Advanced Multi-Agent Collaboration' : 'The Future of Automation'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {isAuthenticated && (
                <div className="flex items-center space-x-2">
                  <Badge variant="outline" className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span>Enhanced Mode</span>
                  </Badge>
                  <Badge variant="outline" className="flex items-center space-x-1">
                    <Workflow className="w-3 h-3" />
                    <span>LangGraph Active</span>
                  </Badge>
                </div>
              )}
              <LoginButton />
              {isLoading && currentAgent && (
                <Badge className={`${getAgentColor(currentAgent)} text-white animate-pulse`}>
                  <div className="flex items-center space-x-1">
                    {getAgentIcon(currentAgent)}
                    <span>{getAgentName(currentAgent).replace(/[🤖📧📅📄📝⚡🚀]/g, '')} Working</span>
                  </div>
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Enhanced Agents Panel */}
          <div className="lg:col-span-1">
            <Card className={`h-fit border-0 shadow-lg bg-white/80 backdrop-blur-sm ${
              isAuthenticated ? 'ring-2 ring-purple-200' : ''
            }`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center space-x-2">
                  {isAuthenticated ? <Sparkles className="w-5 h-5 text-purple-600" /> : <Bot className="w-5 h-5 text-blue-600" />}
                  <span>{isAuthenticated ? 'Enhanced Agents' : 'Available Agents'}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Agent cards with enhanced styling for authenticated users */}
                <div className={`flex items-center space-x-3 p-3 rounded-xl ${
                  isAuthenticated ? 'bg-purple-50 border border-purple-200' : 'bg-blue-50 border border-blue-200'
                }`}>
                  <div className={`p-2 rounded-lg ${
                    isAuthenticated ? 'bg-purple-500' : 'bg-blue-500'
                  }`}>
                    <Mail className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className={`font-medium ${
                      isAuthenticated ? 'text-purple-900' : 'text-blue-900'
                    }`}>
                      {isAuthenticated ? 'Smart Email Agent' : 'Email Agent'}
                    </p>
                    <p className={`text-xs ${
                      isAuthenticated ? 'text-purple-600' : 'text-blue-600'
                    }`}>
                      {isAuthenticated ? 'Send emails with meeting invites' : 'Send & manage emails'}
                    </p>
                  </div>
                  {isAuthenticated && <Sparkles className="w-4 h-4 text-purple-500" />}
                </div>

                {/* More agent cards... */}
                {isAuthenticated && (
                  <div className="flex items-center space-x-3 p-3 rounded-xl bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200">
                    <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                      <Workflow className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-purple-900">LangGraph Orchestrator</p>
                      <p className="text-xs text-purple-600">Multi-agent collaboration engine</p>
                    </div>
                    <Crown className="w-4 h-4 text-purple-500" />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Enhanced Quick Actions */}
            <Card className="mt-6 border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center space-x-2">
                  {isAuthenticated ? <Zap className="w-5 h-5 text-purple-600" /> : <Bot className="w-5 h-5" />}
                  <span>{isAuthenticated ? 'Enhanced Workflows' : 'Quick Actions'}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {quickActions.map((action, index) => (
                  <Button
                    key={index}
                    variant="ghost"
                    className={`w-full text-left justify-start h-auto p-3 text-sm ${
                      action.enhanced ? 'hover:bg-purple-50 border border-purple-100' : ''
                    }`}
                    onClick={() => setInputMessage(action.text)}
                  >
                    <div className="flex items-start space-x-2">
                      {action.icon}
                      <span className="text-wrap">{action.text}</span>
                      {action.enhanced && <Sparkles className="w-3 h-3 text-purple-500 flex-shrink-0 mt-0.5" />}
                    </div>
                  </Button>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Enhanced Chat Interface */}
          <div className="lg:col-span-3">
            <Card className={`h-[700px] flex flex-col border-0 shadow-xl bg-white/80 backdrop-blur-sm ${
              isAuthenticated ? 'ring-2 ring-purple-200' : ''
            }`}>
              <CardHeader className={`flex-shrink-0 border-b ${
                isAuthenticated 
                  ? 'bg-gradient-to-r from-purple-50 to-indigo-50' 
                  : 'bg-gradient-to-r from-slate-50 to-blue-50'
              }`}>
                <CardTitle className="text-xl flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {isAuthenticated ? <Sparkles className="w-6 h-6 text-purple-600" /> : <Bot className="w-6 h-6 text-blue-600" />}
                    <span>{isAuthenticated ? 'Enhanced AI Assistant' : 'AI Assistant'}</span>
                  </div>
                  {isAuthenticated && (
                    <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                      <Shield className="w-3 h-3 mr-1" />
                      Authenticated
                    </Badge>
                  )}
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
                            ? isAuthenticated
                              ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white"
                              : "bg-blue-600 text-white"
                            : "bg-slate-100 text-slate-900"
                        }`}
                      >
                        {msg.sender === "agent" && msg.agent_type && (
                          <div className="flex items-center space-x-2 mb-2 opacity-75">
                            <div className={`p-1 rounded-md ${getAgentColor(msg.agent_type)}`}>
                              {getAgentIcon(msg.agent_type)}
                            </div>
                            <div className="flex items-center space-x-1">
                              <span className="text-xs font-medium capitalize">
                                {msg.agent_type.replace('_agent', '').replace('_', ' ')} Agent
                              </span>
                              {msg.enhanced && <Sparkles className="w-3 h-3" />}
                            </div>
                            {msg.agents_involved && msg.agents_involved.length > 1 && (
                              <Badge variant="outline" className="text-xs py-0 px-1">
                                <Workflow className="w-3 h-3 mr-1" />
                                {msg.agents_involved.length} agents
                              </Badge>
                            )}
                          </div>
                        )}
                        <div className="whitespace-pre-wrap text-sm leading-relaxed">
                          {msg.html_response ? (
                            <div dangerouslySetInnerHTML={{ __html: msg.html_response }} />
                          ) : (
                            msg.message
                          )}
                        </div>
                        <div className={`text-xs mt-2 opacity-60 flex items-center justify-between`}>
                          <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                          {msg.enhanced && (
                            <Badge variant="outline" className="text-xs py-0 px-1">
                              <Crown className="w-3 h-3 mr-1" />
                              Enhanced
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {/* Loading indicator with enhanced styling for authenticated users */}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className={`border rounded-2xl px-4 py-3 max-w-[80%] ${
                        isAuthenticated 
                          ? 'bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200'
                          : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200'
                      }`}>
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <div className={`animate-spin w-5 h-5 border-2 border-t-transparent rounded-full ${
                              isAuthenticated ? 'border-purple-600' : 'border-blue-600'
                            }`}></div>
                            {currentAgent && (
                              <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full animate-pulse ${getAgentColor(currentAgent)}`}></div>
                            )}
                          </div>
                          <div className="flex-1">
                            <div className={`text-sm font-medium ${
                              isAuthenticated ? 'text-purple-900' : 'text-blue-900'
                            }`}>
                              {processingStep || "AI Agent is thinking..."}
                            </div>
                            {currentAgent && (
                              <div className={`text-xs mt-1 flex items-center space-x-1 ${
                                isAuthenticated ? 'text-purple-600' : 'text-blue-600'
                              }`}>
                                <span>{getAgentName(currentAgent)} is working on your request</span>
                                {isAuthenticated && <Sparkles className="w-3 h-3" />}
                              </div>
                            )}
                            {agentsInvolved.length > 1 && (
                              <div className="text-xs mt-1 text-purple-600">
                                <Workflow className="w-3 h-3 inline mr-1" />
                                Multi-agent collaboration active
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* Enhanced Input Area */}
              <div className="flex-shrink-0 border-t bg-slate-50 p-4">
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                    className={`flex-shrink-0 transition-colors ${
                      isAuthenticated 
                        ? 'hover:bg-purple-50 hover:border-purple-300'
                        : 'hover:bg-blue-50 hover:border-blue-300'
                    }`}
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
                    onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && (useStreaming ? sendStreamingMessage() : sendMessage())}
                    placeholder={isAuthenticated 
                      ? "Ask your enhanced AI agents for multi-agent collaboration..."
                      : "Ask your AI agents to help with emails, calendar, files, or notes..."
                    }
                    className={`flex-1 border-0 bg-white shadow-sm transition-all ${
                      isAuthenticated 
                        ? 'focus:ring-2 focus:ring-purple-500'
                        : 'focus:ring-2 focus:ring-blue-500'
                    }`}
                    disabled={isLoading || isStreaming}
                  />
                  
                  <Button
                    onClick={useStreaming ? sendStreamingMessage : sendMessage}
                    disabled={!inputMessage.trim() || isLoading || isStreaming}
                    className={`flex-shrink-0 transition-all duration-200 shadow-lg hover:shadow-xl ${
                      isAuthenticated 
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700'
                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700'
                    }`}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex justify-between items-center mt-2">
                  <div className="flex items-center space-x-3">
                    <p className="text-xs text-slate-500">
                      {isAuthenticated 
                        ? 'Enhanced features active • Multi-agent workflows • Press Ctrl+/ for shortcuts'
                        : 'Upload documents • Press Enter to send • Ctrl+/ for shortcuts • Sign in for enhanced features'
                      }
                    </p>
                    {/* Streaming toggle hidden - using regular mode only */}
                  </div>
                  {isLoading && (
                    <div className={`text-xs font-medium ${
                      isAuthenticated ? 'text-purple-600' : 'text-blue-600'
                    }`}>
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

// Auth Callback Component
function AuthCallback() {
  const { handleAuthCallback } = useAuth();
  const [status, setStatus] = useState('processing');

  useEffect(() => {
    const processCallback = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        
        if (code) {
          await handleAuthCallback(code);
          setStatus('success');
          // Redirect to main app after successful auth
          setTimeout(() => {
            window.location.href = '/';
          }, 2000);
        } else {
          setStatus('error');
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        setStatus('error');
      }
    };

    processCallback();
  }, [handleAuthCallback]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
      <Card className="w-96 text-center">
        <CardContent className="p-8">
          {status === 'processing' && (
            <div className="space-y-4">
              <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
              <h2 className="text-xl font-semibold">Completing Sign In...</h2>
              <p className="text-gray-600">Please wait while we authenticate your account.</p>
            </div>
          )}
          {status === 'success' && (
            <div className="space-y-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-green-700">Sign In Successful!</h2>
              <p className="text-gray-600">Redirecting you to the enhanced AI agents...</p>
            </div>
          )}
          {status === 'error' && (
            <div className="space-y-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-red-700">Sign In Failed</h2>
              <p className="text-gray-600">There was an error signing you in. Please try again.</p>
              <Button onClick={() => window.location.href = '/'} className="mt-4">
                Return to Home
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Main App Component
function App() {
  const isCallback = window.location.pathname === '/auth/callback';

  return (
    <AuthProvider>
      {isCallback ? <AuthCallback /> : <ChatInterface />}
    </AuthProvider>
  );
}

export default App;