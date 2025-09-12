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
import { MessageGenerationSidebar } from "./MessageGenerationSidebar";
import { CommentGenerationSidebar } from "./CommentGenerationSidebar";
import { getSuggestedImages } from "@/services/categoryMapper";
import { useMessageGeneration } from "@/hooks/useMessageGeneration";
import { executeEnhancedSmartLauncher } from "@/utils/messageUtils";

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

// Utility functions for Facebook Messenger integration
const extractFacebookIdFromProfileUrl = (profileUrl: string): string | null => {
  console.log("🔍 Extracting Facebook ID from URL:", profileUrl);

  if (!profileUrl) {
    console.log("❌ No profile URL provided");
    return null;
  }

  // Handle group-based profile URLs first
  // Pattern: /groups/[groupid]/user/[userid]/
  if (profileUrl.includes("/groups/") && profileUrl.includes("/user/")) {
    console.log("🎯 Detected group-based profile URL");
    const userMatch = profileUrl.match(/\/user\/([^/?]+)/);
    if (userMatch) {
      console.log("✅ Extracted user ID from group URL:", userMatch[1]);
      return userMatch[1];
    } else {
      console.log("❌ Group URL pattern matched but failed to extract user ID");
    }
  }

  // Extract user ID from other Facebook URL formats
  const patterns = [
    {
      pattern: /facebook\.com\/profile\.php\?id=(\d+)/,
      name: "profile.php?id format",
    },
    {
      pattern: /facebook\.com\/([a-zA-Z0-9._-]+)(?:\/|$)/,
      name: "direct username format",
    },
    {
      pattern: /facebook\.com\/people\/[^/]+\/(\d+)/,
      name: "people/name/id format",
    },
  ];

  for (let i = 0; i < patterns.length; i++) {
    const { pattern, name } = patterns[i];
    console.log(`🔍 Trying pattern ${i + 1} (${name}):`, pattern);
    const match = profileUrl.match(pattern);
    if (match) {
      console.log(`✅ Pattern ${i + 1} matched! Extracted ID:`, match[1]);
      return match[1];
    } else {
      console.log(`❌ Pattern ${i + 1} (${name}) no match`);
    }
  }

  console.log("❌ No patterns matched for URL:", profileUrl);
  return null;
};

const createMessengerLink = (profileUrl: string): string | null => {
  const userId = extractFacebookIdFromProfileUrl(profileUrl);
  if (!userId) return null;

  return `https://www.facebook.com/messages/t/${userId}`;
};

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
  const [selectedImages, setSelectedImages] = useState<
    Record<string, string[]>
  >({});
  const [showImageSelector, setShowImageSelector] = useState<
    Record<string, boolean>
  >({});
  const [imagePacks, setImagePacks] = useState<ImagePack[]>([]);
  // Smart categorization state
  const [commentSmartMode, setCommentSmartMode] = useState<Record<string, boolean>>({});
  const [messageSmartMode, setMessageSmartMode] = useState<Record<string, boolean>>({});

  // Smart Launcher state
  const {
    generateMessage,
    isGenerating,
    error: messageError,
    clearError,
  } = useMessageGeneration();
  const [generatedMessages, setGeneratedMessages] = useState<
    Record<string, string>
  >({});
  const [smartLauncherNotifications, setSmartLauncherNotifications] = useState<
    Record<string, string>
  >({});
  const [detectedCategories, setDetectedCategories] = useState<
    Record<string, string[]>
  >({});
  const [loadingCategories, setLoadingCategories] = useState<
    Record<string, boolean>
  >({});
  // Real-time text analysis state
  const [analyzingText, setAnalyzingText] = useState<Record<string, boolean>>(
    {}
  );
  const [realTimeCategories, setRealTimeCategories] = useState<
    Record<string, string[]>
  >({});
  // Automation method preference
  const [automationMethod, setAutomationMethod] = useState<
    "clipboard" | "selenium"
  >("selenium");
  // User-selectable images for Generate & Send Message
  const [showUserImageSelector, setShowUserImageSelector] = useState<
    Record<string, boolean>
  >({});
  const [userSelectedImages, setUserSelectedImages] = useState<
    Record<string, string[]>
  >({});
  const [availableImages, setAvailableImages] = useState<ImagePack[]>([]);

  // NEW: Message preview functionality
  const [showMessagePreview, setShowMessagePreview] = useState<
    Record<string, boolean>
  >({});
  const [editableMessages, setEditableMessages] = useState<
    Record<string, string>
  >({});
  const [includePostImage, setIncludePostImage] = useState<
    Record<string, boolean>
  >({});

  useEffect(() => {
    fetchComments();
    fetchTemplates();
    fetchImagePacks();
    fetchAvailableImages();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchComments, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchComments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/comments/queue`);
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
      const response = await fetch(`${API_BASE_URL}/api/templates`);
      if (response.ok) {
        const templatesArray = await response.json();
        const grouped = templatesArray.reduce(
          (acc: Record<string, Template[]>, template: any) => {
            const category = template.category || "GENERIC";
            if (!acc[category]) {
              acc[category] = [];
            }
            acc[category].push({
              id: template.id,
              text: template.body,
              post_type: category.toLowerCase(),
            });
            return acc;
          },
          {}
        );
        setTemplates(grouped);
      }
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    }
  };

  const fetchImagePacks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/image-packs`);
      if (response.ok) {
        const packs = await response.json();
        setImagePacks(packs);
      } else {
        console.error("Failed to fetch image packs");
      }
    } catch (error) {
      console.error("Error loading image packs:", error);
    }
  };

  const fetchAvailableImages = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/image-packs`);
      if (response.ok) {
        const packs = await response.json();
        setAvailableImages(packs);
      } else {
        console.error("Failed to fetch available images");
      }
    } catch (error) {
      console.error("Error loading available images:", error);
    }
  };

  const handleApprove = async (commentId: string) => {
    try {
      const images = selectedImages[commentId] || [];
      const response = await fetch(`${API_BASE_URL}/comments/approve`, {
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
        setSelectedImages((prev) => ({ ...prev, [commentId]: [] }));
        setShowImageSelector((prev) => ({ ...prev, [commentId]: false }));
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
      const response = await fetch(`${API_BASE_URL}/comments/approve`, {
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

  const handleSmartLauncher = async (
    commentId: string,
    comment: QueuedComment
  ) => {
    console.log(
      `🚀 Enhanced Smart Launcher initiated for comment: ${commentId} using ${automationMethod} method`
    );

    try {
      // Clear any previous notifications
      setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      clearError();

      // Step 1: Generate the message
      const result = await generateMessage(commentId);
      if (!result) {
        throw new Error("Failed to generate message");
      }

      console.log("✅ Message generated:", {
        method: result.generation_method,
        chars: result.character_count,
        time: `${result.generation_time_seconds}s`,
      });

      // Store the generated message
      setGeneratedMessages((prev) => ({
        ...prev,
        [commentId]: result.message,
      }));

      // Step 2: Execute Enhanced Smart Launcher
      if (!result.messenger_url) {
        throw new Error("No Messenger URL available");
      }

      // Prepare image URLs - combine post_images, screenshot, and user-selected images
      const imageUrls: string[] = [];
      const userImages = userSelectedImages[commentId] || [];

      console.log("📸 Image data from API:", {
        post_images: result.post_images,
        post_screenshot: result.post_screenshot ? "Present (base64)" : "None",
        has_images: result.has_images,
        user_selected: userImages.length,
      });

      // Add AI-detected images first
      if (result.post_images && result.post_images.length > 0) {
        imageUrls.push(...result.post_images);
        console.log(
          `✅ Added ${result.post_images.length} AI-detected post images`
        );
      }
      if (result.post_screenshot && !imageUrls.length) {
        // Use screenshot as fallback if no other images
        imageUrls.push(result.post_screenshot);
        console.log("✅ Using screenshot as fallback");
      }

      // Add user-selected images
      if (userImages.length > 0) {
        // Convert relative paths to absolute local paths for Selenium file upload
        const userImageUrls = userImages.map((img) => {
          if (img.startsWith("http")) return img;
          if (img.startsWith("C:")) return img; // Already absolute path
          // Convert relative path to absolute local path
          return img.replace(
            /^uploads\//,
            "C:/Users/petem/personal/gem-approval/uploads/"
          );
        });
        imageUrls.push(...userImageUrls);
        console.log(`✅ Added ${userImages.length} user-selected images`);
        console.log("🔍 User image paths:", userImageUrls);
      }

      console.log(
        `📷 Total images to process: ${imageUrls.length} (${
          result.post_images?.length || 0
        } AI + ${userImages.length} user-selected)`
      );

      // Check for debug mode (set window.DEBUG_CLIPBOARD = true in console)
      const debugMode = (window as any).DEBUG_CLIPBOARD === true;

      // Use Enhanced Smart Launcher with selected method
      const launcherResult = await executeEnhancedSmartLauncher(
        result.message,
        result.messenger_url,
        imageUrls,
        {
          method: automationMethod,
          debugMode: debugMode,
          sessionId: `user_${commentId}_${Date.now()}`,
        }
      );

      // Step 3: Show user feedback
      setSmartLauncherNotifications((prev) => ({
        ...prev,
        [commentId]: launcherResult.message,
      }));

      // Auto-clear notification after longer time for Selenium (to see duration)
      const clearDelay = automationMethod === "selenium" ? 10000 : 8000;
      setTimeout(() => {
        setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      }, clearDelay);
    } catch (error) {
      console.error("❌ Enhanced Smart Launcher failed:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      setSmartLauncherNotifications((prev) => ({
        ...prev,
        [commentId]: `❌ Error: ${errorMessage}`,
      }));

      // Clear error notification after 5 seconds
      setTimeout(() => {
        setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      }, 5000);
    }
  };

  const startEditing = (comment: QueuedComment) => {
    setEditingComment(comment.id);

    let commentToEdit = comment.generated_comment;

    if (
      comment.post_author &&
      comment.generated_comment.includes("Hi there!")
    ) {
      commentToEdit = personalizeTemplate(
        comment.generated_comment.replace("Hi there!", "Hi {{author_name}}!"),
        comment.post_author
      );
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
    setSelectedImages((prev) => {
      const currentImages = prev[commentId] || [];
      const newImages = currentImages.includes(filename)
        ? currentImages.filter((img) => img !== filename)
        : [...currentImages, filename];
      return { ...prev, [commentId]: newImages };
    });
  };

  const toggleImageSelector = (commentId: string) => {
    setShowImageSelector((prev) => ({
      ...prev,
      [commentId]: !prev[commentId],
    }));

    if (!showImageSelector[commentId] && !detectedCategories[commentId]) {
      loadDetectedCategories(commentId);
    }
  };

  const loadDetectedCategories = async (commentId: string) => {
    setLoadingCategories((prev) => ({ ...prev, [commentId]: true }));
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/comments/${commentId}/categories`
      );
      if (response.ok) {
        const data = await response.json();
        setDetectedCategories((prev) => ({
          ...prev,
          [commentId]: data.categories || [],
        }));
      }
    } catch (error) {
      console.error(
        `Error loading categories for comment ${commentId}:`,
        error
      );
    } finally {
      setLoadingCategories((prev) => ({ ...prev, [commentId]: false }));
    }
  };

  const handleBulkImageSelect = (commentId: string, filenames: string[]) => {
    setSelectedImages((prev) => ({
      ...prev,
      [commentId]: filenames,
    }));
  };

  const toggleUserImageSelector = (commentId: string) => {
    setShowUserImageSelector((prev) => ({
      ...prev,
      [commentId]: !prev[commentId],
    }));
  };

  // NEW: Generate message only (no sending) and show preview
  const handleGenerateMessageOnly = async (commentId: string) => {
    console.log(`🚀 BUTTON CLICKED! Generating message only for: ${commentId}`);

    try {
      // Clear any previous notifications
      setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      clearError();

      // Generate the message using existing logic
      const result = await generateMessage(commentId);
      if (!result) {
        throw new Error("Failed to generate message");
      }

      console.log("✅ Message generated for preview:", {
        method: result.generation_method,
        chars: result.character_count,
        time: `${result.generation_time_seconds}s`,
      });

      // Store the generated message
      setGeneratedMessages((prev) => ({
        ...prev,
        [commentId]: result.message,
      }));
      setEditableMessages((prev) => ({ ...prev, [commentId]: result.message }));

      // Show the preview box
      console.log("🔍 DEBUG: Setting preview box to open for", commentId);
      setShowMessagePreview((prev) => {
        const newState = { ...prev, [commentId]: true };
        console.log("🔍 DEBUG: Preview state after update:", newState);
        return newState;
      });
    } catch (error) {
      console.error("❌ Message generation failed:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      setSmartLauncherNotifications((prev) => ({
        ...prev,
        [commentId]: `❌ Error: ${errorMessage}`,
      }));

      // Clear error notification after 5 seconds
      setTimeout(() => {
        setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      }, 5000);
    }
  };

  // NEW: Send message from preview box
  const handleSendMessageFromPreview = async (
    commentId: string,
    comment: QueuedComment
  ) => {
    console.log(`📤 Sending message from preview for: ${commentId}`);

    try {
      // Get the final edited message
      const finalMessage =
        editableMessages[commentId] || generatedMessages[commentId];
      if (!finalMessage) {
        throw new Error("No message to send");
      }

      // Prepare image URLs - POST IMAGE FIRST, then user-selected images
      const imageUrls: string[] = [];

      // Add post images FIRST if toggle is enabled
      if (
        includePostImage[commentId] &&
        comment.post_images &&
        comment.post_images.trim().length > 0
      ) {
        try {
          // Parse post_images the same way renderPostImages does
          let parsedImages: string[] = [];
          const postImagesStr = comment.post_images.trim();
          
          if (postImagesStr.startsWith('[') || postImagesStr.startsWith('{')) {
            // JSON array or object format
            const parsed = JSON.parse(postImagesStr);
            parsedImages = Array.isArray(parsed) ? parsed : [parsed];
          } else {
            // Single image URL as string
            parsedImages = [postImagesStr];
          }
          
          // Filter out empty/null images and add to the beginning
          const validImages = parsedImages.filter((url) => url && url.trim() !== '');
          if (validImages.length > 0) {
            imageUrls.push(...validImages);
          }
        } catch (parseError) {
          // Fallback: treat as single URL string
          imageUrls.push(comment.post_images);
        }
      }

      // Add user-selected images AFTER post image
      const userImages = userSelectedImages[commentId] || [];
      if (userImages.length > 0) {
        const userImageUrls = userImages.map((img) => {
          if (img.startsWith("http")) return img;
          if (img.startsWith("C:")) return img;
          return img.replace(
            /^uploads\//,
            "C:/Users/petem/personal/gem-approval/uploads/"
          );
        });
        imageUrls.push(...userImageUrls);
      }

      // Create messenger URL
      const messengerUrl = createMessengerLink(comment.post_author_url || "");
      if (!messengerUrl) {
        throw new Error("No Messenger URL available");
      }

      // Check for debug mode
      const debugMode = (window as any).DEBUG_CLIPBOARD === true;

      // Use existing Enhanced Smart Launcher
      const launcherResult = await executeEnhancedSmartLauncher(
        finalMessage,
        messengerUrl,
        imageUrls,
        {
          method: automationMethod,
          debugMode: debugMode,
          sessionId: `preview_${commentId}_${Date.now()}`,
        }
      );

      // Show success feedback
      setSmartLauncherNotifications((prev) => ({
        ...prev,
        [commentId]: launcherResult.message,
      }));

      // Close the preview box
      setShowMessagePreview((prev) => ({ ...prev, [commentId]: false }));

      // Auto-clear notification
      const clearDelay = automationMethod === "selenium" ? 10000 : 8000;
      setTimeout(() => {
        setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      }, clearDelay);
    } catch (error) {
      console.error("❌ Send message from preview failed:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      setSmartLauncherNotifications((prev) => ({
        ...prev,
        [commentId]: `❌ Error: ${errorMessage}`,
      }));

      // Clear error notification after 5 seconds
      setTimeout(() => {
        setSmartLauncherNotifications((prev) => ({ ...prev, [commentId]: "" }));
      }, 5000);
    }
  };

  const handleUserImageSelect = (commentId: string, filename: string) => {
    setUserSelectedImages((prev) => {
      const currentImages = prev[commentId] || [];
      const newImages = currentImages.includes(filename)
        ? currentImages.filter((img) => img !== filename)
        : [...currentImages, filename];
      return { ...prev, [commentId]: newImages };
    });
  };

  const handleUserBulkImageSelect = (
    commentId: string,
    filenames: string[]
  ) => {
    setUserSelectedImages((prev) => ({
      ...prev,
      [commentId]: filenames,
    }));
  };

  const toggleCommentSmartMode = (commentId: string, enabled: boolean) => {
    setCommentSmartMode((prev) => ({ ...prev, [commentId]: enabled }));

    if (enabled) {
      if (editingComment === commentId && editedText.length >= 10) {
        analyzeCommentText(commentId, editedText);
      }

      // Auto-select images for comment generation only
      if (detectedCategories[commentId]?.length > 0) {
        const suggested = getSuggestedImages(
          detectedCategories[commentId],
          imagePacks,
          2
        );
        setSelectedImages((prev) => ({
          ...prev,
          [commentId]: suggested,
        }));
      }
    } else {
      setRealTimeCategories((prev) => ({ ...prev, [commentId]: [] }));
    }
  };

  const toggleMessageSmartMode = (commentId: string, enabled: boolean) => {
    setMessageSmartMode((prev) => ({ ...prev, [commentId]: enabled }));

    if (enabled) {
      const currentMessage = editableMessages[commentId];
      if (currentMessage && currentMessage.length >= 10) {
        analyzeMessageText(commentId, currentMessage);
      }

      // Auto-select images for message generation only
      if (detectedCategories[commentId]?.length > 0) {
        const suggested = getSuggestedImages(
          detectedCategories[commentId],
          imagePacks,
          2
        );
        setUserSelectedImages((prev) => ({
          ...prev,
          [commentId]: suggested,
        }));
      }
    }
    // Note: Don't clear realTimeCategories here as comment section might still be using it
  };

  const analyzeCommentText = useCallback(
    debounce(async (commentId: string, text: string) => {
      if (!text || text.length < 10) {
        setRealTimeCategories((prev) => ({ ...prev, [commentId]: [] }));
        return;
      }

      setAnalyzingText((prev) => ({ ...prev, [commentId]: true }));
      try {
        const response = await fetch(`${API_BASE_URL}/api/analyze-text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });

        if (response.ok) {
          const data = await response.json();
          const categories = data.categories || [];
          setRealTimeCategories((prev) => ({
            ...prev,
            [commentId]: categories,
          }));

          // Auto-select suggested images for comment generation only
          if (categories.length > 0) {
            const suggested = getSuggestedImages(categories, imagePacks, 2);
            setSelectedImages((prev) => ({
              ...prev,
              [commentId]: suggested,
            }));
          }
        }
      } catch (error) {
        console.error("Real-time comment text analysis failed:", error);
        setRealTimeCategories((prev) => ({ ...prev, [commentId]: [] }));
      } finally {
        setAnalyzingText((prev) => ({ ...prev, [commentId]: false }));
      }
    }, 800),
    [imagePacks]
  );

  const analyzeMessageText = useCallback(
    debounce(async (commentId: string, text: string) => {
      if (!text || text.length < 10) {
        return;
      }

      setAnalyzingText((prev) => ({ ...prev, [commentId]: true }));
      try {
        const response = await fetch(`${API_BASE_URL}/api/analyze-text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });

        if (response.ok) {
          const data = await response.json();
          const categories = data.categories || [];
          
          // Auto-select suggested images for message generation only
          if (categories.length > 0) {
            const suggested = getSuggestedImages(categories, imagePacks, 2);
            setUserSelectedImages((prev) => ({
              ...prev,
              [commentId]: suggested,
            }));
          }
        }
      } catch (error) {
        console.error("Real-time message text analysis failed:", error);
      } finally {
        setAnalyzingText((prev) => ({ ...prev, [commentId]: false }));
      }
    }, 800),
    [imagePacks]
  );

  const handleTextEdit = (commentId: string, text: string) => {
    setEditedText(text);

    if (commentSmartMode[commentId]) {
      analyzeCommentText(commentId, text);
    }
  };

  const personalizeTemplate = (
    templateText: string,
    authorName: string | undefined
  ): string => {
    if (!authorName) {
      return templateText.replace(/\{\{author_name\}\}/g, "there");
    }

    const nameParts = authorName.split(" ");
    const titles = [
      "dr.",
      "dr",
      "mr.",
      "mr",
      "mrs.",
      "mrs",
      "ms.",
      "ms",
      "miss",
      "prof.",
      "prof",
      "rev.",
      "rev",
    ];

    let firstName = nameParts[0];

    for (let i = 0; i < nameParts.length; i++) {
      const part = nameParts[i].toLowerCase().replace(/[.,]/g, "");
      if (!titles.includes(part)) {
        firstName = nameParts[i];
        break;
      }
    }

    firstName = firstName.replace(/[.,]/g, "");

    return templateText.replace(/\{\{author_name\}\}/g, firstName || "there");
  };

  const handleTemplateSelect = (templateId: string, comment: QueuedComment) => {
    const allTemplates = Object.values(templates).flat();
    const template = allTemplates.find((t) => t.id === templateId);

    if (template) {
      const personalizedText = personalizeTemplate(
        template.text,
        comment.post_author
      );
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

  const renderPostImages = (
    comment: QueuedComment,
    isCompact: boolean = false
  ) => {
    let imageUrls: string[] = [];

    if (comment.post_images && comment.post_images.trim() !== "") {
      try {
        const parsed = JSON.parse(comment.post_images);
        imageUrls = Array.isArray(parsed) ? parsed : [parsed];
      } catch {
        imageUrls = [comment.post_images];
      }
    }

    imageUrls = imageUrls.filter((url) => url && url.trim() !== "");

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
                if (imageUrl.startsWith("http") || imageUrl.startsWith("data:"))
                  return imageUrl;
                if (imageUrl.startsWith("iVBORw0KGgo"))
                  return `data:image/png;base64,${imageUrl}`;
                if (imageUrl.startsWith("/9j/"))
                  return `data:image/jpeg;base64,${imageUrl}`;
                if (!imageUrl.startsWith("http"))
                  return `data:image/jpeg;base64,${imageUrl}`;
                return imageUrl;
              })()}
              alt={`Post image ${imgIndex + 1}`}
              className={`${imageSize} rounded-lg border-2 border-white shadow-sm object-cover hover:scale-105 transition-transform duration-200 cursor-pointer`}
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='${
                  isCompact ? "64" : "80"
                }' height='${isCompact ? "64" : "80"}' viewBox='0 0 ${
                  isCompact ? "64" : "80"
                } ${isCompact ? "64" : "80"}'%3E%3Crect width='${
                  isCompact ? "64" : "80"
                }' height='${
                  isCompact ? "64" : "80"
                }' fill='%23f3f4f6'/%3E%3Ctext x='${
                  isCompact ? "32" : "40"
                }' y='${
                  isCompact ? "36" : "45"
                }' font-family='Arial' font-size='${
                  isCompact ? "8" : "10"
                }' fill='%23666' text-anchor='middle'%3ENo Image%3C/text%3E%3C/svg%3E`;
              }}
            />
          ))}
          {imageUrls.length > maxImages && (
            <div
              className={`${imageSize} rounded-lg border-2 border-dashed border-slate-300 bg-slate-100 flex items-center justify-center text-xs font-medium text-slate-600`}
            >
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
          {comments.length} {comments.length === 1 ? "comment" : "comments"}{" "}
          waiting for approval
        </CardDescription>
      </CardHeader>
      <CardContent>
        {comments.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
              <MessageCircle className="h-8 w-8 text-slate-400" />
            </div>
            <p className="text-slate-500 text-lg font-medium">
              No comments in queue
            </p>
            <p className="text-slate-400 text-sm mt-2">
              New comments will appear here when they're ready for approval
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {comments.map((comment, index) => (
              <Card
                key={comment.id}
                className="group relative overflow-hidden bg-gradient-to-br from-white via-slate-50/50 to-white border-0 shadow-lg hover:shadow-2xl transition-all duration-500 hover:scale-[1.02] backdrop-blur-sm"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-indigo-500/5 opacity-0 group-hover:opacity-100 transition-all duration-500" />
                <div className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-blue-500 via-purple-500 to-indigo-600 group-hover:w-2 transition-all duration-300" />
                <CardContent className="relative pt-6 z-10">
                  {/* Post Content Section - Full Width */}
                  <div className="mb-6">
                    <Card className="bg-gradient-to-br from-purple-50/30 to-indigo-50/30 border-l-4 border-l-purple-500 shadow-lg">
                      <CardContent className="p-4">
                        {/* Header with Post Info Only */}
                        <div className="flex items-center gap-3 mb-4">
                          <Badge
                            className={`${getPostTypeColor(
                              comment.post_type
                            )} font-semibold px-3 py-1 rounded-full shadow-sm border-0`}
                          >
                            {comment.post_type.toUpperCase()}
                          </Badge>
                          {comment.post_author && (
                            <span className="text-sm font-medium text-slate-600 bg-white/60 px-3 py-1 rounded-full">
                              by {comment.post_author}
                            </span>
                          )}
                        </div>

                        {/* Main Content Area */}
                        <div className="flex gap-6">
                          {/* Left Side - Post Text */}
                          <div className="flex-1">
                            <h5 className="text-xs font-semibold text-purple-700 mb-2 flex items-center gap-2">
                              <div className="w-0.5 h-3 bg-gradient-to-b from-purple-500 to-indigo-600 rounded-full"></div>
                              Original Post
                            </h5>
                            <p className="text-sm leading-relaxed text-slate-700 bg-white/60 p-4 rounded-lg border border-purple-200/30 mb-3">
                              {comment.post_text}
                            </p>

                            {/* Action Buttons - Below Text */}
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() =>
                                  window.open(comment.post_author_url, "_blank")
                                }
                                className="bg-gradient-to-r from-purple-100 to-indigo-100 hover:from-purple-200 hover:to-indigo-200 text-purple-700 border-0 shadow-sm hover:shadow-md transition-all duration-200 rounded-lg font-medium"
                              >
                                <ExternalLink className="h-4 w-4 mr-2" />
                                View Post
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
                          </div>

                          {/* Right Side - Larger Post Image */}
                          <div className="flex-shrink-0 w-80 flex items-center justify-center">
                            <div className="relative [&_img]:!w-full [&_img]:!max-w-80 [&_img]:!h-64 [&_img]:!object-cover [&_img]:!rounded-lg [&_img]:!shadow-lg [&_img]:!border [&_img]:!border-purple-200/30">
                              {renderPostImages(comment)}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Sidebar Layout - 50% left + 50% right */}
                  <div className="flex gap-4 h-full">
                    {/* Left Side: Comment Generation Sidebar (50%) */}
                    <div className="flex-1 min-w-0" style={{ flex: "0 0 50%" }}>
                      <CommentGenerationSidebar
                        comment={comment}
                        isEditing={editingComment === comment.id}
                        editedText={editedText}
                        selectedTemplate={selectedTemplate}
                        templates={templates}
                        selectedImages={selectedImages[comment.id] || []}
                        showImageSelector={
                          showImageSelector[comment.id] || false
                        }
                        imagePacks={imagePacks}
                        smartMode={commentSmartMode[comment.id] || false}
                        analyzingText={analyzingText[comment.id] || false}
                        realTimeCategories={
                          realTimeCategories[comment.id] || []
                        }
                        detectedCategories={
                          detectedCategories[comment.id] || []
                        }
                        loadingCategories={
                          loadingCategories[comment.id] || false
                        }
                        onStartEditing={() => startEditing(comment)}
                        onCancelEditing={cancelEditing}
                        onApprove={() => handleApprove(comment.id)}
                        onTextEdit={(text) => handleTextEdit(comment.id, text)}
                        onTemplateSelect={(templateId) =>
                          handleTemplateSelect(templateId, comment)
                        }
                        onToggleImageSelector={() =>
                          toggleImageSelector(comment.id)
                        }
                        onImageSelect={(filename) =>
                          handleImageSelect(comment.id, filename)
                        }
                        onBulkImageSelect={(filenames) =>
                          handleBulkImageSelect(comment.id, filenames)
                        }
                        onToggleSmartMode={(enabled) =>
                          toggleCommentSmartMode(comment.id, enabled)
                        }
                        personalizeTemplate={personalizeTemplate}
                      />
                    </div>

                    {/* Right Sidebar: Message Generation (50%) */}
                    <div className="flex-1 min-w-0">
                      {comment.post_author_url &&
                        comment.post_author &&
                        comment.post_author !== "User" && (
                          <MessageGenerationSidebar
                            comment={comment}
                            isGenerating={isGenerating}
                            automationMethod={automationMethod}
                            notification={
                              smartLauncherNotifications[comment.id]
                            }
                            message={editableMessages[comment.id] || ""}
                            isPreviewOpen={
                              showMessagePreview[comment.id] || false
                            }
                            isSending={false} // TODO: Add sending state
                            userSelectedImages={
                              userSelectedImages[comment.id] || []
                            }
                            availableImages={availableImages}
                            includePostImage={
                              includePostImage[comment.id] || false
                            }
                            showImageSelector={
                              showUserImageSelector[comment.id] || false
                            }
                            onGenerateMessage={() =>
                              handleGenerateMessageOnly(comment.id)
                            }
                            onMessageChange={(message) => {
                              setEditableMessages((prev) => ({
                                ...prev,
                                [comment.id]: message,
                              }));
                              if (messageSmartMode[comment.id]) {
                                analyzeMessageText(comment.id, message);
                              }
                            }}
                            onSendMessage={() =>
                              handleSendMessageFromPreview(comment.id, comment)
                            }
                            onToggleIncludePostImage={() =>
                              setIncludePostImage((prev) => ({
                                ...prev,
                                [comment.id]: !prev[comment.id],
                              }))
                            }
                            onToggleImageSelector={() =>
                              setShowUserImageSelector((prev) => ({
                                ...prev,
                                [comment.id]: !prev[comment.id],
                              }))
                            }
                            onImageSelect={(filename) =>
                              handleUserImageSelect(comment.id, filename)
                            }
                            onBulkImageSelect={(filenames) =>
                              handleUserBulkImageSelect(comment.id, filenames)
                            }
                            onClearImages={() =>
                              setUserSelectedImages((prev) => ({
                                ...prev,
                                [comment.id]: [],
                              }))
                            }
                            smartMode={messageSmartMode[comment.id] || false}
                            analyzingText={analyzingText[comment.id] || false}
                            realTimeCategories={
                              realTimeCategories[comment.id] || []
                            }
                            detectedCategories={
                              detectedCategories[comment.id] || []
                            }
                            loadingCategories={loadingCategories[comment.id] || false}
                            onToggleSmartMode={(enabled) =>
                              toggleMessageSmartMode(comment.id, enabled)
                            }
                          />
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
