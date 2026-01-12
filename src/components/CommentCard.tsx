import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { API_BASE_URL } from "../config/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ExternalLink, Check, X, Clock, Image, Sparkles } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { ImageGallery } from "./ImageGallery";
import { getSuggestedImages } from "@/services/categoryMapper";

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
  onApprove: (commentId: string, editedComment?: string, images?: string[]) => void;
  onReject: (commentId: string) => void;
}

interface ImagePack {
  id: string;
  name: string;
  images: { filename: string; description: string }[];
}

export function CommentCard({ comment, onApprove, onReject }: CommentCardProps) {
  const [editedComment, setEditedComment] = useState(comment.suggestedComment);
  const [showImageSelector, setShowImageSelector] = useState(false);
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [imagePacks, setImagePacks] = useState<ImagePack[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Smart categorization state
  const [smartMode, setSmartMode] = useState(true); // Default to smart mode ON
  const [detectedCategories, setDetectedCategories] = useState<string[]>([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(false);
  const [autoSelectEnabled, setAutoSelectEnabled] = useState(false);
  
  const isPending = comment.status === 'pending';

  // Load detected categories for this comment
  const loadDetectedCategories = async () => {
    setIsLoadingCategories(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/comments/${comment.id}/categories`);
      if (response.ok) {
        const data = await response.json();
        setDetectedCategories(data.categories || []);
        console.log('Detected categories:', data.categories);
      } else {
        console.error('Failed to load categories:', response.status);
        setDetectedCategories([]);
      }
    } catch (error) {
      console.error('Error loading categories:', error);
      setDetectedCategories([]);
    } finally {
      setIsLoadingCategories(false);
    }
  };

  // Load image packs and categories when component mounts
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      
      // Load image packs (existing code)
      try {
        const response = await fetch('${API_BASE_URL}/api/image-packs');
        if (response.ok) {
          const packs = await response.json();
          setImagePacks(packs);
        } else {
          console.error('Failed to load image packs:', response.status);
        }
      } catch (error) {
        console.error('Error loading image packs:', error);
      }
      
      // NEW: Load detected categories
      await loadDetectedCategories();
      
      setLoading(false);
    };

    loadData();
  }, [comment.id]); // Add comment.id as dependency

  const handleImageSelect = (filename: string) => {
    setSelectedImages(prev => 
      prev.includes(filename) 
        ? prev.filter(img => img !== filename)
        : [...prev, filename]
    );
  };
  
  const handleBulkImageSelect = (filenames: string[]) => {
    setSelectedImages(filenames);
  };
  
  // Auto-select suggested images when smart mode is enabled
  useEffect(() => {
    if (autoSelectEnabled && smartMode && detectedCategories.length > 0 && imagePacks.length > 0) {
      const suggested = getSuggestedImages(detectedCategories, imagePacks, 2);
      setSelectedImages(suggested);
      setAutoSelectEnabled(false); // Only auto-select once
    }
  }, [autoSelectEnabled, smartMode, detectedCategories, imagePacks]);

  
  return (
    <Card className="transition-shadow duration-200 hover:shadow-lg border border-border/50">
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
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-sm">Suggested Comment:</h4>
            {isPending && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowImageSelector(!showImageSelector)}
                className="h-7 px-2"
              >
                <Image className="h-3 w-3 mr-1" />
                Images ({selectedImages.length})
              </Button>
            )}
          </div>
          
          {/* Image Gallery - New Visual Interface */}
          {showImageSelector && isPending && (
            <div className="border rounded-lg bg-background/50 backdrop-blur-sm">
              <div className="border-b p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h5 className="font-semibold text-sm">Select Images</h5>
                    
                    {/* Smart Mode Toggle */}
                    <div className="flex items-center gap-2">
                      <Switch
                        id="smart-gallery"
                        checked={smartMode}
                        onCheckedChange={(checked) => {
                          setSmartMode(checked);
                          if (checked && detectedCategories.length > 0) {
                            setAutoSelectEnabled(true);
                          }
                        }}
                        disabled={isLoadingCategories || detectedCategories.length === 0}
                      />
                      <Label htmlFor="smart-gallery" className="text-xs cursor-pointer">
                        <span className="flex items-center gap-1">
                          <Sparkles className="h-3 w-3" />
                          Smart Mode
                        </span>
                      </Label>
                    </div>
                    
                    {/* Category count */}
                    {detectedCategories.length > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {detectedCategories.length} categories detected
                      </Badge>
                    )}
                  </div>
                  
                  {/* Auto-select button */}
                  {smartMode && detectedCategories.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const suggested = getSuggestedImages(detectedCategories, imagePacks, 2);
                        setSelectedImages(suggested);
                      }}
                      className="text-xs"
                    >
                      <Sparkles className="h-3 w-3 mr-1" />
                      Auto-Select Best
                    </Button>
                  )}
                </div>
              </div>
              
              <div className="p-3">
                <ImageGallery
                  categories={smartMode ? detectedCategories : []}
                  imagePacks={imagePacks}
                  selectedImages={selectedImages}
                  onImageSelect={handleImageSelect}
                  onBulkSelect={handleBulkImageSelect}
                  smartMode={smartMode}
                  loading={loading || isLoadingCategories}
                />
              </div>
            </div>
          )}
          
          <Textarea
            value={editedComment}
            onChange={(e) => setEditedComment(e.target.value)}
            disabled={!isPending}
            className="text-sm min-h-[80px] resize-none"
            placeholder="Edit your comment here..."
          />
          
          {selectedImages.length > 0 && (
            <div className="flex flex-wrap gap-1 p-2 bg-muted rounded-md">
              {selectedImages.map((image, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {image}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedImages(prev => prev.filter((_, i) => i !== index))}
                    className="ml-1 h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                  >
                    ×
                  </Button>
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
      
      <CardFooter className="pt-0">
        {isPending && (
          <div className="flex gap-2 w-full">
            <Button
              variant="default"
              size="sm"
              onClick={() => onApprove(comment.id, editedComment, selectedImages.length > 0 ? selectedImages : undefined)}
              className="bg-success hover:bg-success/90 text-success-foreground flex-1"
            >
              <Check className="h-3 w-3 mr-1" />
              Approve
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onReject(comment.id)}
              className="flex-1"
            >
              <X className="h-3 w-3 mr-1" />
              Reject
            </Button>
          </div>
        )}
      </CardFooter>
    </Card>
  );
}