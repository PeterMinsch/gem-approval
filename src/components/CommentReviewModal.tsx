import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { ExternalLink, Check, X } from "lucide-react";
import { Comment } from "./CommentCard";
import { StatusBadge } from "./StatusBadge";

interface CommentReviewModalProps {
  comment: Comment | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (commentId: string, editedComment: string) => void;
  onReject: (commentId: string) => void;
}

export function CommentReviewModal({ 
  comment, 
  isOpen, 
  onClose, 
  onApprove, 
  onReject 
}: CommentReviewModalProps) {
  const [editedComment, setEditedComment] = useState("");
  
  useEffect(() => {
    if (comment) {
      setEditedComment(comment.suggestedComment);
    }
  }, [comment]);

  if (!comment) return null;

  const handleApprove = () => {
    onApprove(comment.id, editedComment);
    onClose();
  };

  const handleReject = () => {
    onReject(comment.id);
    onClose();
  };

  const isPending = comment.status === 'pending';

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              Review Comment
              <StatusBadge status={comment.status} />
            </DialogTitle>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => window.open(comment.postUrl, '_blank')}
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              View Post
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label className="text-sm font-medium">Original Facebook Post</Label>
            <div className="mt-1 p-3 bg-muted/50 rounded-md border text-sm">
              {comment.postText}
            </div>
          </div>

          <div>
            <Label htmlFor="comment-edit" className="text-sm font-medium">
              {isPending ? "Edit Comment (Optional)" : "Comment Content"}
            </Label>
            <Textarea
              id="comment-edit"
              value={editedComment}
              onChange={(e) => setEditedComment(e.target.value)}
              className="mt-1 min-h-[100px]"
              placeholder="Enter your comment..."
              disabled={!isPending}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Character count: {editedComment.length}
            </p>
          </div>

          <div className="text-xs text-muted-foreground">
            <p>Created: {new Date(comment.createdAt).toLocaleString()}</p>
            {comment.approvedAt && (
              <p>Approved: {new Date(comment.approvedAt).toLocaleString()}</p>
            )}
            {comment.postedAt && (
              <p>Posted: {new Date(comment.postedAt).toLocaleString()}</p>
            )}
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          
          {isPending && (
            <>
              <Button
                variant="destructive"
                onClick={handleReject}
              >
                <X className="h-3 w-3 mr-1" />
                Reject
              </Button>
              <Button
                onClick={handleApprove}
                disabled={!editedComment.trim()}
                className="bg-success hover:bg-success/90 text-success-foreground"
              >
                <Check className="h-3 w-3 mr-1" />
                Approve & Save
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}