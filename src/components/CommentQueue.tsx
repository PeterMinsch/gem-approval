import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Badge } from "./ui/badge";
import { Textarea } from "./ui/textarea";
import { CheckCircle, XCircle, Edit, ExternalLink, MessageCircle } from "lucide-react";

interface QueuedComment {
  id: string;
  post_url: string;
  post_text: string;
  generated_comment: string;
  post_type: string;
  post_author?: string;
  post_engagement?: string;
  status: string;
  created_at: string;
}

export const CommentQueue: React.FC = () => {
  const [comments, setComments] = useState<QueuedComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingComment, setEditingComment] = useState<string | null>(null);
  const [editedText, setEditedText] = useState("");

  useEffect(() => {
    fetchComments();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchComments, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchComments = async () => {
    try {
      const response = await fetch("http://localhost:8000/comments/queue");
      if (response.ok) {
        const data = await response.json();
        setComments(data);
      }
    } catch (error) {
      console.error("Failed to fetch comments:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (commentId: string) => {
    try {
      const response = await fetch("http://localhost:8000/comments/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          comment_id: commentId,
          action: "approve",
          edited_comment: editedText || undefined
        })
      });
      
      if (response.ok) {
        setEditingComment(null);
        setEditedText("");
        fetchComments(); // Refresh the list
      }
    } catch (error) {
      console.error("Failed to approve comment:", error);
    }
  };

  const handleReject = async (commentId: string, reason: string) => {
    try {
      const response = await fetch("http://localhost:8000/comments/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          comment_id: commentId,
          action: "reject",
          rejection_reason: reason
        })
      });
      
      if (response.ok) {
        fetchComments(); // Refresh the list
      }
    } catch (error) {
      console.error("Failed to reject comment:", error);
    }
  };

  const startEditing = (comment: QueuedComment) => {
    setEditingComment(comment.id);
    setEditedText(comment.generated_comment);
  };

  const cancelEditing = () => {
    setEditingComment(null);
    setEditedText("");
  };

  const getPostTypeColor = (postType: string) => {
    switch (postType) {
      case "service": return "bg-blue-100 text-blue-800";
      case "iso": return "bg-green-100 text-green-800";
      case "general": return "bg-purple-100 text-purple-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Comment Queue</CardTitle>
          <CardDescription>Loading comments...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          Comment Approval Queue
        </CardTitle>
        <CardDescription>
          {comments.length} comments waiting for approval
        </CardDescription>
      </CardHeader>
      <CardContent>
        {comments.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No comments in queue</p>
        ) : (
          <div className="space-y-4">
            {comments.map((comment) => (
              <Card key={comment.id} className="border-l-4 border-l-blue-500">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={getPostTypeColor(comment.post_type)}>
                          {comment.post_type.toUpperCase()}
                        </Badge>
                        {comment.post_author && (
                          <span className="text-sm text-gray-600">
                            by {comment.post_author}
                          </span>
                        )}
                      </div>
                      
                      <div className="mb-3">
                        <h4 className="font-medium text-sm text-gray-700 mb-1">Original Post:</h4>
                        <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                          {comment.post_text}
                        </p>
                      </div>

                      <div className="mb-3">
                        <h4 className="font-medium text-sm text-gray-700 mb-1">Generated Comment:</h4>
                        {editingComment === comment.id ? (
                          <Textarea
                            value={editedText}
                            onChange={(e) => setEditedText(e.target.value)}
                            className="min-h-[80px]"
                          />
                        ) : (
                          <p className="text-sm bg-blue-50 p-2 rounded">
                            {comment.generated_comment}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>Created: {new Date(comment.created_at).toLocaleString()}</span>
                        {comment.post_engagement && (
                          <span>• {comment.post_engagement}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 ml-4">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => window.open(comment.post_url, '_blank')}
                      >
                        <ExternalLink className="h-4 w-4 mr-1" />
                        View Post
                      </Button>
                      
                      {editingComment === comment.id ? (
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            onClick={() => handleApprove(comment.id)}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Save & Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={cancelEditing}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            onClick={() => startEditing(comment)}
                            variant="outline"
                          >
                            <Edit className="h-4 w-4 mr-1" />
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleApprove(comment.id)}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleReject(comment.id, "Rejected by user")}
                            className="text-red-600 border-red-600 hover:bg-red-50"
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
