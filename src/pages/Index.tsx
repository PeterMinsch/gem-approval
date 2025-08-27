import { useState } from "react";
import { CommentCard, Comment } from "@/components/CommentCard";
import { CommentReviewModal } from "@/components/CommentReviewModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MessageSquare, Clock, Check, X, CheckCircle, RefreshCw } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

// Mock data for demonstration
const mockComments: Comment[] = [
  {
    id: '1',
    postUrl: 'https://facebook.com/groups/jewelry/posts/123',
    postText: 'Looking for elegant diamond earrings for my wedding. Any recommendations for trusted jewelers?',
    suggestedComment: 'Congratulations on your upcoming wedding! 💎 For elegant diamond earrings, I highly recommend visiting our showroom. We specialize in bridal jewelry and have a beautiful collection of certified diamond earrings. Feel free to DM us for more details!',
    status: 'pending',
    createdAt: '2024-01-15T10:30:00Z'
  },
  {
    id: '2',
    postUrl: 'https://facebook.com/groups/jewelry/posts/124',
    postText: 'My gold chain broke and needs repair. Where can I find reliable jewelry repair services?',
    suggestedComment: 'Sorry to hear about your chain! We offer professional gold chain repair services with same-day turnaround for most repairs. Our skilled craftsmen can restore your jewelry to like-new condition. Bring it in for a free estimate!',
    status: 'approved',
    createdAt: '2024-01-15T09:15:00Z',
    approvedAt: '2024-01-15T09:45:00Z'
  },
  {
    id: '3',
    postUrl: 'https://facebook.com/groups/jewelry/posts/125',
    postText: 'What\'s the difference between 14k and 18k gold? Planning to buy a necklace.',
    suggestedComment: 'Great question! 14k gold is 58.3% pure gold and more durable for everyday wear, while 18k gold is 75% pure gold with a richer color but softer. For necklaces, both are excellent choices - 14k for daily wear, 18k for special occasions. Happy to help you choose the perfect piece!',
    status: 'posted',
    createdAt: '2024-01-14T16:20:00Z',
    approvedAt: '2024-01-14T16:30:00Z',
    postedAt: '2024-01-14T16:35:00Z'
  },
  {
    id: '4',
    postUrl: 'https://facebook.com/groups/jewelry/posts/126',
    postText: 'Selling vintage pearl necklace, inherited from grandmother. How to determine its value?',
    suggestedComment: 'Beautiful inheritance! Vintage pearls can be quite valuable. We offer complimentary appraisal services for vintage jewelry. Our certified gemologists can help determine authenticity, quality, and current market value. Schedule a consultation today!',
    status: 'rejected',
    createdAt: '2024-01-14T14:10:00Z'
  }
];

const Index = () => {
  const [comments, setComments] = useState<Comment[]>(mockComments);
  const [selectedComment, setSelectedComment] = useState<Comment | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("pending");
  const { toast } = useToast();

  const handleEdit = (comment: Comment) => {
    setSelectedComment(comment);
    setIsModalOpen(true);
  };

  const handleApprove = (commentId: string, editedComment?: string) => {
    setComments(prev => 
      prev.map(comment => 
        comment.id === commentId 
          ? { 
              ...comment, 
              status: 'approved' as const,
              suggestedComment: editedComment || comment.suggestedComment,
              approvedAt: new Date().toISOString()
            }
          : comment
      )
    );
    toast({
      title: "Comment Approved",
      description: "The comment has been approved and is ready for posting.",
    });
  };

  const handleReject = (commentId: string) => {
    setComments(prev => 
      prev.map(comment => 
        comment.id === commentId 
          ? { ...comment, status: 'rejected' as const }
          : comment
      )
    );
    toast({
      title: "Comment Rejected",
      description: "The comment has been rejected and will not be posted.",
      variant: "destructive",
    });
  };

  const getFilteredComments = (status?: string) => {
    if (!status || status === 'all') return comments;
    return comments.filter(comment => comment.status === status);
  };

  const getStatusCount = (status: string) => {
    return comments.filter(comment => comment.status === status).length;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                Facebook Comment CRM
              </h1>
              <p className="text-muted-foreground mt-1">
                Review and manage automated Facebook comments for jewelry posts
              </p>
            </div>
            <Button variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Sync Comments
            </Button>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-card rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-pending" />
                <span className="text-sm font-medium">Pending</span>
              </div>
              <p className="text-2xl font-bold text-pending mt-1">
                {getStatusCount('pending')}
              </p>
            </div>
            <div className="bg-card rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-success" />
                <span className="text-sm font-medium">Approved</span>
              </div>
              <p className="text-2xl font-bold text-success mt-1">
                {getStatusCount('approved')}
              </p>
            </div>
            <div className="bg-card rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-success" />
                <span className="text-sm font-medium">Posted</span>
              </div>
              <p className="text-2xl font-bold text-success mt-1">
                {getStatusCount('posted')}
              </p>
            </div>
            <div className="bg-card rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <X className="h-4 w-4 text-destructive" />
                <span className="text-sm font-medium">Rejected</span>
              </div>
              <p className="text-2xl font-bold text-destructive mt-1">
                {getStatusCount('rejected')}
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5 mb-6">
            <TabsTrigger value="pending" className="flex items-center gap-2">
              <Clock className="h-3 w-3" />
              Pending ({getStatusCount('pending')})
            </TabsTrigger>
            <TabsTrigger value="approved" className="flex items-center gap-2">
              <Check className="h-3 w-3" />
              Approved ({getStatusCount('approved')})
            </TabsTrigger>
            <TabsTrigger value="posted" className="flex items-center gap-2">
              <CheckCircle className="h-3 w-3" />
              Posted ({getStatusCount('posted')})
            </TabsTrigger>
            <TabsTrigger value="rejected" className="flex items-center gap-2">
              <X className="h-3 w-3" />
              Rejected ({getStatusCount('rejected')})
            </TabsTrigger>
            <TabsTrigger value="all" className="flex items-center gap-2">
              <MessageSquare className="h-3 w-3" />
              All ({comments.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pending">
            <CommentGrid 
              comments={getFilteredComments('pending')} 
              onApprove={handleApprove}
              onReject={handleReject}
              emptyMessage="No pending comments to review."
            />
          </TabsContent>
          
          <TabsContent value="approved">
            <CommentGrid 
              comments={getFilteredComments('approved')} 
              onApprove={handleApprove}
              onReject={handleReject}
              emptyMessage="No approved comments."
            />
          </TabsContent>
          
          <TabsContent value="posted">
            <CommentGrid 
              comments={getFilteredComments('posted')} 
              onApprove={handleApprove}
              onReject={handleReject}
              emptyMessage="No posted comments yet."
            />
          </TabsContent>
          
          <TabsContent value="rejected">
            <CommentGrid 
              comments={getFilteredComments('rejected')} 
              onApprove={handleApprove}
              onReject={handleReject}
              emptyMessage="No rejected comments."
            />
          </TabsContent>
          
          <TabsContent value="all">
            <CommentGrid 
              comments={getFilteredComments('all')} 
              onApprove={handleApprove}
              onReject={handleReject}
              emptyMessage="No comments available."
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Review Modal */}
      <CommentReviewModal
        comment={selectedComment}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedComment(null);
        }}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </div>
  );
};

interface CommentGridProps {
  comments: Comment[];
  onApprove: (commentId: string, editedComment?: string) => void;
  onReject: (commentId: string) => void;
  emptyMessage: string;
}

function CommentGrid({ comments, onApprove, onReject, emptyMessage }: CommentGridProps) {
  if (comments.length === 0) {
    return (
      <div className="text-center py-12">
        <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p className="text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {comments.map((comment) => (
        <CommentCard
          key={comment.id}
          comment={comment}
          onApprove={onApprove}
          onReject={onReject}
        />
      ))}
    </div>
  );
}

export default Index;