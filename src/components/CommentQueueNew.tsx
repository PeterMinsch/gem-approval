import React, { useState, useEffect, useCallback } from "react";
import { debounce } from "lodash";
import { API_BASE_URL } from "../config/api";
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
  post_author_url?: string;
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
      const response = await fetch("${API_BASE_URL}/comments/queue");
      if (response.ok) {
        const data = await response.json();
        console.log("[DEBUG] CommentQueue API response:", data);
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
      const response = await fetch("${API_BASE_URL}/api/templates");
      if (response.ok) {
        const templatesArray = await response.json();
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
      const response = await fetch('${API_BASE_URL}/api/image-packs');
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
      const response = await fetch("${API_BASE_URL}/comments/approve", {
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
        console.log("✅ Comment approved successfully");
        setEditingComment(null);
        setEditedText("");
        setSelectedImages(prev => ({ ...prev, [commentId]: [] }));
        setShowImageSelector(prev => ({ ...prev, [commentId]: false }));
        fetchComments();
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
      const response = await fetch("${API_BASE_URL}/comments/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          comment_id: commentId,
          action: "reject",
          rejection_reason: reason,
        }),
      });

      if (response.ok) {
        fetchComments();
      }
    } catch (error) {
      console.error("Failed to reject comment:", error);
    }
  };

  const startEditing = (comment: QueuedComment) => {
    setEditingComment(comment.id);
    
    let commentToEdit = comment.generated_comment;
    
    if (comment.post_author && comment.generated_comment.includes("Hi there!")) {
      commentToEdit = personalizeTemplate(comment.generated_comment.replace("Hi there!", "Hi {{author_name}}!"), comment.post_author);
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
    
    if (!showImageSelector[commentId] && !detectedCategories[commentId]) {
      loadDetectedCategories(commentId);
    }
  };
  
  const loadDetectedCategories = async (commentId: string) => {
    setLoadingCategories(prev => ({ ...prev, [commentId]: true }));
    try {
      const response = await fetch(`${API_BASE_URL}/api/comments/${commentId}/categories`);
      if (response.ok) {
        const data = await response.json();
        setDetectedCategories(prev => ({
          ...prev,
          [commentId]: data.categories || []
        }));
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
      if (editingComment === commentId && editedText.length >= 10) {
        analyzeEditedText(commentId, editedText);
      }
      
      if (detectedCategories[commentId]?.length > 0) {
        const suggested = getSuggestedImages(detectedCategories[commentId], imagePacks, 2);
        setSelectedImages(prev => ({
          ...prev,
          [commentId]: suggested
        }));
      }
    } else {
      setRealTimeCategories(prev => ({ ...prev, [commentId]: [] }));
    }
  };

  const analyzeEditedText = useCallback(
    debounce(async (commentId: string, text: string) => {
      if (!text || text.length < 10) {
        setRealTimeCategories(prev => ({ ...prev, [commentId]: [] }));
        return;
      }

      setAnalyzingText(prev => ({ ...prev, [commentId]: true }));
      try {
        const response = await fetch('${API_BASE_URL}/api/analyze-text', {
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
    
    if (smartMode[commentId]) {
      analyzeEditedText(commentId, text);
    }
  };

  const personalizeTemplate = (templateText: string, authorName: string | undefined): string => {
    if (!authorName) {
      return templateText.replace(/\{\{author_name\}\}/g, "there");
    }

    const nameParts = authorName.split(" ");
    const titles = ['dr.', 'dr', 'mr.', 'mr', 'mrs.', 'mrs', 'ms.', 'ms', 'miss', 'prof.', 'prof', 'rev.', 'rev'];
    
    let firstName = nameParts[0];
    
    for (let i = 0; i < nameParts.length; i++) {
      const part = nameParts[i].toLowerCase().replace(/[.,]/g, '');
      if (!titles.includes(part)) {
        firstName = nameParts[i];
        break;
      }
    }
    
    firstName = firstName.replace(/[.,]/g, '');
    
    return templateText.replace(/\{\{author_name\}\}/g, firstName || "there");
  };

  const extractFacebookIdFromProfileUrl = (profileUrl: string): string | null => {
    if (!profileUrl || !profileUrl.includes('facebook.com')) {
      return null;
    }

    try {
      if (profileUrl.includes('profile.php?id=')) {
        // Extract numeric ID: facebook.com/profile.php?id=123456789
        const match = profileUrl.match(/id=([^&]+)/);
        return match ? match[1] : null;
      } else {
        // Extract username: facebook.com/john.smith
        const urlParts = profileUrl.split('facebook.com/')[1];
        if (urlParts) {
          const username = urlParts.split('?')[0].split('/')[0];
          return username && !['profile.php', 'photo', 'groups', 'events'].includes(username) ? username : null;
        }
      }
    } catch (error) {
      console.error('Error extracting Facebook ID:', error);
      return null;
    }
    return null;
  };

  const createMessengerLink = (profileUrl: string): string | null => {
    const facebookId = extractFacebookIdFromProfileUrl(profileUrl);
    return facebookId ? `https://www.facebook.com/messages/t/${facebookId}` : null;
  };

  const handleMessageAuthor = (comment: QueuedComment) => {
    if (!comment.post_author_url) {
      console.warn('No author profile URL available for messaging');
      return;
    }

    const messengerUrl = createMessengerLink(comment.post_author_url);
    if (messengerUrl) {
      window.open(messengerUrl, '_blank');
    } else {
      console.error('Could not create Messenger link from profile URL:', comment.post_author_url);
    }
  };

  const handleTemplateSelect = (templateId: string, comment: QueuedComment) => {
    const allTemplates = Object.values(templates).flat();
    const template = allTemplates.find((t) => t.id === templateId);

    if (template) {
      const personalizedText = personalizeTemplate(template.text, comment.post_author);
      setEditedText(personalizedText);
      setSelectedTemplate(templateId);
    }
  };

  const getPostTypeColor = (postType: string) => {
    switch (postType) {
      case "service":
        return "bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg";
      case "iso":
        return "bg-gradient-to-r from-emerald-500 to-green-600 text-white shadow-lg";
      case "general":
        return "bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg";
      default:
        return "bg-gradient-to-r from-slate-500 to-gray-600 text-white shadow-lg";
    }
  };

  const renderPostImages = (comment: QueuedComment, isCompact: boolean = false) => {
    let imageUrls: string[] = [];
    
    if (comment.post_images && comment.post_images.trim() !== "") {
      try {
        const parsed = JSON.parse(comment.post_images);
        imageUrls = Array.isArray(parsed) ? parsed : [parsed];
      } catch {
        imageUrls = [comment.post_images];
      }
    }
    
    imageUrls = imageUrls.filter(url => url && url.trim() !== "");
    
    if (imageUrls.length === 0) return null;
    
    const maxImages = isCompact ? 2 : 3;
    const imageSize = isCompact ? "w-16 h-16" : "w-20 h-20";
    
    return (
      <div className="mb-4">
        <div className="flex gap-2 flex-wrap">
          {imageUrls.slice(0, maxImages).map((imageUrl, imgIndex) => (
            <img
              key={imgIndex}
              src={(() => {
                if (imageUrl.startsWith("http") || imageUrl.startsWith("data:")) return imageUrl;
                if (imageUrl.startsWith("iVBORw0KGgo")) return `data:image/png;base64,${imageUrl}`;
                if (imageUrl.startsWith("/9j/")) return `data:image/jpeg;base64,${imageUrl}`;
                if (!imageUrl.startsWith("http")) return `data:image/jpeg;base64,${imageUrl}`;
                return imageUrl;
              })()}
              alt={`Post image ${imgIndex + 1}`}
              className={`${imageSize} rounded-lg border-2 border-white shadow-sm object-cover hover:scale-105 transition-transform duration-200 cursor-pointer`}
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='${isCompact ? '64' : '80'}' height='${isCompact ? '64' : '80'}' viewBox='0 0 ${isCompact ? '64' : '80'} ${isCompact ? '64' : '80'}'%3E%3Crect width='${isCompact ? '64' : '80'}' height='${isCompact ? '64' : '80'}' fill='%23f3f4f6'/%3E%3Ctext x='${isCompact ? '32' : '40'}' y='${isCompact ? '36' : '45'}' font-family='Arial' font-size='${isCompact ? '8' : '10'}' fill='%23666' text-anchor='middle'%3ENo Image%3C/text%3E%3C/svg%3E`;
              }}
            />
          ))}
          {imageUrls.length > maxImages && (
            <div className={`${imageSize} rounded-lg border-2 border-dashed border-slate-300 bg-slate-100 flex items-center justify-center text-xs font-medium text-slate-600`}>
              +{imageUrls.length - maxImages}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-white to-slate-50/30 border-0 shadow-xl backdrop-blur-sm">
        <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100/50">
          <CardTitle>Loading...</CardTitle>
          <CardDescription>Loading comments...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-white to-slate-50/30 border-0 shadow-xl backdrop-blur-sm">
      <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100/50">
        <CardTitle className="flex items-center gap-3 text-xl font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg">
            <MessageCircle className="h-5 w-5" />
          </div>
          Comment Approval Queue
        </CardTitle>
        <CardDescription className="text-slate-600 font-medium">
          {comments.length} {comments.length === 1 ? 'comment' : 'comments'} waiting for approval
        </CardDescription>
      </CardHeader>
      <CardContent>
        {comments.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
              <MessageCircle className="h-8 w-8 text-slate-400" />
            </div>
            <p className="text-slate-500 text-lg font-medium">No comments in queue</p>
            <p className="text-slate-400 text-sm mt-2">New comments will appear here when they're ready for approval</p>
          </div>
        ) : (
          <div className="space-y-6">
            {comments.map((comment, index) => (
              <Card 
                key={comment.id} 
                className="group relative overflow-hidden bg-gradient-to-br from-white via-slate-50/50 to-white border-0 shadow-lg hover:shadow-xl transition-shadow duration-200 backdrop-blur-sm"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-indigo-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                <div className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-blue-500 via-purple-500 to-indigo-600 group-hover:w-2 transition-[width] duration-200" />
                <CardContent className="relative pt-6 z-10">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      {editingComment === comment.id ? (
                        // UNIFIED EDITING COMPONENT
                        <div className="border-0 rounded-xl bg-gradient-to-br from-white via-slate-50/50 to-white shadow-lg backdrop-blur-sm overflow-hidden">
                          {/* Post Information Section */}
                          <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-slate-50/30 to-white">
                            <div className="flex items-center gap-3 mb-4">
                              <Badge className={`${getPostTypeColor(comment.post_type)} font-semibold px-3 py-1 rounded-full shadow-sm border-0`}>
                                {comment.post_type.toUpperCase()}
                              </Badge>
                              {comment.post_author && (
                                <span className="text-sm font-medium text-slate-600 bg-slate-100 px-3 py-1 rounded-full">
                                  by {comment.post_author}
                                </span>
                              )}
                            </div>
                            
                            {renderPostImages(comment, true)}
                            
                            <div className="mb-4">
                              <h5 className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-2">
                                <div className="w-0.5 h-3 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-full"></div>
                                Original Post
                              </h5>
                              <p className="text-sm leading-relaxed text-slate-700 bg-white/80 p-3 rounded-lg border border-slate-200/30 line-clamp-3">
                                {comment.post_text}
                              </p>
                            </div>
                          </div>
                          
                          {/* Template Selection */}
                          <div className="p-4 border-b border-slate-200/50">
                            <label className="text-sm font-semibold text-slate-700 block mb-3 flex items-center gap-2">
                              <div className="w-1 h-3 bg-gradient-to-b from-emerald-500 to-green-600 rounded-full"></div>
                              Choose Template (Optional)
                            </label>
                            <Select
                              value={selectedTemplate}
                              onValueChange={(value) => handleTemplateSelect(value, comment)}
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
                                      {templateList.map((template) => {
                                        const personalizedPreview = personalizeTemplate(template.text, comment.post_author);
                                        return (
                                          <SelectItem key={template.id} value={template.id}>
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
                          
                          {/* Comment Editor Section */}
                          <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-white to-slate-50/30">
                            <div className="flex items-center justify-between mb-3">
                              <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                                <div className="w-1 h-3 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-full"></div>
                                Custom Comment
                              </label>
                              {analyzingText[comment.id] && (
                                <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-50 px-3 py-1.5 rounded-full animate-pulse">
                                  <div className="animate-spin h-4 w-4 border-2 border-purple-600 border-t-transparent rounded-full"></div>
                                  <span className="font-medium">Analyzing...</span>
                                </div>
                              )}
                            </div>

                            {/* Real-time detected categories */}
                            {smartMode[comment.id] && realTimeCategories[comment.id]?.length > 0 && (
                              <div className="mb-3 p-3 bg-gradient-to-r from-purple-50/50 to-indigo-50/50 rounded-lg border border-purple-200/30">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-sm font-semibold text-purple-700">Live Detected Categories:</span>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {realTimeCategories[comment.id].map(category => (
                                    <Badge key={category} className="text-xs bg-gradient-to-r from-purple-500 to-indigo-600 text-white border-0 shadow-sm px-2 py-1 rounded-full font-medium">
                                      <Sparkles className="h-3 w-3 mr-1" />
                                      {category}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}

                            <Textarea
                              value={editedText}
                              onChange={(e) => handleTextEdit(comment.id, e.target.value)}
                              className="min-h-[120px] resize-none border-0 bg-white/80 backdrop-blur-sm shadow-inner rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:bg-white transition-all duration-200"
                              placeholder="Write your comment here... 

💡 Tip: Enable Smart Mode for real-time category detection and image suggestions!"
                            />
                          </div>

                          {/* Selected Images Preview */}
                          {(selectedImages[comment.id] || []).length > 0 && (
                            <div className="px-4 py-3 border-b border-slate-200/50 bg-gradient-to-r from-blue-50/30 to-indigo-50/30">
                              <div className="flex items-center gap-3 mb-3">
                                <div className="p-1.5 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-600 text-white">
                                  <Image className="h-4 w-4" />
                                </div>
                                <span className="text-sm font-semibold text-slate-700">
                                  Attached Images ({(selectedImages[comment.id] || []).length})
                                </span>
                              </div>
                              <div className="flex gap-2 flex-wrap">
                                {(selectedImages[comment.id] || []).map((image, index) => (
                                  <div key={index} className="relative group">
                                    <img
                                      src={image.startsWith('http') ? image : `${API_BASE_URL}/${image}`}
                                      alt={image}
                                      className="w-16 h-16 object-cover rounded-lg border-2 border-white shadow-md bg-white group-hover:scale-105 transition-transform duration-200"
                                      onError={(e) => {
                                        const target = e.target as HTMLImageElement;
                                        target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%23f3f4f6'/%3E%3Ctext x='32' y='36' font-family='Arial' font-size='8' fill='%23666' text-anchor='middle'%3ENo Image%3C/text%3E%3C/svg%3E";
                                      }}
                                    />
                                    <Button
                                      variant="destructive"
                                      size="sm"
                                      onClick={() => handleImageSelect(comment.id, image)}
                                      className="absolute -top-1 -right-1 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-all duration-200 text-xs bg-red-500 hover:bg-red-600 shadow-lg rounded-full border-2 border-white"
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
                            <div className="border-b border-slate-200/50 bg-gradient-to-br from-slate-50/50 to-white">
                              <div className="p-4">
                                <div className="flex items-center justify-between mb-4">
                                  <div className="flex items-center gap-4">
                                    <h5 className="font-semibold text-sm text-slate-700 flex items-center gap-2">
                                      <div className="w-1 h-4 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-full"></div>
                                      Add Images
                                    </h5>
                                    
                                    {/* Smart Mode Toggle */}
                                    <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200/50">
                                      <Switch
                                        id={`smart-mode-${comment.id}`}
                                        checked={smartMode[comment.id] || false}
                                        onCheckedChange={(checked) => toggleSmartMode(comment.id, checked)}
                                        disabled={loadingCategories[comment.id]}
                                        className="data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-purple-500 data-[state=checked]:to-indigo-600"
                                      />
                                      <Label htmlFor={`smart-mode-${comment.id}`} className="text-sm font-medium cursor-pointer text-slate-700">
                                        <span className="flex items-center gap-2">
                                          <Sparkles className="h-4 w-4 text-purple-500" />
                                          Smart Mode
                                        </span>
                                      </Label>
                                    </div>
                                    
                                    {/* Category count badge */}
                                    {loadingCategories[comment.id] ? (
                                      <Badge className="text-xs bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 border-0 shadow-sm animate-pulse">
                                        Loading...
                                      </Badge>
                                    ) : (() => {
                                      const storedCats = detectedCategories[comment.id] || [];
                                      const liveCats = realTimeCategories[comment.id] || [];
                                      const allCategories = [...new Set([...storedCats, ...liveCats])];
                                      
                                      if (allCategories.length > 0) {
                                        return (
                                          <Badge className="text-xs bg-gradient-to-r from-emerald-500 to-green-600 text-white border-0 shadow-lg px-3 py-1 rounded-full font-semibold">
                                            {allCategories.length} {allCategories.length === 1 ? 'category' : 'categories'}
                                          </Badge>
                                        );
                                      } else if (smartMode[comment.id]) {
                                        return (
                                          <Badge className="text-xs bg-gradient-to-r from-slate-100 to-gray-100 text-slate-600 border-0 shadow-sm px-3 py-1 rounded-full">
                                            No categories detected
                                          </Badge>
                                        );
                                      }
                                      return null;
                                    })()}
                                  </div>
                                  
                                  {/* Auto-select button */}
                                  {(() => {
                                    const storedCats = detectedCategories[comment.id] || [];
                                    const liveCats = realTimeCategories[comment.id] || [];
                                    const allCategories = [...new Set([...storedCats, ...liveCats])];
                                    
                                    if (smartMode[comment.id] && allCategories.length > 0) {
                                      return (
                                        <Button
                                          size="sm"
                                          onClick={() => {
                                            const suggested = getSuggestedImages(allCategories, imagePacks, 2);
                                            setSelectedImages(prev => ({
                                              ...prev,
                                              [comment.id]: suggested
                                            }));
                                          }}
                                          className="text-sm bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white shadow-lg border-0 px-4 py-2 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl"
                                        >
                                          <Sparkles className="h-4 w-4 mr-2" />
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
                          <div className="p-4 flex items-center justify-between bg-gradient-to-r from-slate-50/50 to-white border-t border-slate-200/50">
                            <div className="flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => toggleImageSelector(comment.id)}
                                className="h-9 px-4 text-slate-600 hover:text-slate-800 hover:bg-gradient-to-r hover:from-slate-100 hover:to-slate-50 rounded-lg transition-all duration-200 border border-transparent hover:border-slate-200"
                              >
                                <Image className="h-4 w-4 mr-2" />
                                {showImageSelector[comment.id] ? 'Hide' : 'Add'} Images
                                {(selectedImages[comment.id] || []).length > 0 && (
                                  <span className="ml-2 text-xs bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-2 py-0.5 rounded-full font-medium shadow-sm">
                                    {(selectedImages[comment.id] || []).length}
                                  </span>
                                )}
                              </Button>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={cancelEditing}
                                className="h-9 px-4 text-slate-600 hover:text-slate-800 hover:bg-gradient-to-r hover:from-slate-100 hover:to-slate-50 rounded-lg transition-all duration-200 border border-transparent hover:border-slate-200"
                              >
                                Cancel
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleApprove(comment.id)}
                                className="bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white h-9 px-6 shadow-lg border-0 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl"
                              >
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Post to Facebook
                              </Button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        // UNIFIED READ-ONLY COMPONENT
                        <div className="border-0 rounded-xl bg-gradient-to-br from-white via-slate-50/50 to-white shadow-lg backdrop-blur-sm overflow-hidden">
                          {/* Post Information Section */}
                          <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-slate-50/30 to-white">
                            <div className="flex items-center gap-3 mb-4">
                              <Badge className={`${getPostTypeColor(comment.post_type)} font-semibold px-3 py-1 rounded-full shadow-sm border-0`}>
                                {comment.post_type.toUpperCase()}
                              </Badge>
                              {comment.post_author && (
                                <span className="text-sm font-medium text-slate-600 bg-slate-100 px-3 py-1 rounded-full">
                                  by {comment.post_author}
                                </span>
                              )}
                            </div>
                            
                            {renderPostImages(comment)}
                            
                            <div className="mb-4">
                              <h5 className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-2">
                                <div className="w-0.5 h-3 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-full"></div>
                                Original Post
                              </h5>
                              <p className="text-sm leading-relaxed text-slate-700 bg-white/80 p-3 rounded-lg border border-slate-200/30">
                                {comment.post_text}
                              </p>
                            </div>
                          </div>
                          
                          {/* Generated Comment */}
                          <div className="p-4 bg-gradient-to-r from-blue-50/30 to-indigo-50/30">
                            <h5 className="text-xs font-semibold text-slate-600 mb-3 flex items-center gap-2">
                              <div className="w-0.5 h-3 bg-gradient-to-b from-purple-500 to-indigo-600 rounded-full"></div>
                              Generated Comment
                            </h5>
                            <p className="text-sm leading-relaxed text-slate-700 font-medium bg-white/60 p-3 rounded-lg">
                              {comment.generated_comment}
                            </p>
                          </div>
                        </div>
                      )}

                      <div className="flex items-center gap-3 text-xs text-slate-500 bg-slate-50/50 px-3 py-2 rounded-lg mt-4">
                        <span className="font-medium">
                          Created: {new Date(comment.created_at).toLocaleString()}
                        </span>
                        {comment.post_engagement && (
                          <span className="px-2 py-1 bg-slate-200/50 rounded-full">• {comment.post_engagement}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col gap-3 ml-6">
                      <Button
                        size="sm"
                        onClick={() => window.open(comment.post_url, "_blank")}
                        className="bg-gradient-to-r from-slate-100 to-slate-200 hover:from-slate-200 hover:to-slate-300 text-slate-700 border-0 shadow-sm hover:shadow-md transition-all duration-200 rounded-lg font-medium"
                      >
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View Post
                      </Button>

                      {comment.post_author_url && comment.post_author && comment.post_author !== "User" && (
                        <Button
                          size="sm"
                          onClick={() => handleMessageAuthor(comment)}
                          className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white border-0 shadow-sm hover:shadow-md transition-all duration-200 rounded-lg font-medium"
                          title={`Send message to ${comment.post_author} on Facebook Messenger`}
                        >
                          <MessageCircle className="h-4 w-4 mr-2" />
                          Message {comment.post_author?.split(' ')[0] || 'Author'}
                        </Button>
                      )}

                      {editingComment !== comment.id && (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => startEditing(comment)}
                            className="bg-gradient-to-r from-blue-100 to-indigo-100 hover:from-blue-200 hover:to-indigo-200 text-blue-700 border-0 shadow-sm hover:shadow-md transition-all duration-200 rounded-lg font-medium"
                          >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleApprove(comment.id)}
                            className="bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white shadow-lg border-0 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl"
                          >
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            onClick={() =>
                              handleReject(comment.id, "Rejected by user")
                            }
                            className="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-lg border-0 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl"
                          >
                            <XCircle className="h-4 w-4 mr-2" />
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