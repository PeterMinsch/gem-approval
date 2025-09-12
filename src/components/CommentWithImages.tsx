import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { API_BASE_URL } from "../config/api";
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Calendar,
  User,
  Image as ImageIcon,
  Expand,
  Star
} from 'lucide-react';

interface CommentWithImagesProps {
  text: string;
  images: string[];
  masterImage?: string;
  timestamp?: string;
  author?: string;
  className?: string;
  showTimestamp?: boolean;
  showAuthor?: boolean;
}

export function CommentWithImages({ 
  text, 
  images, 
  masterImage, 
  timestamp, 
  author,
  className = "",
  showTimestamp = true,
  showAuthor = true
}: CommentWithImagesProps) {
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  
  // Ensure master image appears first in the images array
  const sortedImages = images.length > 0 ? (() => {
    if (masterImage && images.includes(masterImage)) {
      return [
        masterImage,
        ...images.filter(img => img !== masterImage)
      ];
    }
    return images;
  })() : [];

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return null;
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const ImageLightbox = ({ images, initialIndex }: { images: string[], initialIndex: number }) => (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 text-white hover:bg-black/70"
        >
          <Expand className="h-3 w-3" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl w-full">
        <div className="relative">
          <img
            src={`${API_BASE_URL}/${images[selectedImageIndex]}`}
            alt={`Image ${selectedImageIndex + 1}`}
            className="w-full h-auto max-h-[70vh] object-contain rounded-lg"
          />
          
          {images.length > 1 && (
            <div className="flex justify-center mt-4 gap-2">
              {images.map((image, index) => (
                <button
                  key={image}
                  onClick={() => setSelectedImageIndex(index)}
                  className={`w-12 h-12 rounded border-2 overflow-hidden ${
                    index === selectedImageIndex ? 'border-primary' : 'border-gray-300'
                  }`}
                >
                  <img
                    src={`${API_BASE_URL}/${image}`}
                    alt={`Thumbnail ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );

  return (
    <Card className={`bg-white shadow-sm hover:shadow-md transition-shadow ${className}`}>
      <CardContent className="p-4 space-y-4">
        {/* Header with author and timestamp */}
        {(showAuthor || showTimestamp) && (
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              {showAuthor && author && (
                <>
                  <User className="h-3 w-3" />
                  <span className="font-medium">{author}</span>
                </>
              )}
            </div>
            
            {showTimestamp && timestamp && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>{formatTimestamp(timestamp)}</span>
              </div>
            )}
          </div>
        )}

        {/* Comment Text */}
        <div className="prose prose-sm max-w-none">
          <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{text}</p>
        </div>
        
        {/* Images Section */}
        {sortedImages.length > 0 && (
          <div className="space-y-3">
            {/* Master Image - Large Display */}
            {sortedImages.length > 0 && (
              <div className="relative group">
                <div className="relative rounded-lg overflow-hidden bg-gray-100">
                  <img
                    src={`${API_BASE_URL}/${sortedImages[0]}`}
                    alt="Main image"
                    className="w-full max-w-md rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    loading="lazy"
                    onClick={() => setSelectedImageIndex(0)}
                  />
                  
                  {/* Master Image Badge */}
                  {sortedImages[0] === masterImage && (
                    <div className="absolute top-2 left-2">
                      <Badge className="bg-primary text-primary-foreground flex items-center gap-1">
                        <Star className="h-2 w-2" />
                        Main
                      </Badge>
                    </div>
                  )}
                  
                  {/* Image Count Badge */}
                  {sortedImages.length > 1 && (
                    <div className="absolute top-2 right-2">
                      <Badge variant="secondary" className="bg-black/50 text-white">
                        <ImageIcon className="h-2 w-2 mr-1" />
                        {sortedImages.length}
                      </Badge>
                    </div>
                  )}
                  
                  {/* Lightbox Trigger */}
                  <ImageLightbox images={sortedImages} initialIndex={0} />
                </div>
              </div>
            )}
            
            {/* Additional Images - Thumbnail Grid */}
            {sortedImages.length > 1 && (
              <div className="space-y-2">
                <h5 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <ImageIcon className="h-3 w-3" />
                  Additional Images ({sortedImages.length - 1})
                </h5>
                
                <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
                  {sortedImages.slice(1).map((image, index) => (
                    <Dialog key={image}>
                      <DialogTrigger asChild>
                        <div 
                          className="relative aspect-square rounded border hover:shadow-md transition-shadow cursor-pointer group overflow-hidden"
                          onClick={() => setSelectedImageIndex(index + 1)}
                        >
                          <img
                            src={`${API_BASE_URL}/${image}`}
                            alt={`Additional image ${index + 2}`}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                            loading="lazy"
                          />
                          
                          {/* Hover overlay */}
                          <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <Expand className="h-4 w-4 text-white" />
                          </div>
                        </div>
                      </DialogTrigger>
                      <DialogContent className="max-w-4xl">
                        <img
                          src={`${API_BASE_URL}/${image}`}
                          alt={`Full size image ${index + 2}`}
                          className="w-full h-auto max-h-[70vh] object-contain rounded-lg"
                        />
                      </DialogContent>
                    </Dialog>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* No images placeholder */}
        {sortedImages.length === 0 && (
          <div className="text-center py-4 text-muted-foreground">
            <ImageIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No images attached</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}