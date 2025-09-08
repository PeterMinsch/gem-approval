import React, { useState, useEffect, useCallback } from "react";
import { debounce } from "lodash";
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
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import {
  CheckCircle,
  XCircle,
  Edit,
  ExternalLink,
  MessageCircle,
  Image,
  Sparkles,
} from "lucide-react";
import { ImageGallery } from "./ImageGallery";
import { getSuggestedImages } from "@/services/categoryMapper";

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
  // Smart categorization state
  const [smartMode, setSmartMode] = useState<Record<string, boolean>>({});
  const [detectedCategories, setDetectedCategories] = useState<Record<string, string[]>>({});
  const [loadingCategories, setLoadingCategories] = useState<Record<string, boolean>>({});
  // Real-time text analysis state
  const [analyzingText, setAnalyzingText] = useState<Record<string, boolean>>({});
  const [realTimeCategories, setRealTimeCategories] = useState<Record<string, string[]>>({});

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
    console.log('[DEBUG] toggleImageSelector:', { commentId, currentState: showImageSelector[commentId] });
    setShowImageSelector(prev => ({
      ...prev,
      [commentId]: !prev[commentId]
    }));
    
    // Load categories when opening image selector for the first time
    if (!showImageSelector[commentId] && !detectedCategories[commentId]) {
      console.log('[DEBUG] Loading categories for comment:', commentId);
      loadDetectedCategories(commentId);
    }
  };
  
  const loadDetectedCategories = async (commentId: string) => {
    console.log('[DEBUG] loadDetectedCategories started for:', commentId);
    setLoadingCategories(prev => ({ ...prev, [commentId]: true }));
    try {
      const response = await fetch(`http://localhost:8000/api/comments/${commentId}/categories`);
      console.log('[DEBUG] API response status:', response.status, response.ok);
      if (response.ok) {
        const data = await response.json();
        console.log('[DEBUG] API response data:', data);
        setDetectedCategories(prev => ({
          ...prev,
          [commentId]: data.categories || []
        }));
        console.log('[DEBUG] Categories stored for comment', commentId, ':', data.categories || []);
        // Enable smart mode by default if categories are detected
        if (data.categories && data.categories.length > 0) {
          setSmartMode(prev => ({ ...prev, [commentId]: true }));
        }
      }
    } catch (error) {
      console.error(`Error loading categories for comment ${commentId}:`, error);
    } finally {
      setLoadingCategories(prev => ({ ...prev, [commentId]: false }));
    }
  };
  
  const handleBulkImageSelect = (commentId: string, filenames: string[]) => {
    setSelectedImages(prev => ({
      ...prev,
      [commentId]: filenames
    }));
  };
  
  const toggleSmartMode = (commentId: string, enabled: boolean) => {
    setSmartMode(prev => ({ ...prev, [commentId]: enabled }));
    
    if (enabled) {
      // Trigger analysis on existing edited text if available
      if (editingComment === commentId && editedText.length >= 10) {
        analyzeEditedText(commentId, editedText);
      }
      
      // Auto-select suggested images when enabling smart mode
      if (detectedCategories[commentId]?.length > 0) {
        const suggested = getSuggestedImages(detectedCategories[commentId], imagePacks, 2);
        setSelectedImages(prev => ({
          ...prev,
          [commentId]: suggested
        }));
      }
    } else {
      // Clear real-time categories when disabling smart mode
      setRealTimeCategories(prev => ({ ...prev, [commentId]: [] }));
    }
  };

  // Real-time text analysis for edited comments
  const analyzeEditedText = useCallback(
    debounce(async (commentId: string, text: string) => {
      if (!text || text.length < 10) {
        setRealTimeCategories(prev => ({ ...prev, [commentId]: [] }));
        return;
      }

      setAnalyzingText(prev => ({ ...prev, [commentId]: true }));
      try {
        const response = await fetch('http://localhost:8000/api/analyze-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        
        if (response.ok) {
          const data = await response.json();
          setRealTimeCategories(prev => ({ 
            ...prev, 
            [commentId]: data.categories || [] 
          }));
          console.log('[DEBUG] Real-time analysis for comment', commentId, ':', data.categories);
        }
      } catch (error) {
        console.error('Real-time text analysis failed:', error);
        setRealTimeCategories(prev => ({ ...prev, [commentId]: [] }));
      } finally {
        setAnalyzingText(prev => ({ ...prev, [commentId]: false }));
      }
    }, 800),
    []
  );

  const handleTextEdit = (commentId: string, text: string) => {
    setEditedText(text);
    
    // Trigger real-time analysis if smart mode is enabled
    if (smartMode[commentId]) {
      analyzeEditedText(commentId, text);
    }
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
                        <div className="mb-1">
                          <h4 className="font-medium text-sm text-gray-700">
                            Generated Comment:
                          </h4>
                        </div>
                        {editingComment === comment.id ? (
                          <div className="space-y-3">
                            {/* Template Selection */}
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

                            {/* Integrated Comment Composer */}
                            <div className="border rounded-lg bg-background/50">
                              <div className="p-3 border-b">
                                <div className="flex items-center justify-between mb-2">
                                  <label className="text-sm font-medium text-gray-700">
                                    Custom Comment:
                                  </label>
                                  {analyzingText[comment.id] && (
                                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                      <div className="animate-spin h-3 w-3 border border-primary border-t-transparent rounded-full"></div>
                                      Analyzing...
                                    </div>
                                  )}
                                </div>

                                {/* Real-time detected categories */}
                                {smartMode[comment.id] && realTimeCategories[comment.id]?.length > 0 && (
                                  <div className="mb-2 flex items-center gap-2 flex-wrap">
                                    <span className="text-xs font-medium text-muted-foreground">Live detected:</span>
                                    {realTimeCategories[comment.id].map(category => (
                                      <Badge key={category} variant="secondary" className="text-xs">
                                        <Sparkles className="h-2 w-2 mr-1" />
                                        {category}
                                      </Badge>
                                    ))}
                                  </div>
                                )}

                                <Textarea
                                  value={editedText}
                                  onChange={(e) => handleTextEdit(comment.id, e.target.value)}
                                  className="min-h-[120px] resize-none"
                                  placeholder="Write your comment here... 

💡 Tip: Enable Smart Mode for real-time category detection and image suggestions!"
                                />
                              </div>

                              {/* Selected Images Preview - Integrated within composer */}
                              {(selectedImages[comment.id] || []).length > 0 && (
                                <div className="px-3 py-2 border-b bg-gray-50/50">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Image className="h-4 w-4 text-gray-600" />
                                    <span className="text-sm font-medium text-gray-700">
                                      Attached Images ({(selectedImages[comment.id] || []).length})
                                    </span>
                                  </div>
                                  <div className="flex gap-2 flex-wrap">
                                    {(selectedImages[comment.id] || []).map((image, index) => (
                                      <div key={index} className="relative group">
                                        <img
                                          src={image.startsWith('http') ? image : `http://localhost:8000/${image}`}
                                          alt={image}
                                          className="w-16 h-16 object-cover rounded border border-gray-200 bg-white"
                                          onError={(e) => {
                                            const target = e.target as HTMLImageElement;
                                            target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%23f3f4f6'/%3E%3Ctext x='32' y='36' font-family='Arial' font-size='8' fill='%23666' text-anchor='middle'%3ENo Image%3C/text%3E%3C/svg%3E";
                                          }}
                                        />
                                        <Button
                                          variant="destructive"
                                          size="sm"
                                          onClick={() => handleImageSelect(comment.id, image)}
                                          className="absolute -top-1 -right-1 h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-xs"
                                        >
                                          ×
                                        </Button>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Inline Expandable Gallery */}
                              {showImageSelector[comment.id] && (
                                <div className="border-b">
                                  <div className="p-3">
                                    <div className="flex items-center justify-between mb-3">
                                      <div className="flex items-center gap-3">
                                        <h5 className="font-medium text-sm text-gray-700">Add Images</h5>
                                        
                                        {/* Smart Mode Toggle - Now in gallery */}
                                        <div className="flex items-center gap-2">
                                          <Switch
                                            id={`smart-mode-${comment.id}`}
                                            checked={smartMode[comment.id] || false}
                                            onCheckedChange={(checked) => toggleSmartMode(comment.id, checked)}
                                            disabled={loadingCategories[comment.id]}
                                          />
                                          <Label htmlFor={`smart-mode-${comment.id}`} className="text-xs cursor-pointer">
                                            <span className="flex items-center gap-1">
                                              <Sparkles className="h-3 w-3" />
                                              Smart Mode
                                            </span>
                                          </Label>
                                        </div>
                                        
                                        {/* Category count badge - Combined stored and real-time */}
                                        {loadingCategories[comment.id] ? (
                                          <Badge variant="outline" className="text-xs">
                                            Loading...
                                          </Badge>
                                        ) : (() => {
                                          // Combine both stored and real-time categories for accurate count
                                          const storedCats = detectedCategories[comment.id] || [];
                                          const liveCats = realTimeCategories[comment.id] || [];
                                          const allCategories = [...new Set([...storedCats, ...liveCats])]; // Unique categories
                                          
                                          if (allCategories.length > 0) {
                                            return (
                                              <Badge variant="secondary" className="text-xs">
                                                {allCategories.length} categories
                                              </Badge>
                                            );
                                          } else if (smartMode[comment.id]) {
                                            return (
                                              <Badge variant="outline" className="text-xs text-muted-foreground">
                                                No categories detected
                                              </Badge>
                                            );
                                          }
                                          return null;
                                        })()}
                                      </div>
                                      
                                      {/* Auto-select button - Works with both stored and real-time categories */}
                                      {(() => {
                                        const storedCats = detectedCategories[comment.id] || [];
                                        const liveCats = realTimeCategories[comment.id] || [];
                                        const allCategories = [...new Set([...storedCats, ...liveCats])];
                                        
                                        if (smartMode[comment.id] && allCategories.length > 0) {
                                          return (
                                            <Button
                                              variant="outline"
                                              size="sm"
                                              onClick={() => {
                                                const suggested = getSuggestedImages(allCategories, imagePacks, 2);
                                                setSelectedImages(prev => ({
                                                  ...prev,
                                                  [comment.id]: suggested
                                                }));
                                              }}
                                              className="text-xs"
                                            >
                                              <Sparkles className="h-3 w-3 mr-1" />
                                              Auto-Select
                                            </Button>
                                          );
                                        }
                                        return null;
                                      })()}
                                    </div>
                                    
                                    <ImageGallery
                                      categories={smartMode[comment.id] ? (
                                        realTimeCategories[comment.id]?.length > 0 
                                          ? realTimeCategories[comment.id] 
                                          : (detectedCategories[comment.id] || [])
                                      ) : []}
                                      imagePacks={imagePacks}
                                      selectedImages={selectedImages[comment.id] || []}
                                      onImageSelect={(filename) => handleImageSelect(comment.id, filename)}
                                      onBulkSelect={(filenames) => handleBulkImageSelect(comment.id, filenames)}
                                      smartMode={smartMode[comment.id] || false}
                                      loading={loadingCategories[comment.id] || false}
                                    />
                                  </div>
                                </div>
                              )}

                              {/* Integrated Action Bar */}
                              <div className="p-3 flex items-center justify-between bg-gray-50/30">
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => toggleImageSelector(comment.id)}
                                    className="h-8 px-3 text-gray-600 hover:text-gray-800"
                                  >
                                    <Image className="h-4 w-4 mr-1" />
                                    {showImageSelector[comment.id] ? 'Hide' : 'Add'} Images
                                    {(selectedImages[comment.id] || []).length > 0 && (
                                      <span className="ml-1 text-xs bg-blue-100 text-blue-800 px-1 rounded">
                                        {(selectedImages[comment.id] || []).length}
                                      </span>
                                    )}
                                  </Button>
                                </div>
                                
                                <div className="flex items-center gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={cancelEditing}
                                    className="h-8"
                                  >
                                    Cancel
                                  </Button>
                                  <Button
                                    size="sm"
                                    onClick={() => handleApprove(comment.id)}
                                    className="bg-green-600 hover:bg-green-700 h-8"
                                  >
                                    <CheckCircle className="h-4 w-4 mr-1" />
                                    Post to Facebook
                                  </Button>
                                </div>
                              </div>
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

                      {editingComment !== comment.id && (
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
