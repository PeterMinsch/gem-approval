import React from "react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { ImageGallery } from "./ImageGallery";
import {
  MessageSquare,
  User,
  ExternalLink,
  Edit3,
  CheckCircle,
  XCircle,
  Image,
  Sparkles,
  FileText,
  Settings,
} from "lucide-react";

interface QueuedComment {
  id: string;
  post_author?: string;
  post_text: string;
  post_author_url?: string;
  post_images?: string;
  post_type: string;
  generated_comment: string;
}

interface ImagePack {
  id: string;
  name: string;
  images: { filename: string; description: string }[];
}

interface Template {
  id: string;
  text: string;
}

interface CommentGenerationSidebarProps {
  comment: QueuedComment;
  isEditing: boolean;
  editedText: string;
  selectedTemplate: string;
  templates: Record<string, Template[]>;
  selectedImages: string[];
  showImageSelector: boolean;
  imagePacks: ImagePack[];
  smartMode: boolean;
  analyzingText: boolean;
  realTimeCategories: string[];
  detectedCategories: string[];
  loadingCategories: boolean;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onApprove: () => void;
  onTextEdit: (text: string) => void;
  onTemplateSelect: (templateId: string) => void;
  onToggleImageSelector: () => void;
  onToggleSmartMode: (enabled: boolean) => void;
  onImageSelect: (filename: string) => void;
  onBulkImageSelect: (filenames: string[]) => void;
  personalizeTemplate: (text: string, authorName?: string) => string;
}

export const CommentGenerationSidebar: React.FC<CommentGenerationSidebarProps> = ({
  comment,
  isEditing,
  editedText,
  selectedTemplate,
  templates,
  selectedImages,
  showImageSelector,
  imagePacks,
  smartMode,
  analyzingText,
  realTimeCategories,
  detectedCategories,
  loadingCategories,
  onStartEditing,
  onCancelEditing,
  onApprove,
  onTextEdit,
  onTemplateSelect,
  onToggleImageSelector,
  onToggleSmartMode,
  onImageSelect,
  onBulkImageSelect,
  personalizeTemplate,
}) => {
  const hasAuthor = comment.post_author && comment.post_author !== "User";

  return (
    <Card className="h-full bg-gradient-to-br from-purple-50/30 to-indigo-50/30 border-l-4 border-l-purple-500 shadow-lg">
      <CardHeader className="pb-3 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-purple-100/50">
        <CardTitle className="text-sm font-semibold text-purple-800 flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-purple-500 text-white">
            <MessageSquare className="h-4 w-4" />
          </div>
          Comment Approval
        </CardTitle>
        {hasAuthor && (
          <div className="flex items-center gap-2 text-xs text-purple-600">
            <User className="h-3 w-3" />
            <span>By: {comment.post_author}</span>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-4 space-y-4">
        {isEditing ? (
          <>
            {/* Template Selection */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">Choose Template (Optional)</h4>
              <Select value={selectedTemplate} onValueChange={onTemplateSelect}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a template or write custom comment below..." />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(templates).map(([postType, templateList]) => (
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
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Comment Editor */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-700">Custom Comment</h4>
                {analyzingText && (
                  <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-50 px-2 py-1 rounded-full">
                    <div className="animate-spin h-3 w-3 border-2 border-purple-600 border-t-transparent rounded-full"></div>
                    <span className="text-xs">Analyzing...</span>
                  </div>
                )}
              </div>

              {/* Real-time detected categories */}
              {smartMode && realTimeCategories.length > 0 && (
                <div className="p-2 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                  <div className="text-xs font-semibold text-purple-700 mb-1">Live Detected Categories:</div>
                  <div className="flex flex-wrap gap-1">
                    {realTimeCategories.map(category => (
                      <Badge key={category} className="text-xs bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-2 py-0.5 rounded-full">
                        <Sparkles className="h-2 w-2 mr-1" />
                        {category}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <Textarea
                value={editedText}
                onChange={(e) => onTextEdit(e.target.value)}
                className="min-h-[100px] resize-none focus:ring-purple-500 focus:border-purple-500"
                placeholder="Write your comment here..."
              />
            </div>

            {/* Selected Images Preview */}
            {selectedImages.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Image className="h-4 w-4 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">
                    Attached Images ({selectedImages.length})
                  </span>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {selectedImages.map((image, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={image.startsWith('http') ? image : `http://localhost:8000/${image}`}
                        alt={image}
                        className="w-12 h-12 object-cover rounded border-2 border-white shadow-sm"
                      />
                      <button
                        onClick={() => onImageSelect(image)}
                        className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity duration-200 shadow-lg"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Image Selector with Smart Mode Toggle */}
            <div className="space-y-2 relative">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onToggleImageSelector}
                    className="h-8 w-8 p-0 rounded-full hover:bg-purple-100 text-purple-600 relative"
                  >
                    <Image className="h-4 w-4" />
                    {selectedImages.length > 0 && (
                      <span className="absolute -top-1 -right-1 h-5 w-5 bg-purple-500 text-white text-xs rounded-full flex items-center justify-center">
                        {selectedImages.length}
                      </span>
                    )}
                  </Button>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-3 w-3 text-purple-600" />
                    <Switch
                      id={`smart-mode-${comment.id}`}
                      checked={smartMode}
                      onCheckedChange={onToggleSmartMode}
                      className="data-[state=checked]:bg-purple-500 scale-75"
                    />
                  </div>
                </div>
                {selectedImages.length > 0 && (
                  <span className="text-xs text-gray-500">
                    {selectedImages.length} image{selectedImages.length !== 1 ? 's' : ''} selected
                  </span>
                )}
              </div>

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
                          Select Images for Comment
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
                        imagePacks={imagePacks}
                        selectedImages={selectedImages}
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

            {/* Editing Action Buttons */}
            <div className="flex gap-2 pt-2 border-t border-purple-200">
              <Button
                variant="outline"
                size="sm"
                onClick={onCancelEditing}
                className="flex-1 bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 text-purple-700 border-purple-200"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={onApprove}
                className="flex-1 bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 text-white shadow-lg border-0 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl"
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Post Comment
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* Generated Comment Display - Click to Edit */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-purple-700 flex items-center gap-2">
                <Edit3 className="h-4 w-4" />
                Comment to {comment.post_author}
              </h4>
              <div 
                className="p-3 bg-white/60 rounded-lg border border-purple-200/30 cursor-pointer hover:bg-white/80 hover:border-purple-300 transition-all duration-200 group"
                onClick={onStartEditing}
              >
                <p className="text-sm text-slate-700 leading-relaxed font-medium group-hover:text-slate-800">
                  {comment.generated_comment}
                </p>
                <div className="text-xs text-purple-600 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  Click to edit comment
                </div>
              </div>
            </div>

            {/* Post Comment Button */}
            <div className="pt-3 border-t border-purple-200">
              <Button
                size="sm"
                onClick={onApprove}
                className="w-full bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 text-white shadow-lg border-0 rounded-lg font-medium transition-all duration-200 hover:scale-105 hover:shadow-xl"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Post Comment
              </Button>
            </div>
          </>
        )}

        {/* Smart Mode Indicator */}
        {smartMode && (
          <div className="p-2 bg-white rounded-lg border border-purple-100">
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <Settings className="h-3 w-3" />
              <span>Smart Mode Active</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};