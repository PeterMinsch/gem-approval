import React, { useState } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { ImageGallery } from "./ImageGallery";
import {
  Send,
  Edit3,
  Image,
  X,
  Eye,
  FileImage,
  Sparkles,
} from "lucide-react";

interface QueuedComment {
  id: string;
  post_author?: string;
  post_text: string;
  post_author_url?: string;
  post_images?: string;
}

interface ImagePack {
  id: string;
  name: string;
  images: { filename: string; description: string }[];
}

interface MessagePreviewBoxProps {
  comment: QueuedComment;
  message: string;
  isOpen: boolean;
  isGenerating: boolean;
  isSending: boolean;
  automationMethod: 'clipboard' | 'selenium';
  userSelectedImages: string[];
  availableImages: ImagePack[];
  includePostImage: boolean;
  showImageSelector: boolean;
  notification?: string;
  onClose: () => void;
  onMessageChange: (message: string) => void;
  onSendMessage: () => void;
  onToggleIncludePostImage: () => void;
  onToggleImageSelector: () => void;
  onImageSelect: (filename: string) => void;
  onBulkImageSelect: (filenames: string[]) => void;
  onClearImages: () => void;
}

export const MessagePreviewBox: React.FC<MessagePreviewBoxProps> = ({
  comment,
  message,
  isOpen,
  isGenerating,
  isSending,
  automationMethod,
  userSelectedImages,
  availableImages,
  includePostImage,
  showImageSelector,
  notification,
  onClose,
  onMessageChange,
  onSendMessage,
  onToggleIncludePostImage,
  onToggleImageSelector,
  onImageSelect,
  onBulkImageSelect,
  onClearImages,
}) => {
  console.log('🔍 DEBUG MessagePreviewBox:', { 
    isOpen, 
    message: message.substring(0, 50) + '...', 
    commentId: comment.id 
  });
  
  if (!isOpen) return null;

  const hasUserImages = userSelectedImages.length > 0;
  const hasPostImages = comment.post_images && comment.post_images.trim().length > 0;
  const totalImages = userSelectedImages.length + (includePostImage && hasPostImages ? 1 : 0);

  return (
    <Card className="mt-4 border-2 border-purple-200 bg-gradient-to-br from-purple-50/50 to-indigo-50/30 shadow-lg">
      <CardHeader className="pb-3 bg-gradient-to-r from-purple-100/50 to-indigo-100/50 border-b border-purple-200">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-purple-800 flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-purple-500 text-white">
              <Eye className="h-4 w-4" />
            </div>
            Message Preview
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-purple-600 hover:text-purple-800 hover:bg-purple-100"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-4 space-y-4">
        {/* Editable Message */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Edit3 className="h-4 w-4 text-gray-600" />
            <Label className="text-sm font-medium text-gray-700">
              Message to {comment.post_author}
            </Label>
            <span className="text-xs text-gray-500">({message.length} characters)</span>
          </div>
          <Textarea
            value={message}
            onChange={(e) => onMessageChange(e.target.value)}
            className="min-h-[120px] resize-none focus:ring-purple-500 focus:border-purple-500"
            placeholder="Edit your message here..."
            disabled={isSending}
          />
        </div>

        {/* Image Controls */}
        <div className="space-y-3">
          {/* Post Image Toggle */}
          {hasPostImages && (
            <div className="flex items-center gap-3 p-3 bg-white rounded-lg border border-purple-200">
              <div className="flex items-center gap-2">
                <Switch
                  id="include-post-image"
                  checked={includePostImage}
                  onCheckedChange={onToggleIncludePostImage}
                  disabled={isSending}
                  className="data-[state=checked]:bg-purple-500"
                />
                <Label htmlFor="include-post-image" className="text-sm font-medium cursor-pointer">
                  <span className="flex items-center gap-2">
                    <FileImage className="h-4 w-4" />
                    Include post image (1)
                  </span>
                </Label>
              </div>
            </div>
          )}

          {/* Add Images Button */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleImageSelector}
              className="flex items-center gap-2 hover:bg-purple-50 border-purple-200"
              disabled={isSending}
            >
              <Image className="h-4 w-4" />
              {showImageSelector ? 'Hide Images' : 'Add Images'}
              {hasUserImages && (
                <span className="ml-1 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                  {userSelectedImages.length}
                </span>
              )}
            </Button>

            {hasUserImages && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClearImages}
                className="text-xs text-purple-600 hover:text-purple-800"
                disabled={isSending}
              >
                Clear All
              </Button>
            )}
          </div>

          {/* Image Gallery */}
          {showImageSelector && (
            <div className="p-3 bg-white rounded-lg border border-purple-200">
              <ImageGallery
                categories={[]}
                imagePacks={availableImages}
                selectedImages={userSelectedImages}
                onImageSelect={onImageSelect}
                onBulkSelect={onBulkImageSelect}
                smartMode={false}
                loading={false}
              />
            </div>
          )}

          {/* Image Summary */}
          {totalImages > 0 && (
            <div className="p-2 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-700 flex items-center gap-1">
                <Image className="h-3 w-3" />
                <span>
                  {totalImages} image{totalImages !== 1 ? 's' : ''} will be sent
                  {includePostImage && hasPostImages && hasUserImages && 
                    ` (1 from post + ${userSelectedImages.length} selected)`
                  }
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Notification Area */}
        {notification && (
          <div className={`text-xs p-2 rounded-md ${
            notification.includes('❌') 
              ? 'bg-red-50 text-red-700 border border-red-200' 
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}>
            {notification}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-2 border-t border-purple-200">
          <div className="text-xs text-gray-500 flex items-center gap-1">
            <Sparkles className="h-3 w-3" />
            <span>Method: {automationMethod === 'selenium' ? 'Full Automation' : 'Clipboard Mode'}</span>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSending}
              className="border-gray-300"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={onSendMessage}
              disabled={isSending || !message.trim()}
              className="bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 text-white shadow-lg"
            >
              {isSending ? (
                <>
                  <div className="animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Message
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};