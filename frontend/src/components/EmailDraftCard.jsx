import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Mail, 
  Send, 
  CheckCircle, 
  XCircle, 
  Edit, 
  AlertTriangle,
  Shield,
  Clock,
  User,
  FileText,
  Sparkles
} from 'lucide-react';

/**
 * Email Draft Preview Card Component
 * Displays email drafts with approval/rejection controls
 */
export function EmailDraftCard({ draft, onApprove, onReject, onEdit, onSend, isAuthenticated = false }) {
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  if (!draft) return null;

  const handleApprove = async () => {
    setIsLoading(true);
    try {
      await onApprove?.(draft.draft_id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    setIsLoading(true);
    try {
      await onReject?.(draft.draft_id);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    setIsLoading(true);
    try {
      await onSend?.(draft.draft_id);
    } finally {
      setIsLoading(false);
    }
  };

  // Status colors
  const getStatusColor = (status) => {
    switch (status) {
      case 'drafted': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'pending_approval': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'approved': return 'bg-green-100 text-green-700 border-green-200';
      case 'rejected': return 'bg-red-100 text-red-700 border-red-200';
      case 'sent': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'failed': return 'bg-red-100 text-red-700 border-red-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // Risk level colors
  const getRiskColor = (level) => {
    switch (level) {
      case 'low': return 'text-green-600';
      case 'medium': return 'text-yellow-600';
      case 'high': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const safetyChecks = draft.safety_checks || {};
  const hasFlags = safetyChecks.flags && safetyChecks.flags.length > 0;

  return (
    <Card className={`border-0 shadow-lg transition-all duration-200 ${
      isAuthenticated 
        ? 'bg-gradient-to-br from-purple-50 to-indigo-50 ring-2 ring-purple-200' 
        : 'bg-white'
    }`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${
              isAuthenticated 
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600' 
                : 'bg-blue-600'
            }`}>
              <Mail className="w-5 h-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-lg flex items-center space-x-2">
                <span>Email Draft</span>
                {isAuthenticated && <Sparkles className="w-4 h-4 text-purple-600" />}
              </CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                {draft.created_at ? new Date(draft.created_at).toLocaleString() : 'Just now'}
              </p>
            </div>
          </div>
          <Badge className={`${getStatusColor(draft.status)} border`}>
            {draft.status.replace('_', ' ')}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Draft Details */}
        <div className="space-y-3">
          {/* To */}
          <div className="flex items-start space-x-3">
            <User className="w-4 h-4 text-slate-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-slate-500 font-medium">To</p>
              <p className="text-sm font-medium text-slate-900">{draft.to}</p>
            </div>
          </div>

          {/* CC/BCC */}
          {(draft.cc || draft.bcc) && (
            <div className="flex items-start space-x-3">
              <User className="w-4 h-4 text-slate-500 mt-0.5" />
              <div className="flex-1">
                {draft.cc && (
                  <div className="mb-1">
                    <p className="text-xs text-slate-500 font-medium">CC</p>
                    <p className="text-sm text-slate-700">{draft.cc.join(', ')}</p>
                  </div>
                )}
                {draft.bcc && (
                  <div>
                    <p className="text-xs text-slate-500 font-medium">BCC</p>
                    <p className="text-sm text-slate-700">{draft.bcc.join(', ')}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Subject */}
          <div className="flex items-start space-x-3">
            <FileText className="w-4 h-4 text-slate-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-slate-500 font-medium">Subject</p>
              <p className="text-sm font-semibold text-slate-900">{draft.subject}</p>
            </div>
          </div>

          <Separator />

          {/* Body Preview */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500 font-medium">Message</p>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setExpanded(!expanded)}
                className="h-6 text-xs"
              >
                {expanded ? 'Collapse' : 'Expand'}
              </Button>
            </div>
            <div className={`bg-white border border-slate-200 rounded-lg p-4 ${
              expanded ? 'max-h-96 overflow-y-auto' : 'max-h-24 overflow-hidden'
            }`}>
              <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans">
                {draft.body}
              </pre>
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <Clock className="w-3 h-3" />
              <span>Tone: <span className="font-medium text-slate-700">{draft.tone || 'professional'}</span></span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <AlertTriangle className="w-3 h-3" />
              <span>Priority: <span className="font-medium text-slate-700">{draft.priority || 'medium'}</span></span>
            </div>
          </div>
        </div>

        {/* Safety Checks */}
        {safetyChecks && (
          <div className="space-y-2">
            <Separator />
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-700">Safety Checks</span>
              </div>
              <Badge variant="outline" className={`text-xs ${getRiskColor(safetyChecks.risk_level)}`}>
                {safetyChecks.risk_level || 'unknown'} risk
              </Badge>
            </div>

            {hasFlags && (
              <Alert className="bg-yellow-50 border-yellow-200">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                <AlertDescription className="text-xs text-yellow-800 ml-2">
                  <p className="font-medium mb-1">Issues detected:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {safetyChecks.flags.slice(0, 3).map((flag, idx) => (
                      <li key={idx}>{flag}</li>
                    ))}
                  </ul>
                  {safetyChecks.recommendations && safetyChecks.recommendations.length > 0 && (
                    <p className="mt-2 font-medium">
                      💡 {safetyChecks.recommendations[0]}
                    </p>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {!hasFlags && safetyChecks.passed && (
              <div className="flex items-center space-x-2 text-xs text-green-600">
                <CheckCircle className="w-4 h-4" />
                <span>All safety checks passed</span>
              </div>
            )}
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-between items-center pt-4 border-t bg-slate-50/50">
        <div className="flex space-x-2">
          {draft.status === 'pending_approval' && (
            <>
              <Button
                onClick={handleApprove}
                disabled={isLoading}
                className={`${
                  isAuthenticated
                    ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700'
                    : 'bg-green-600 hover:bg-green-700'
                } text-white shadow-md`}
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Approve
              </Button>
              <Button
                onClick={handleReject}
                disabled={isLoading}
                variant="outline"
                className="border-red-300 text-red-600 hover:bg-red-50"
              >
                <XCircle className="w-4 h-4 mr-2" />
                Reject
              </Button>
            </>
          )}

          {draft.status === 'approved' && (
            <Button
              onClick={handleSend}
              disabled={isLoading}
              className={`${
                isAuthenticated
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700'
                  : 'bg-blue-600 hover:bg-blue-700'
              } text-white shadow-md`}
            >
              <Send className="w-4 h-4 mr-2" />
              Send Email
            </Button>
          )}

          {draft.status === 'sent' && (
            <Badge className="bg-purple-100 text-purple-700 border-purple-200">
              <CheckCircle className="w-4 h-4 mr-1" />
              Email Sent Successfully
            </Badge>
          )}
        </div>

        {onEdit && draft.status !== 'sent' && (
          <Button
            onClick={() => onEdit?.(draft)}
            variant="ghost"
            size="sm"
            disabled={isLoading}
            className="text-slate-600 hover:text-slate-900"
          >
            <Edit className="w-4 h-4 mr-2" />
            Edit
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

export default EmailDraftCard;
