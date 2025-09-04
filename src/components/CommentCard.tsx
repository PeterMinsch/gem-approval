import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ExternalLink, Check, X, Clock, Image, ChevronDown, ChevronRight } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

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
  const isPending = comment.status === 'pending';

  // Load image packs when component mounts
  useEffect(() => {
    const loadImagePacks = async () => {
      setLoading(true);
      try {
        // For now, use mock data since the API has validation issues
        const mockPacks: ImagePack[] = [
          {
            id: 'engagement_rings',
            name: 'Engagement Rings',
            images: [
              { filename: 'solitaire_diamond.jpg', description: 'Classic solitaire diamond ring' },
              { filename: 'vintage_halo.jpg', description: 'Vintage-inspired halo setting' },
              { filename: 'three_stone.jpg', description: 'Three stone engagement ring' }
            ]
          },
          {
            id: 'earrings_collection', 
            name: 'Earrings Collection',
            images: [
              { filename: 'diamond_studs.jpg', description: 'Classic diamond stud earrings' },
              { filename: 'pearl_drops.jpg', description: 'Elegant pearl drop earrings' },
              { filename: 'gold_hoops.jpg', description: 'Modern gold hoop earrings' }
            ]
          }
        ];
        setImagePacks(mockPacks);
      } catch (error) {
        console.error('Error loading image packs:', error);
      } finally {
        setLoading(false);
      }
    };

    loadImagePacks();
  }, []);

  const handleImageSelect = (filename: string) => {
    setSelectedImages(prev => 
      prev.includes(filename) 
        ? prev.filter(img => img !== filename)
        : [...prev, filename]
    );
  };
  
  return (
    <Card className="transition-all duration-200 hover:shadow-lg border border-border/50">
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
          
          {/* Image Pack Selection */}
          {showImageSelector && isPending && (
            <div className="border rounded-md p-3 bg-muted/30 space-y-3">
              <h5 className="font-medium text-sm">Select Images to Attach:</h5>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading image packs...</div>
              ) : (
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
                              checked={selectedImages.includes(image.filename)}
                              onChange={() => handleImageSelect(image.filename)}
                              className="rounded border-2"
                            />
                            <div className="text-sm">
                              <div className="font-medium">{image.filename}</div>
                              <div className="text-muted-foreground text-xs">{image.description}</div>
                            </div>
                          </label>
                        ))}
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              )}
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