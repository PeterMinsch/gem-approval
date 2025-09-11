import React, { useState } from "react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { ImageGallery } from "./ImageGallery";
import {
  Sparkles,
  Image,
  MessageCircle,
  Send,
  Settings,
  User,
  Edit3,
  Eye,
  FileImage,
  X,
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

interface MessageGenerationSidebarProps {
  comment: QueuedComment;
  isGenerating: boolean;
  automationMethod: 'clipboard' | 'selenium';
  notification?: string;
  message: string;
  isPreviewOpen: boolean;
  isSending: boolean;
  userSelectedImages: string[];
  availableImages: ImagePack[];
  includePostImage: boolean;
  showImageSelector: boolean;
  smartMode: boolean;
  analyzingText: boolean;
  realTimeCategories: string[];
  detectedCategories: string[];
  loadingCategories: boolean;
  onGenerateMessage: () => void;
  onMessageChange: (message: string) => void;
  onSendMessage: () => void;
  onToggleIncludePostImage: () => void;
  onToggleImageSelector: () => void;
  onToggleSmartMode: (enabled: boolean) => void;
  onImageSelect: (filename: string) => void;
  onBulkImageSelect: (filenames: string[]) => void;
  onClearImages: () => void;
}

export const MessageGenerationSidebar: React.FC<MessageGenerationSidebarProps> = ({
  comment,
  isGenerating,
  automationMethod,
  notification,
  message,
  isPreviewOpen,
  isSending,
  userSelectedImages,
  availableImages,
  includePostImage,
  showImageSelector,
  smartMode,
  analyzingText,
  realTimeCategories,
  detectedCategories,
  loadingCategories,
  onGenerateMessage,
  onMessageChange,
  onSendMessage,
  onToggleIncludePostImage,
  onToggleImageSelector,
  onToggleSmartMode,
  onImageSelect,
  onBulkImageSelect,
  onClearImages,
}) => {
  const hasAuthor = comment.post_author && comment.post_author !== "User";

  return (
    <Card className="h-full bg-gradient-to-br from-purple-50/30 to-indigo-50/30 border-l-4 border-l-purple-500 shadow-lg">
      <CardHeader className="pb-3 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-purple-100/50">
        <CardTitle className="text-sm font-semibold text-purple-800 flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-purple-500 text-white">
            <MessageCircle className="h-4 w-4" />
          </div>
          Private Message
        </CardTitle>
        {hasAuthor && (
          <div className="flex items-center gap-2 text-xs text-purple-600">
            <User className="h-3 w-3" />
            <span>To: {comment.post_author}</span>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-4 space-y-4">
        {/* Message Generation Section - Only show if no message generated yet */}
        {!isPreviewOpen && (
          <>
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Generate Message
              </h4>
              
              {/* Generate Button */}
              <Button
                size="sm"
                disabled={isGenerating}
                onClick={onGenerateMessage}
                className="w-full bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 disabled:from-gray-400 disabled:to-gray-500 text-white shadow-lg border-0 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl disabled:cursor-not-allowed disabled:transform-none"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full" />
                    {automationMethod === 'selenium' ? 'Automating...' : 'Generating...'}
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate
                  </>
                )}
              </Button>
            </div>

            {/* Automation Method Display */}
            <div className="p-3 bg-white rounded-lg border border-purple-100">
              <div className="flex items-center gap-2 text-xs text-gray-600">
                <Settings className="h-3 w-3" />
                <span>Method: {automationMethod === 'selenium' ? 'Full Automation' : 'Clipboard Mode'}</span>
              </div>
            </div>
          </>
        )}

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

        {/* Debug Info */}
        {isGenerating && (
          <div className="text-xs text-gray-500 p-2 bg-gray-50 rounded">
            Generating message...
          </div>
        )}

        {/* Message Preview Section */}
        {isPreviewOpen && (
          <div className="space-y-4 pt-4 border-t border-purple-200">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-purple-600" />
              <h4 className="text-sm font-medium text-purple-800">Message Preview</h4>
            </div>
            
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
                className="min-h-[100px] resize-none focus:ring-purple-500 focus:border-purple-500"
                placeholder="Edit your message here..."
                disabled={isSending}
              />
            </div>

            {/* Image Controls */}
            <div className="space-y-3">
              {/* Post Image Toggle */}
              {comment.post_images && comment.post_images.trim().length > 0 && (
                <div className="flex items-center gap-3 p-2 bg-white rounded-lg border border-purple-100">
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
                      Include post image
                    </span>
                  </Label>
                </div>
              )}

              {/* Add Images Button with Smart Mode Toggle */}
              <div className="space-y-2 relative">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={onToggleImageSelector}
                      className="h-8 w-8 p-0 rounded-full hover:bg-purple-100 text-purple-600 relative"
                      disabled={isSending}
                    >
                      <Image className="h-4 w-4" />
                      {userSelectedImages.length > 0 && (
                        <span className="absolute -top-1 -right-1 h-5 w-5 bg-purple-500 text-white text-xs rounded-full flex items-center justify-center">
                          {userSelectedImages.length}
                        </span>
                      )}
                    </Button>
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-3 w-3 text-purple-600" />
                      <Switch
                        id={`smart-mode-msg-${comment.id}`}
                        checked={smartMode}
                        onCheckedChange={onToggleSmartMode}
                        className="data-[state=checked]:bg-purple-500 scale-75"
                        disabled={isSending}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {userSelectedImages.length > 0 && (
                      <span className="text-xs text-gray-500">
                        {userSelectedImages.length} image{userSelectedImages.length !== 1 ? 's' : ''} selected
                      </span>
                    )}
                    {userSelectedImages.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClearImages}
                        className="text-xs text-purple-600 hover:text-purple-800 h-6 px-2"
                        disabled={isSending}
                      >
                        Clear All
                      </Button>
                    )}
                  </div>
                </div>

                {/* Selected Images Preview */}
                {userSelectedImages.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Image className="h-4 w-4 text-gray-600" />
                      <span className="text-sm font-medium text-gray-700">
                        Attached Images ({userSelectedImages.length})
                      </span>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {userSelectedImages.map((image, index) => (
                        <div key={index} className="relative group">
                          <img
                            src={image.startsWith('http') ? image : `http://localhost:8000/${image}`}
                            alt={image}
                            className="w-12 h-12 object-cover rounded border-2 border-white shadow-sm"
                          />
                          <button
                            onClick={() => onImageSelect(image)}
                            className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity duration-200 shadow-lg"
                            disabled={isSending}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Image Gallery Modal */}
                {showImageSelector && (
                  <>
                    {/* Backdrop */}
                    <div 
                      className="fixed inset-0 z-40 bg-black/20"
                      onClick={onToggleImageSelector}
                    />
                    {/* Modal */}
                    <div className="fixed z-50 top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-2xl bg-white rounded-lg border border-purple-200 shadow-2xl max-h-[80vh] overflow-hidden">
                      <div className="p-4 border-b border-purple-100">
                        <div className="flex items-center justify-between">
                          <h4 className="text-lg font-semibold text-purple-800 flex items-center gap-2">
                            <Image className="h-5 w-5" />
                            Select Images for Message
                          </h4>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={onToggleImageSelector}
                            className="h-8 w-8 p-0 text-gray-400 hover:text-gray-600 rounded-full"
                          >
                            ×
                          </Button>
                        </div>
                      </div>
                      <div className="p-4 overflow-y-auto max-h-[60vh]">
                        <ImageGallery
                          categories={smartMode ? (
                            realTimeCategories.length > 0 
                              ? realTimeCategories 
                              : detectedCategories
                          ) : []}
                          imagePacks={availableImages}
                          selectedImages={userSelectedImages}
                          onImageSelect={onImageSelect}
                          onBulkSelect={onBulkImageSelect}
                          smartMode={smartMode}
                          loading={loadingCategories}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Image Summary */}
              {(userSelectedImages.length > 0 || (includePostImage && comment.post_images)) && (
                <div className="p-2 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="text-xs text-blue-700 flex items-center gap-1">
                    <Image className="h-3 w-3" />
                    <span>
                      {userSelectedImages.length + (includePostImage && comment.post_images ? 1 : 0)} image{userSelectedImages.length + (includePostImage && comment.post_images ? 1 : 0) !== 1 ? 's' : ''} will be sent
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onGenerateMessage}
                disabled={isGenerating || isSending}
                className="flex-1 border-purple-200 text-purple-700 hover:bg-purple-50"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                {isGenerating ? 'Generating...' : 'New Message'}
              </Button>
              
              <Button
                size="sm"
                onClick={onSendMessage}
                disabled={isSending || !message.trim()}
                className="flex-1 bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 text-white shadow-lg"
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
        )}
      </CardContent>
    </Card>
  );
};