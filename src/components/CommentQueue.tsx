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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  CheckCircle,
  XCircle,
  Edit,
  ExternalLink,
  MessageCircle,
  Image,
  ChevronDown,
  ChevronRight,
  //Template,
} from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";

interface QueuedComment {
  id: string;
  post_url: string;
  post_text: string;
  generated_comment: string;
  post_type: string;
  post_author?: string;
  post_engagement?: string;
  post_images?: string;
  status: string;
  created_at: string;
}

interface Template {
  id: string;
  text: string;
  post_type: string;
}

interface TemplateResponse {
  success: boolean;
  templates: Record<string, Template[]>;
  error?: string;
}

interface ImagePack {
  id: string;
  name: string;
  images: { filename: string; description: string }[];
}

export const CommentQueue: React.FC = () => {
  const [comments, setComments] = useState<QueuedComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingComment, setEditingComment] = useState<string | null>(null);
  const [editedText, setEditedText] = useState("");
  const [templates, setTemplates] = useState<Record<string, Template[]>>({});
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [showTemplateSelector, setShowTemplateSelector] = useState<
    string | null
  >(null);
  const [selectedImages, setSelectedImages] = useState<Record<string, string[]>>({});
  const [showImageSelector, setShowImageSelector] = useState<Record<string, boolean>>({});
  const [imagePacks, setImagePacks] = useState<ImagePack[]>([]);

  useEffect(() => {
    fetchComments();
    fetchTemplates();
    fetchImagePacks();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchComments, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchComments = async () => {
    try {
      const response = await fetch("http://localhost:8000/comments/queue");
      if (response.ok) {
        const data = await response.json();
        // Debug: log post_images for each comment
        console.log("[DEBUG] CommentQueue API response:", data);
        data.forEach((comment: any) => {
          console.log(
            `[DEBUG] comment.id=${comment.id} post_images=`,
            comment.post_images
          );
        });
        setComments(data);
      }
    } catch (error) {
      console.error("Failed to fetch comments:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/templates");
      if (response.ok) {
        const templatesArray = await response.json();
        // Convert array to grouped format by category
        const grouped = templatesArray.reduce((acc: Record<string, Template[]>, template: any) => {
          const category = template.category || 'GENERIC';
          if (!acc[category]) {
            acc[category] = [];
          }
          acc[category].push({
            id: template.id,
            text: template.body,
            post_type: category.toLowerCase()
          });
          return acc;
        }, {});
        setTemplates(grouped);
      }
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    }
  };

  const fetchImagePacks = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/image-packs');
      if (response.ok) {
        const packs = await response.json();
        setImagePacks(packs);
      } else {
        console.error('Failed to fetch image packs');
      }
    } catch (error) {
      console.error('Error loading image packs:', error);
    }
  };

  const handleApprove = async (commentId: string) => {
    try {
      const images = selectedImages[commentId] || [];
      const response = await fetch("http://localhost:8000/comments/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          comment_id: commentId,
          action: "approve",
          edited_comment: editedText || undefined,
          images: images.length > 0 ? images : undefined,
        }),
      });

      if (response.ok) {
        const result = await response.json();

        // Show success message with posting status
        if (result.message.includes("posted successfully")) {
          // Success toast would go here if you have a toast system
          console.log("✅ Comment approved and posted to Facebook!");
        } else if (result.message.includes("posting failed")) {
          console.warn("⚠️ Comment approved but posting failed");
          // Warning toast would go here
        } else if (result.message.includes("posting encountered an error")) {
          console.warn("⚠️ Comment approved but posting had an error");
          // Warning toast would go here
        } else {
          console.log("✅ Comment approved successfully");
        }

        setEditingComment(null);
        setEditedText("");
        setSelectedImages(prev => ({ ...prev, [commentId]: [] }));
        setShowImageSelector(prev => ({ ...prev, [commentId]: false }));
        fetchComments(); // Refresh the list
      } else {
        const error = await response.json();
        console.error("Failed to approve comment:", error);
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
          rejection_reason: reason,
        }),
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
    
    // Check if the generated comment needs personalization
    let commentToEdit = comment.generated_comment;
    
    // If we have an author name and the comment contains "Hi there!", personalize it
    if (comment.post_author && comment.generated_comment.includes("Hi there!")) {
      // Replace "Hi there!" with personalized greeting
      commentToEdit = personalizeTemplate(comment.generated_comment.replace("Hi there!", "Hi {{author_name}}!"), comment.post_author);
      console.log('Personalized initial comment:', { 
        original: comment.generated_comment.substring(0, 50),
        personalized: commentToEdit.substring(0, 50),
        author: comment.post_author
      });
    }
    
    setEditedText(commentToEdit);
    setShowTemplateSelector(comment.id);
    setSelectedTemplate("");
  };

  const cancelEditing = () => {
    setEditingComment(null);
    setEditedText("");
    setShowTemplateSelector(null);
    setSelectedTemplate("");
  };

  const handleImageSelect = (commentId: string, filename: string) => {
    setSelectedImages(prev => {
      const currentImages = prev[commentId] || [];
      const newImages = currentImages.includes(filename)
        ? currentImages.filter(img => img !== filename)
        : [...currentImages, filename];
      return { ...prev, [commentId]: newImages };
    });
  };

  const toggleImageSelector = (commentId: string) => {
    setShowImageSelector(prev => ({
      ...prev,
      [commentId]: !prev[commentId]
    }));
  };

  // Helper function to personalize template text with first name
  const personalizeTemplate = (templateText: string, authorName: string | undefined): string => {
    if (!authorName) {
      return templateText.replace(/\{\{author_name\}\}/g, "there");
    }

    // Extract first name, skipping common titles (matching backend logic)
    const nameParts = authorName.split(" ");
    const titles = ['dr.', 'dr', 'mr.', 'mr', 'mrs.', 'mrs', 'ms.', 'ms', 'miss', 'prof.', 'prof', 'rev.', 'rev'];
    
    let firstName = nameParts[0];
    
    // Skip titles to find the actual first name
    for (let i = 0; i < nameParts.length; i++) {
      const part = nameParts[i].toLowerCase().replace(/[.,]/g, '');
      if (!titles.includes(part)) {
        firstName = nameParts[i];
        break;
      }
    }
    
    // Clean up the first name (remove punctuation)
    firstName = firstName.replace(/[.,]/g, '');
    
    return templateText.replace(/\{\{author_name\}\}/g, firstName || "there");
  };

  const handleTemplateSelect = (templateId: string, comment: QueuedComment) => {
    const allTemplates = Object.values(templates).flat();
    const template = allTemplates.find((t) => t.id === templateId);

    if (template) {
      // Debug logging to see what's happening
      console.log('Template selection:', {
        templateId,
        originalTemplate: template.text.substring(0, 100),
        authorName: comment.post_author,
        hasAuthor: !!comment.post_author
      });

      // Use the helper function to personalize the template
      const personalizedText = personalizeTemplate(template.text, comment.post_author);
      console.log('Personalized result:', personalizedText.substring(0, 100));
      
      setEditedText(personalizedText);
      setSelectedTemplate(templateId);
    }
  };

  const getPostTypeColor = (postType: string) => {
    switch (postType) {
      case "service":
        return "bg-blue-100 text-blue-800";
      case "iso":
        return "bg-green-100 text-green-800";
      case "general":
        return "bg-purple-100 text-purple-800";
      default:
        return "bg-gray-100 text-gray-800";
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
                      {/* Display post images if available */}
                      {(() => {
                        let imageUrls: string[] = [];

                        // Parse post_images - could be JSON string array or single string
                        if (
                          comment.post_images &&
                          comment.post_images.trim() !== ""
                        ) {
                          try {
                            // Try parsing as JSON array first
                            const parsed = JSON.parse(comment.post_images);
                            imageUrls = Array.isArray(parsed)
                              ? parsed
                              : [parsed];
                          } catch {
                            // If not JSON, treat as single URL/base64 string
                            imageUrls = [comment.post_images];
                          }
                        }

                        // Filter out empty/invalid URLs
                        imageUrls = imageUrls.filter(
                          (url) => url && url.trim() !== ""
                        );

                        if (imageUrls.length === 0) return null;

                        return (
                          <div className="mb-3">
                            <div className="flex gap-2 flex-wrap">
                              {imageUrls.slice(0, 3).map((imageUrl, index) => (
                                <img
                                  key={index}
                                  src={(() => {
                                    // Handle different image URL formats
                                    if (
                                      imageUrl.startsWith("http") ||
                                      imageUrl.startsWith("data:")
                                    ) {
                                      return imageUrl;
                                    }
                                    // PNG base64 usually starts with iVBORw0KGgo
                                    if (imageUrl.startsWith("iVBORw0KGgo")) {
                                      return `data:image/png;base64,${imageUrl}`;
                                    }
                                    // JPEG base64 usually starts with /9j/
                                    if (imageUrl.startsWith("/9j/")) {
                                      return `data:image/jpeg;base64,${imageUrl}`;
                                    }
                                    // Default to jpeg if unknown base64
                                    if (!imageUrl.startsWith("http")) {
                                      return `data:image/jpeg;base64,${imageUrl}`;
                                    }
                                    return imageUrl;
                                  })()}
                                  alt={`Post image ${index + 1}`}
                                  className="w-20 h-20 rounded border border-gray-200 object-cover"
                                  onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    target.src =
                                      "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Crect width='80' height='80' fill='%23f3f4f6'/%3E%3Ctext x='40' y='45' font-family='Arial' font-size='10' fill='%23666' text-anchor='middle'%3ENo Image%3C/text%3E%3C/svg%3E";
                                    target.style.objectFit = "cover";
                                  }}
                                />
                              ))}
                              {imageUrls.length > 3 && (
                                <div className="w-20 h-20 rounded border border-gray-200 bg-gray-100 flex items-center justify-center text-xs text-gray-500">
                                  +{imageUrls.length - 3}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })()}

                      <div className="mb-3">
                        <h4 className="font-medium text-sm text-gray-700 mb-1">
                          Original Post:
                        </h4>
                        <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                          {comment.post_text}
                        </p>
                      </div>

                      <div className="mb-3">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium text-sm text-gray-700">
                            Generated Comment:
                          </h4>
                          {editingComment === comment.id && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => toggleImageSelector(comment.id)}
                              className="h-7 px-2"
                            >
                              <Image className="h-3 w-3 mr-1" />
                              Images ({(selectedImages[comment.id] || []).length})
                            </Button>
                          )}
                        </div>
                        {editingComment === comment.id ? (
                          <div className="space-y-3">
                            {/* Image Pack Selection */}
                            {showImageSelector[comment.id] && (
                              <div className="border rounded-md p-3 bg-muted/30 space-y-3">
                                <h5 className="font-medium text-sm">Select Images to Attach:</h5>
                                <div className="space-y-2">
                                  {imagePacks.map(pack => (
                                    <Collapsible key={pack.id}>
                                      <CollapsibleTrigger asChild>
                                        <Button variant="ghost" className="justify-between h-8 w-full px-2 text-left">
                                          <span className="text-sm font-medium">{pack.name}</span>
                                          <ChevronRight className="h-4 w-4" />
                                        </Button>
                                      </CollapsibleTrigger>
                                      <CollapsibleContent className="space-y-1 pl-4">
                                        {pack.images.map(image => (
                                          <label 
                                            key={image.filename}
                                            className="flex items-center space-x-2 cursor-pointer hover:bg-accent/50 rounded p-1"
                                          >
                                            <input
                                              type="checkbox"
                                              checked={(selectedImages[comment.id] || []).includes(image.filename)}
                                              onChange={() => handleImageSelect(comment.id, image.filename)}
                                              className="rounded border-2"
                                            />
                                            <div className="text-sm">
                                              <div className="font-medium">{image.filename.split('/').pop()}</div>
                                              <div className="text-muted-foreground text-xs">{image.description}</div>
                                            </div>
                                          </label>
                                        ))}
                                      </CollapsibleContent>
                                    </Collapsible>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Selected Images Display */}
                            {(selectedImages[comment.id] || []).length > 0 && (
                              <div className="space-y-2">
                                <h5 className="font-medium text-sm">Selected Images:</h5>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                  {(selectedImages[comment.id] || []).map((image, index) => (
                                    <div key={index} className="relative group">
                                      <img
                                        src={image.startsWith('http') ? image : `http://localhost:8000/${image}`}
                                        alt={image}
                                        className="w-full h-auto max-h-32 object-contain rounded border border-gray-200 bg-gray-50"
                                        onError={(e) => {
                                          const target = e.target as HTMLImageElement;
                                          target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='80' viewBox='0 0 120 80'%3E%3Crect width='120' height='80' fill='%23f3f4f6'/%3E%3Ctext x='60' y='45' font-family='Arial' font-size='10' fill='%23666' text-anchor='middle'%3ENo Image%3C/text%3E%3C/svg%3E";
                                        }}
                                      />
                                      <Button
                                        variant="destructive"
                                        size="sm"
                                        onClick={() => handleImageSelect(comment.id, image)}
                                        className="absolute top-1 right-1 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                                      >
                                        ×
                                      </Button>
                                      <div className="mt-1 text-xs text-center text-muted-foreground truncate">
                                        {image.split('/').pop()}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">
                                Choose Template (Optional):
                              </label>
                              <Select
                                value={selectedTemplate}
                                onValueChange={(value) =>
                                  handleTemplateSelect(value, comment)
                                }
                              >
                                <SelectTrigger className="w-full">
                                  <SelectValue placeholder="Select a template or write custom comment below..." />
                                </SelectTrigger>
                                <SelectContent>
                                  {Object.entries(templates).map(
                                    ([postType, templateList]) => (
                                      <React.Fragment key={postType}>
                                        <div className="px-2 py-1 text-xs font-semibold text-gray-500 uppercase">
                                          {postType} Templates
                                        </div>
                                        {templateList.map((template, index) => {
                                          // Show personalized version in dropdown
                                          const personalizedPreview = personalizeTemplate(template.text, comment.post_author);
                                          return (
                                            <SelectItem
                                              key={template.id}
                                              value={template.id}
                                            >
                                              {personalizedPreview.substring(0, 80)}...
                                            </SelectItem>
                                          );
                                        })}
                                      </React.Fragment>
                                    )
                                  )}
                                </SelectContent>
                              </Select>
                            </div>
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">
                                Custom Comment:
                              </label>
                              <Textarea
                                value={editedText}
                                onChange={(e) => setEditedText(e.target.value)}
                                className="min-h-[80px]"
                                placeholder="Edit the comment or paste a template from above..."
                              />
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm bg-blue-50 p-2 rounded">
                            {comment.generated_comment}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>
                          Created:{" "}
                          {new Date(comment.created_at).toLocaleString()}
                        </span>
                        {comment.post_engagement && (
                          <span>• {comment.post_engagement}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 ml-4">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => window.open(comment.post_url, "_blank")}
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
                            Save & Post to Facebook
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
                            Post to Facebook
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              handleReject(comment.id, "Rejected by user")
                            }
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
