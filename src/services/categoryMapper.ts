// Category to image pack mapping service
// Maps detected jewelry categories to relevant image packs and keywords

export interface CategoryMapping {
  keywords: string[];
  packNames: string[];
  priority: number; // Higher priority = more relevant
}

export const categoryToPackMapping: Record<string, CategoryMapping> = {
  'RINGS': {
    keywords: ['ring', 'band', 'engagement', 'wedding', 'anniversary', 'solitaire', 'eternity'],
    packNames: ['Ring Designs', 'Wedding Rings', 'Engagement Rings', 'Generic Card'],
    priority: 10
  },
  'NECKLACES': {
    keywords: ['necklace', 'pendant', 'chain', 'choker', 'locket', 'collar'],
    packNames: ['Necklace Gallery', 'Pendant Styles', 'Chain Collection', 'Generic Card'],
    priority: 10
  },
  'BRACELETS': {
    keywords: ['bracelet', 'bangle', 'wrist', 'cuff', 'charm bracelet', 'tennis bracelet'],
    packNames: ['Bracelet Styles', 'Bangle Collection', 'Generic Card'],
    priority: 10
  },
  'EARRINGS': {
    keywords: ['earring', 'stud', 'hoop', 'drop', 'dangle', 'chandelier', 'ear'],
    packNames: ['Earring Collection', 'Stud Designs', 'Hoop Styles', 'Generic Card'],
    priority: 10
  },
  'CASTING': {
    keywords: ['cast', 'casting', 'mold', 'wax', 'manufacturing', 'production', 'lost wax'],
    packNames: ['Casting Services', 'Manufacturing', 'Production Gallery', 'Generic Card'],
    priority: 8
  },
  'CAD': {
    keywords: ['cad', '3d', 'design', 'model', 'render', 'digital', 'computer aided'],
    packNames: ['CAD Designs', '3D Models', 'Digital Renders', 'Generic Card'],
    priority: 8
  },
  'SETTING': {
    keywords: ['setting', 'stone', 'gem', 'diamond', 'prong', 'bezel', 'pave', 'channel'],
    packNames: ['Stone Setting', 'Setting Examples', 'Diamond Settings', 'Generic Card'],
    priority: 7
  },
  'ENGRAVING': {
    keywords: ['engrav', 'etch', 'inscri', 'personali', 'monogram', 'custom text'],
    packNames: ['Engraving Samples', 'Custom Engravings', 'Personalization', 'Generic Card'],
    priority: 6
  },
  'ENAMEL': {
    keywords: ['enamel', 'color', 'painted', 'cloisonne', 'champleve', 'plique'],
    packNames: ['Enamel Work', 'Color Fill', 'Painted Jewelry', 'Generic Card'],
    priority: 6
  },
  'GENERIC': {
    keywords: ['generic', 'general', 'bravo', 'comment', 'jewelry', 'custom', 'handmade'],
    packNames: ['Generic Card', 'General Collection'],
    priority: 1
  }
};

export interface ImagePack {
  id: string;
  name: string;
  images: Array<{
    filename: string;
    description: string;
  }>;
}

/**
 * Get relevant image packs based on detected categories
 */
export function getRelevantPacks(
  categories: string[], 
  allPacks: ImagePack[]
): ImagePack[] {
  if (!categories || categories.length === 0) {
    return allPacks;
  }

  const relevantPackNames = new Set<string>();
  const packPriorities = new Map<string, number>();

  // Collect all relevant pack names and their priorities
  categories.forEach(category => {
    const mapping = categoryToPackMapping[category];
    if (mapping) {
      mapping.packNames.forEach(packName => {
        relevantPackNames.add(packName.toLowerCase());
        // Keep the highest priority for each pack
        const currentPriority = packPriorities.get(packName.toLowerCase()) || 0;
        packPriorities.set(packName.toLowerCase(), Math.max(currentPriority, mapping.priority));
      });
    }
  });

  // Filter and sort packs
  const filteredPacks = allPacks.filter(pack => {
    const packNameLower = pack.name.toLowerCase();
    // Check if pack name matches any of the relevant pack names
    return Array.from(relevantPackNames).some(relevantName => 
      packNameLower.includes(relevantName) || relevantName.includes(packNameLower)
    );
  });

  // Sort by priority (higher priority first)
  filteredPacks.sort((a, b) => {
    const priorityA = packPriorities.get(a.name.toLowerCase()) || 0;
    const priorityB = packPriorities.get(b.name.toLowerCase()) || 0;
    return priorityB - priorityA;
  });

  // If no packs found, return generic pack as fallback
  if (filteredPacks.length === 0) {
    const genericPack = allPacks.find(pack => 
      pack.name.toLowerCase().includes('generic') || 
      pack.name.toLowerCase().includes('general')
    );
    return genericPack ? [genericPack] : [];
  }

  return filteredPacks;
}

/**
 * Check if an image matches a category based on keywords
 */
export function imageMatchesCategory(
  image: { filename: string; description: string },
  category: string,
  packName: string
): boolean {
  const mapping = categoryToPackMapping[category];
  if (!mapping) return false;

  const searchText = `${image.filename} ${image.description} ${packName}`.toLowerCase();
  
  // Check if any keyword matches
  return mapping.keywords.some(keyword => 
    searchText.includes(keyword.toLowerCase())
  );
}

/**
 * Get suggested images for categories (top N from each category)
 */
export function getSuggestedImages(
  categories: string[],
  packs: ImagePack[],
  maxPerCategory: number = 2
): string[] {
  const suggestedImages: string[] = [];
  const imagesByCategory = new Map<string, string[]>();

  // Group images by category
  categories.forEach(category => {
    const categoryImages: string[] = [];
    
    packs.forEach(pack => {
      pack.images.forEach(image => {
        if (imageMatchesCategory(image, category, pack.name)) {
          categoryImages.push(image.filename);
        }
      });
    });
    
    imagesByCategory.set(category, categoryImages);
  });

  // Select top images from each category
  imagesByCategory.forEach((images, category) => {
    const selected = images.slice(0, maxPerCategory);
    suggestedImages.push(...selected);
  });

  // Remove duplicates
  return [...new Set(suggestedImages)];
}

/**
 * Get category display configuration
 */
export function getCategoryConfig(category: string) {
  const configs: Record<string, { label: string; color: string; icon?: string }> = {
    'RINGS': { label: 'Rings', color: 'purple', icon: '💍' },
    'NECKLACES': { label: 'Necklaces', color: 'blue', icon: '📿' },
    'BRACELETS': { label: 'Bracelets', color: 'green', icon: '⌚' },
    'EARRINGS': { label: 'Earrings', color: 'pink', icon: '👂' },
    'CASTING': { label: 'Casting', color: 'orange', icon: '🔨' },
    'CAD': { label: 'CAD/3D', color: 'indigo', icon: '💻' },
    'SETTING': { label: 'Stone Setting', color: 'red', icon: '💎' },
    'ENGRAVING': { label: 'Engraving', color: 'yellow', icon: '✏️' },
    'ENAMEL': { label: 'Enamel', color: 'teal', icon: '🎨' },
    'GENERIC': { label: 'General', color: 'gray', icon: '📦' }
  };
  
  return configs[category] || configs['GENERIC'];
}