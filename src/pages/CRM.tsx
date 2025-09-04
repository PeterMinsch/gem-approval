import { useState, useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  MessageCircle,
  ExternalLink,
  XCircle,
  Send,
  SkipForward,
  Save,
  Image,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Post {
  id: string;
  post_url: string;
  post_text: string;
  generated_comment: string;
  post_type: string;
  post_author?: string;
  post_engagement?: string;
  status: string;
  created_at: string;
  post_screenshot?: string;
  post_images?: string[];
}

interface Template {
  id: string;
  name: string;
  category: string;
  body: string;
}

const CRM = () => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // Auto-refresh every 5 seconds to show new posts as the bot processes them

  const { toast } = useToast();

  useEffect(() => {
    fetchPosts();
    fetchTemplates();

    // Set up auto-refresh for real-time queue updates
    const interval = setInterval(() => {
      if (!loading) {
        fetchPosts();
      }
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const fetchPosts = async () => {
    try {
      const response = await fetch("http://localhost:8000/comments/queue");

      if (response.ok) {
        const data = await response.json();

        if (data && Array.isArray(data)) {
          setPosts(data);
        } else {
          setPosts([]);
        }
      } else {
        setPosts([]);
      }
    } catch (error) {
      console.error("Error fetching comments:", error);
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await fetch("/api/templates");
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      }
    } catch (error) {
      console.error("Error fetching templates:", error);
    }
  };

  const handleApprove = async (postId: string, commentId: string) => {
    try {
      const response = await fetch(`/api/comments/${commentId}/queue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment_id: commentId }),
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Comment approved and queued",
        });
        fetchPosts(); // Refresh data
      }
    } catch (error) {
      console.error("Error approving comment:", error);
      toast({
        title: "Error",
        description: "Failed to approve comment",
        variant: "destructive",
      });
    }
  };

  const handleSubmit = async (postId: string, commentId: string) => {
    try {
      const response = await fetch(`/api/comments/${commentId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment_id: commentId }),
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Comment submitted for posting",
        });
        fetchPosts(); // Refresh data
      }
    } catch (error) {
      console.error("Error submitting comment:", error);
      toast({
        title: "Error",
        description: "Failed to submit comment",
        variant: "destructive",
      });
    }
  };

  const handleSkip = async (postId: string) => {
    try {
      const response = await fetch(`/api/posts/${postId}/skip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ post_id: postId }),
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Post marked as skipped",
        });
        fetchPosts(); // Refresh data
      }
    } catch (error) {
      console.error("Error skipping post:", error);
      toast({
        title: "Error",
        description: "Failed to skip post",
        variant: "destructive",
      });
    }
  };

  const handlePM = async (postId: string) => {
    try {
      const response = await fetch(`/api/pm-link/${postId}`);
      if (response.ok) {
        const data = await response.json();
        window.open(data.messenger_link, "_blank");
      }
    } catch (error) {
      console.error("Error getting PM link:", error);
      toast({
        title: "Error",
        description: "Failed to get PM link",
        variant: "destructive",
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "PENDING":
        return "bg-yellow-100 text-yellow-800";
      case "APPROVED":
        return "bg-blue-100 text-blue-800";
      case "QUEUED":
        return "bg-purple-100 text-purple-800";
      case "POSTED":
        return "bg-green-100 text-green-800";
      case "SKIPPED":
        return "bg-gray-100 text-gray-800";
      case "PM_SENT":
        return "bg-indigo-100 text-indigo-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getIntentColor = (intent: string) => {
    switch (intent) {
      case "SERVICE":
        return "bg-blue-100 text-blue-800";
      case "ISO_BUY":
        return "bg-green-100 text-green-800";
      case "IGNORE":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const filteredPosts = posts.filter((post) => {
    const matchesSearch =
      searchQuery === "" ||
      post.post_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (post.post_author &&
        post.post_author.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesSearch;
  });

  const getPostsByStatus = (status: string) => {
    const postsForStatus = filteredPosts.filter(
      (post) => post.status === status
    );
    console.log(
      `📊 Posts for status ${status}:`,
      postsForStatus.length,
      postsForStatus
    );
    return postsForStatus;
  };

  console.log("🎯 CRM component rendering with:", {
    loading,
    postsCount: posts.length,
    posts,
  });

  if (loading) {
    console.log("⏳ Showing loading state");
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-lg">Loading CRM...</div>
      </div>
    );
  }

  return (
    <div className="min-h-96">
      <div className="w-full">
        {/* Unified CRM Dashboard Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                Approval Queue
              </h1>
              <p className="text-muted-foreground mt-1">
                Review posts as the bot processes them • Edit comments • Approve
                for Facebook posting
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {getPostsByStatus("PENDING").length}
                </div>
                <div className="text-sm text-muted-foreground">Pending</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {getPostsByStatus("POSTED").length}
                </div>
                <div className="text-sm text-muted-foreground">Posted</div>
              </div>
            </div>
          </div>
        </div>

        {/* Queue Status & Search */}
        <div className="mb-6 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-muted-foreground">
                Queue Active • Auto-refresh every 5s
              </span>
            </div>
            <div className="text-sm text-muted-foreground">
              {filteredPosts.length} post{filteredPosts.length !== 1 ? "s" : ""}{" "}
              in queue
            </div>
          </div>
          <div className="relative w-full md:w-80">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="Search posts, authors, or content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Posts List - Unified Interface */}
        <div className="space-y-4">
          {filteredPosts.length === 0 ? (
            <Card>
              <CardContent className="pt-12 pb-12">
                <div className="text-center">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageCircle className="h-8 w-8 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Queue is Empty
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    No posts are currently waiting for approval.
                  </p>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>• Start your bot to begin scanning Facebook groups</p>
                    <p>
                      • Posts will automatically appear here as they're detected
                    </p>
                    <p>
                      • Each post will include AI-generated comments for your
                      review
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            filteredPosts.map((post) => (
              <PostCard
                key={post.id}
                post={post}
                templates={templates}
                onApprove={handleApprove}
                onSubmit={handleSubmit}
                onSkip={handleSkip}
                onPM={handlePM}
                fetchPosts={fetchPosts}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
};

interface PostCardProps {
  post: Post;
  templates: Template[];
  onApprove: (postId: string, commentId: string) => void;
  onSubmit: (postId: string, commentId: string) => void;
  onSkip: (postId: string) => void;
  onPM: (postId: string) => void;
  fetchPosts: () => Promise<void>;
}

const PostCard = ({ post, fetchPosts, ...otherProps }: PostCardProps) => {
  // Simplified state - only what we need for click-to-edit
  const [commentText, setCommentText] = useState(post.generated_comment || "");
  const [isEditing, setIsEditing] = useState(false);
  const [isPosting, setIsPosting] = useState(false); // Loading state for posting
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // Update comment text when post changes
  useEffect(() => {
    setCommentText(post.generated_comment || "");
  }, [post.generated_comment]);

  // All comments are editable - that's the whole point!
  const canEdit = true;

  const startEditing = () => {
    console.log("startEditing called - comment is now editable");

    setIsEditing(true);

    // Focus textarea after React re-renders
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        // Move cursor to end of text
        const length = textareaRef.current.value.length;
        textareaRef.current.setSelectionRange(length, length);
      }
    }, 0);
  };

  const saveAndPostComment = async () => {
    try {
      setIsPosting(true); // Start loading

      // Show initial progress toast
      toast({
        title: "Starting...",
        description: "Saving your comment and preparing to post...",
      });

      // First save the edited comment
      const saveResponse = await fetch(
        "http://localhost:8000/comments/approve",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            comment_id: post.id,
            action: "approve",
            edited_comment: commentText,
          }),
        }
      );

      if (saveResponse.ok) {
        // Show progress toast
        toast({
          title: "Comment saved! 🎯",
          description: "Now posting to Facebook...",
        });

        // Then post immediately using real-time browser integration
        const postResponse = await fetch(
          `http://localhost:8000/api/comments/${post.id}/submit`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ comment_id: post.id }),
          }
        );

        if (postResponse.ok) {
          setIsEditing(false);
          toast({
            title: "Success! 🎉",
            description: "Comment posted on Facebook in real-time!",
          });
          fetchPosts();
        } else {
          throw new Error("Failed to post comment");
        }
      } else {
        throw new Error("Failed to save comment");
      }
    } catch (error) {
      console.error("Error saving and posting comment:", error);
      toast({
        title: "Error",
        description: `Failed to post comment: ${error.message}`,
        variant: "destructive",
      });
    } finally {
      setIsPosting(false); // Stop loading regardless of outcome
    }
  };

  const cancelEdit = () => {
    setCommentText(post.generated_comment || "");
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      saveAndPostComment();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelEdit();
    }
  };

  // Add utility function to parse image URLs
  const parsePostImages = (post_images?: string | string[]): string[] => {
    if (!post_images) return [];

    // If it's already an array, return it
    if (Array.isArray(post_images)) return post_images;

    // If it's a comma-separated string, split it
    if (typeof post_images === "string") {
      return post_images
        .split(",")
        .map((url) => url.trim())
        .filter((url) => url.length > 0);
    }

    return [];
  };

  const postImages = parsePostImages(post.post_images);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={getStatusColor(post.status)}>
                {post.status}
              </Badge>
              <Badge className={getIntentColor(post.post_type)}>
                {post.post_type.toUpperCase()}
              </Badge>
              {/* Show "New" badge for recent posts */}
              {new Date(post.created_at).getTime() >
                Date.now() - 5 * 60 * 1000 && (
                <Badge className="bg-green-100 text-green-800 animate-pulse">
                  New
                </Badge>
              )}
            </div>
            <CardTitle className="text-lg">
              {post.post_author || "Unknown Author"}
            </CardTitle>
            <CardDescription className="text-sm">
              {new Date(post.created_at).toLocaleString()}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(post.post_url, "_blank")}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Open Post
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => otherProps.onPM(post.id)}
            >
              <MessageCircle className="h-4 w-4 mr-2" />
              PM
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Enhanced Post Images Section */}
        {postImages.length > 0 ? (
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Image className="h-4 w-4" />
              Post Images ({postImages.length})
            </h4>
            <div
              className={`grid gap-3 ${
                postImages.length === 1
                  ? "grid-cols-1"
                  : postImages.length === 2
                  ? "grid-cols-2"
                  : "grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
              }`}
            >
              {postImages.map((url, index) => (
                <div key={index} className="relative group">
                  <div className="aspect-square overflow-hidden rounded-lg border bg-gray-100">
                    <img
                      src={url}
                      alt={`Post image ${index + 1}`}
                      className="w-full h-full object-cover cursor-pointer hover:opacity-90 transition-all duration-200 hover:scale-105"
                      onClick={() => window.open(url, "_blank")}
                      onError={(e) => {
                        // Handle broken images
                        const target = e.target as HTMLImageElement;
                        target.src = "/api/placeholder/200/200";
                        target.alt = "Failed to load image";
                      }}
                    />
                  </div>

                  {/* Image overlay with info */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all rounded-lg flex items-center justify-center">
                    <div className="text-white opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="bg-black bg-opacity-75 px-2 py-1 rounded text-xs font-medium">
                        Click to enlarge
                      </div>
                    </div>
                  </div>

                  {/* Image counter for multiple images */}
                  {postImages.length > 1 && (
                    <div className="absolute top-2 right-2 bg-black bg-opacity-75 text-white px-2 py-1 rounded text-xs font-medium">
                      {index + 1}/{postImages.length}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-500 bg-gray-50 p-4 rounded-lg border-2 border-dashed border-gray-200">
            <div className="flex items-center justify-center gap-2">
              <Image className="h-5 w-5 text-gray-400" />
              <span>No images found in this post</span>
            </div>
          </div>
        )}

        {/* Post Content */}
        <div>
          <h4 className="font-medium mb-2">Post Content</h4>
          <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
            {post.post_text}
          </p>
        </div>

        {/* Quick Info */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <span className="font-medium">Type:</span>
            <Badge className={getIntentColor(post.post_type)}>
              {post.post_type.toUpperCase()}
            </Badge>
          </div>
          {post.post_engagement && (
            <div className="flex items-center gap-1">
              <span className="font-medium">Engagement:</span>
              <span>{post.post_engagement}</span>
            </div>
          )}
        </div>

        {/* Simplified Comment Draft Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">Comment Draft</h4>
            {isEditing && (
              <Badge
                variant="outline"
                className="text-blue-600 border-blue-300"
              >
                Editing
              </Badge>
            )}
            {isPosting && (
              <Badge
                variant="outline"
                className="text-green-600 border-green-300"
              >
                Posting...
              </Badge>
            )}
          </div>

          {isEditing ? (
            // Edit Mode: Show editable textarea with post button
            <div className="space-y-3">
              {isPosting && (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                  <div className="flex items-center space-x-2">
                    <svg
                      className="animate-spin h-4 w-4 text-blue-600"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    <span className="text-sm text-blue-700 font-medium">
                      Posting comment to Facebook...
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-blue-600">
                    This may take a few seconds. Please don't close the browser.
                  </div>
                </div>
              )}
              <textarea
                ref={textareaRef}
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full p-3 border border-blue-300 rounded-md text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 resize-none"
                rows={6}
                placeholder="Edit your comment... (Ctrl+Enter to post, Esc to cancel)"
                disabled={isPosting}
              />
              <div className="flex gap-2">
                <Button
                  onClick={saveAndPostComment}
                  size="sm"
                  className="flex-1"
                  disabled={isPosting}
                >
                  {isPosting ? (
                    <svg
                      className="animate-spin h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Post Comment
                    </>
                  )}
                </Button>
                <Button
                  onClick={cancelEdit}
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  disabled={isPosting}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            // View Mode: Show clickable preview
            <div
              onClick={startEditing}
              className="p-3 border border-gray-300 bg-gray-50 hover:bg-white hover:border-blue-300 hover:shadow-sm cursor-pointer transition-all"
            >
              <div className="min-h-[4rem] whitespace-pre-wrap">
                {commentText || "Click to add a comment..."}
              </div>
              <div className="mt-2 text-xs text-blue-600">Click to edit</div>
            </div>
          )}

          {/* Help text */}
          {!isEditing && (
            <p className="text-xs text-gray-500 text-center">
              Click above to edit and post comment
            </p>
          )}
        </div>

        {/* Skip button - only show when not editing */}
        {post.id && !isEditing && (
          <div className="flex gap-2 pt-4 border-t">
            <Button
              onClick={() => otherProps.onSkip(post.id)}
              variant="outline"
              className="flex-1"
            >
              <SkipForward className="h-4 w-4 mr-2" />
              Skip Post
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "PENDING":
      return "bg-yellow-100 text-yellow-800";
    case "APPROVED":
      return "bg-blue-100 text-blue-800";
    case "QUEUED":
      return "bg-purple-100 text-purple-800";
    case "POSTED":
      return "bg-green-100 text-green-800";
    case "SKIPPED":
      return "bg-gray-100 text-gray-800";
    case "PM_SENT":
      return "bg-indigo-100 text-indigo-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

const getIntentColor = (intent: string) => {
  switch (intent.toLowerCase()) {
    case "service":
      return "bg-blue-100 text-blue-800";
    case "iso":
      return "bg-green-100 text-green-800";
    case "general":
      return "bg-purple-100 text-purple-800";
    case "skip":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

export default CRM;
