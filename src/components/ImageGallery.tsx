import React, { useState, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Image as ImageIcon, 
  Check, 
  ChevronDown, 
  ChevronRight,
  Sparkles,
  Grid3x3,
  List
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ImageItem {
  filename: string;
  description: string;
}

interface ImagePack {
  id: string;
  name: string;
  images: ImageItem[];
}

interface ImageGalleryProps {
  categories: string[];
  imagePacks: ImagePack[];
  selectedImages: string[];
  onImageSelect: (filename: string) => void;
  onBulkSelect?: (filenames: string[]) => void;
  smartMode: boolean;
  loading?: boolean;
}

interface CategoryImageGroup {
  category: string;
  images: Array<{
    filename: string;
    description: string;
    packName: string;
    packId: string;
  }>;
}

const categoryConfig: Record<string, { label: string; color: string; keywords: string[] }> = {
  'RINGS': { 
    label: 'Rings', 
    color: 'bg-purple-100 text-purple-800',
    keywords: ['ring', 'band', 'engagement', 'wedding']
  },
  'NECKLACES': { 
    label: 'Necklaces', 
    color: 'bg-blue-100 text-blue-800',
    keywords: ['necklace', 'pendant', 'chain', 'choker']
  },
  'BRACELETS': { 
    label: 'Bracelets', 
    color: 'bg-green-100 text-green-800',
    keywords: ['bracelet', 'bangle', 'wrist']
  },
  'EARRINGS': { 
    label: 'Earrings', 
    color: 'bg-pink-100 text-pink-800',
    keywords: ['earring', 'stud', 'hoop', 'drop']
  },
  'CASTING': { 
    label: 'Casting', 
    color: 'bg-orange-100 text-orange-800',
    keywords: ['cast', 'mold', 'wax', 'manufacturing']
  },
  'CAD': { 
    label: 'CAD/3D', 
    color: 'bg-indigo-100 text-indigo-800',
    keywords: ['cad', '3d', 'design', 'model']
  },
  'SETTING': { 
    label: 'Stone Setting', 
    color: 'bg-red-100 text-red-800',
    keywords: ['setting', 'stone', 'gem', 'diamond']
  },
  'ENGRAVING': { 
    label: 'Engraving', 
    color: 'bg-yellow-100 text-yellow-800',
    keywords: ['engrav', 'etch', 'inscri']
  },
  'GENERIC': { 
    label: 'General', 
    color: 'bg-gray-100 text-gray-800',
    keywords: ['generic', 'general', 'bravo', 'comment']
  }
};

export function ImageGallery({
  categories,
  imagePacks,
  selectedImages,
  onImageSelect,
  onBulkSelect,
  smartMode,
  loading = false
}: ImageGalleryProps) {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(categories) // Auto-expand detected categories
  );

  // Group images by category based on smart detection
  const categorizedImages = useMemo(() => {
    console.log('[DEBUG] ImageGallery categorizedImages:', { smartMode, categories, imagePacksCount: imagePacks.length });
    if (!smartMode || categories.length === 0) {
      // If smart mode is off, show all images in a single "All Images" category
      const allImages: CategoryImageGroup = {
        category: 'ALL',
        images: imagePacks.flatMap(pack => 
          pack.images.map(img => ({
            ...img,
            packName: pack.name,
            packId: pack.id
          }))
        )
      };
      return [allImages];
    }

    // Smart categorization
    const groups: Record<string, CategoryImageGroup> = {};
    
    categories.forEach(category => {
      groups[category] = {
        category,
        images: []
      };
    });

    // Match images to categories based on keywords
    imagePacks.forEach(pack => {
      pack.images.forEach(image => {
        const imageLower = `${image.filename} ${image.description} ${pack.name}`.toLowerCase();
        
        categories.forEach(category => {
          const config = categoryConfig[category];
          if (config) {
            const matches = config.keywords.some(keyword => 
              imageLower.includes(keyword.toLowerCase())
            );
            
            if (matches) {
              groups[category].images.push({
                ...image,
                packName: pack.name,
                packId: pack.id
              });
            }
          }
        });
      });
    });

    // Always include GENERIC category if it has images
    if (!groups['GENERIC'] && categories.includes('GENERIC')) {
      const genericPack = imagePacks.find(p => 
        p.name.toLowerCase().includes('generic') || 
        p.name.toLowerCase().includes('general')
      );
      
      if (genericPack) {
        groups['GENERIC'] = {
          category: 'GENERIC',
          images: genericPack.images.map(img => ({
            ...img,
            packName: genericPack.name,
            packId: genericPack.id
          }))
        };
      }
    }

    const result = Object.values(groups).filter(group => group.images.length > 0);
    console.log('[DEBUG] ImageGallery result:', result.map(g => ({ category: g.category, imageCount: g.images.length })));
    return result;
  }, [categories, imagePacks, smartMode]);

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const selectAllInCategory = (group: CategoryImageGroup) => {
    if (onBulkSelect) {
      const categoryImageFilenames = group.images.map(img => img.filename);
      const allSelected = categoryImageFilenames.every(f => selectedImages.includes(f));
      
      if (allSelected) {
        // Deselect all
        onBulkSelect(selectedImages.filter(f => !categoryImageFilenames.includes(f)));
      } else {
        // Select all
        const newSelection = [...new Set([...selectedImages, ...categoryImageFilenames])];
        onBulkSelect(newSelection);
      }
    }
  };

  const renderImageThumbnail = (image: any) => {
    const isSelected = selectedImages.includes(image.filename);
    
    return (
      <div
        key={image.filename}
        onClick={() => onImageSelect(image.filename)}
        className={cn(
          "relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all",
          isSelected 
            ? "border-primary ring-2 ring-primary/20" 
            : "border-border hover:border-primary/50"
        )}
      >
        <div className="aspect-square relative bg-muted">
          <img
            src={`http://localhost:8000/${image.filename}`}
            alt={image.description || image.filename}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
              const fallback = e.currentTarget.nextElementSibling as HTMLElement;
              if (fallback) fallback.style.display = 'flex';
            }}
          />
          <div className="w-full h-full items-center justify-center text-muted-foreground hidden">
            <ImageIcon className="h-8 w-8" />
          </div>
          
          {/* Selection overlay */}
          {isSelected && (
            <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
              <div className="bg-primary text-primary-foreground rounded-full p-1">
                <Check className="h-4 w-4" />
              </div>
            </div>
          )}
          
          {/* Hover overlay with details */}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <p className="text-xs text-white truncate">{image.description || image.filename}</p>
            <p className="text-xs text-white/70 truncate">{image.packName}</p>
          </div>
        </div>
      </div>
    );
  };

  const renderCategorySection = (group: CategoryImageGroup) => {
    const isExpanded = expandedCategories.has(group.category);
    const config = categoryConfig[group.category] || categoryConfig['GENERIC'];
    const categoryImages = group.images;
    const selectedCount = categoryImages.filter(img => 
      selectedImages.includes(img.filename)
    ).length;
    const allSelected = selectedCount === categoryImages.length && categoryImages.length > 0;

    return (
      <Card key={group.category} className="overflow-hidden">
        <div 
          className="p-4 border-b cursor-pointer hover:bg-muted/50 transition-colors"
          onClick={() => toggleCategory(group.category)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" className="p-0 h-auto">
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>
              
              <Badge className={cn("text-xs", config.color)}>
                {config.label}
              </Badge>
              
              <span className="text-sm font-medium">
                {categoryImages.length} images
              </span>
              
              {selectedCount > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {selectedCount} selected
                </Badge>
              )}
              
              {smartMode && categories.includes(group.category) && (
                <Badge variant="outline" className="text-xs border-primary text-primary">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Suggested
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => selectAllInCategory(group)}
                className="text-xs"
              >
                {allSelected ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
          </div>
        </div>
        
        {isExpanded && (
          <div className="p-4">
            {viewMode === 'grid' ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {categoryImages.map(renderImageThumbnail)}
              </div>
            ) : (
              <div className="space-y-2">
                {categoryImages.map(image => (
                  <label
                    key={image.filename}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted cursor-pointer"
                  >
                    <Checkbox
                      checked={selectedImages.includes(image.filename)}
                      onCheckedChange={() => onImageSelect(image.filename)}
                    />
                    <div className="w-12 h-12 rounded overflow-hidden bg-muted flex-shrink-0">
                      <img
                        src={`http://localhost:8000/${image.filename}`}
                        alt={image.description}
                        className="w-full h-full object-cover"
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                          const parent = e.currentTarget.parentElement;
                          if (parent) {
                            parent.innerHTML = '<div class="w-full h-full flex items-center justify-center text-muted-foreground"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg></div>';
                          }
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{image.description || image.filename}</p>
                      <p className="text-xs text-muted-foreground truncate">{image.packName}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-muted-foreground">Loading images...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {selectedImages.length} images selected
          </span>
          {smartMode && categories.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              Smart Mode Active
            </Badge>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
          >
            {viewMode === 'grid' ? <List className="h-4 w-4" /> : <Grid3x3 className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      
      {/* Image Categories */}
      <ScrollArea className="h-[500px] pr-4">
        <div className="space-y-4">
          {categorizedImages.map(renderCategorySection)}
          
          {categorizedImages.length === 0 && (
            <Card className="p-8">
              <div className="text-center text-muted-foreground">
                <ImageIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No images available for the detected categories.</p>
                {smartMode && (
                  <p className="text-sm mt-2">
                    Try disabling Smart Mode to see all available images.
                  </p>
                )}
              </div>
            </Card>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}