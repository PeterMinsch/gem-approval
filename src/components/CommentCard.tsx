import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { ExternalLink, Edit, Check, X, Clock } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

export type CommentStatus = 'pending' | 'approved' | 'rejected' | 'posted';

export interface Comment {
  id: string;
  postUrl: string;
  postText: string;
  suggestedComment: string;
  status: CommentStatus;
  createdAt: string;
  approvedAt?: string;
  postedAt?: string;
}

interface CommentCardProps {
  comment: Comment;
  onEdit: (comment: Comment) => void;
  onApprove: (commentId: string) => void;
  onReject: (commentId: string) => void;
}

export function CommentCard({ comment, onEdit, onApprove, onReject }: CommentCardProps) {
  const isPending = comment.status === 'pending';
  
  return (
    <Card className="transition-all duration-200 hover:shadow-lg border border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <StatusBadge status={comment.status} />
              <span className="text-xs text-muted-foreground">
                {new Date(comment.createdAt).toLocaleString()}
              </span>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {comment.postText}
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => window.open(comment.postUrl, '_blank')}
            className="shrink-0"
          >
            <ExternalLink className="h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-2">
          <h4 className="font-medium text-sm">Suggested Comment:</h4>
          <p className="text-sm bg-muted/50 p-3 rounded-md border">
            {comment.suggestedComment}
          </p>
        </div>
      </CardContent>
      
      <CardFooter className="pt-0">
        <div className="flex gap-2 w-full">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onEdit(comment)}
            className="flex-1"
            disabled={!isPending}
          >
            <Edit className="h-3 w-3 mr-1" />
            Edit
          </Button>
          
          {isPending && (
            <>
              <Button
                variant="default"
                size="sm"
                onClick={() => onApprove(comment.id)}
                className="bg-success hover:bg-success/90 text-success-foreground"
              >
                <Check className="h-3 w-3 mr-1" />
                Approve
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onReject(comment.id)}
              >
                <X className="h-3 w-3 mr-1" />
                Reject
              </Button>
            </>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}