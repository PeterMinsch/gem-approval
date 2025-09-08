# 🎯 Auto-Category Image Pack Selection Feature - Implementation Guide

## 📋 Overview

This feature adds intelligent image pack suggestions based on post content analysis. When enabled, the system will automatically show the most relevant image packs first (e.g., ring-related packs for posts mentioning "rings").

**Estimated Implementation Time**: 2-3 hours  
**Difficulty**: Medium  
**Prerequisites**: Existing AI classification system (already implemented)

---

## 🔍 Current System Analysis

### What We Already Have ✅
- **AI-powered post classification** in `bot/classifier.py` 
- **Rich keyword detection** for jewelry terms (`"ring", "necklace", "casting", etc.`)
- **Classification results** stored with confidence scores
- **Image pack system** with categories (`GENERIC`, `CAD`, `CASTING`, etc.)
- **Frontend image selection** in `CommentCard.tsx`

### What We're Adding 🆕
- **Category mapping** from detected keywords to image pack categories
- **Smart toggle switch** in the comment card UI
- **Filtered image pack display** based on detected categories  
- **Database storage** of detected categories per comment

---

## 🛠 Implementation Steps

### Step 1: Enhanced Category Detection (30 minutes)

**File**: `bot/classifier.py`

Add this method to the `PostClassifier` class:

```python
def detect_jewelry_categories(self, text: str, classification: PostClassification) -> List[str]:
    """
    Detect specific jewelry categories from post text and existing classification.
    
    Args:
        text: The original post text
        classification: Existing PostClassification result
        
    Returns:
        List of relevant image pack categories
    """
    categories = []
    text_lower = text.lower()
    
    # Keyword to category mapping
    keyword_to_category = {
        # Jewelry Types
        "ring": "RINGS",
        "wedding ring": "RINGS", 
        "engagement ring": "RINGS",
        "anniversary ring": "RINGS",
        "band": "RINGS",
        "wedding band": "RINGS",
        
        "necklace": "NECKLACES",
        "pendant": "NECKLACES", 
        "chain": "NECKLACES",
        "choker": "NECKLACES",
        
        "bracelet": "BRACELETS",
        "bangle": "BRACELETS",
        "tennis bracelet": "BRACELETS",
        
        "earring": "EARRINGS",
        "earrings": "EARRINGS",
        "stud": "EARRINGS",
        "hoop": "EARRINGS",
        
        # Services
        "casting": "CASTING",
        "cast": "CASTING", 
        "lost wax": "CASTING",
        
        "cad": "CAD",
        "3d design": "CAD",
        "stl": "CAD",
        "3dm": "CAD",
        "matrix": "CAD",
        "rhino": "CAD",
        
        "stone setting": "SETTING",
        "setting": "SETTING",
        "prong": "SETTING",
        "pavé": "SETTING",
        "pave": "SETTING",
        "bezel": "SETTING",
        "channel": "SETTING",
        
        "engraving": "ENGRAVING",
        "laser engraving": "ENGRAVING",
        "hand engraving": "ENGRAVING",
        
        "enamel": "ENAMEL",
        "color fill": "ENAMEL",
        "rhodium": "ENAMEL",
        "plating": "ENAMEL"
    }
    
    # Check for direct keyword matches
    for keyword, category in keyword_to_category.items():
        if keyword in text_lower:
            categories.append(category)
    
    # Fallback based on existing classification
    if not categories:
        if classification.post_type == "service":
            # Default service categories
            categories = ["CAD", "CASTING", "SETTING"]
        elif classification.post_type == "iso":
            # ISO posts might be looking for specific items
            categories = ["GENERIC"]
        else:
            # General posts get generic category
            categories = ["GENERIC"]
    
    # Always include GENERIC as fallback
    if "GENERIC" not in categories:
        categories.append("GENERIC")
    
    # Remove duplicates and return
    return list(set(categories))
```

**Test the enhancement**:
```python
# Add this test function temporarily to verify it works
def test_category_detection():
    from bravo_config import CONFIG
    classifier = PostClassifier(CONFIG)
    
    test_cases = [
        "Looking for someone to cast this engagement ring design",
        "Need help with stone setting on custom necklace", 
        "ISO CAD designer for bracelet project",
        "Beautiful earrings! Love the style"
    ]
    
    for text in test_cases:
        classification = classifier.classify_post(text)
        categories = classifier.detect_jewelry_categories(text, classification)
        print(f"Text: {text[:50]}...")
        print(f"Categories: {categories}")
        print("---")

# Run test: python -c "from classifier import test_category_detection; test_category_detection()"
```

---

### Step 2: Database Schema Update (30 minutes)

**File**: `bot/database.py`

#### 2.1 Add Column to Comment Queue Table

Add this method to the `Database` class:

```python
def add_categories_column(self):
    """Add detected_categories column to comment_queue table if it doesn't exist"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if column exists
            cursor.execute("PRAGMA table_info(comment_queue)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'detected_categories' not in columns:
                cursor.execute("""
                    ALTER TABLE comment_queue 
                    ADD COLUMN detected_categories TEXT DEFAULT '[]'
                """)
                conn.commit()
                print("✅ Added detected_categories column to comment_queue table")
            else:
                print("ℹ️ detected_categories column already exists")
                
    except Exception as e:
        print(f"❌ Error adding categories column: {e}")
```

#### 2.2 Update add_to_comment_queue Method

Modify the existing `add_to_comment_queue` method signature and implementation:

```python
def add_to_comment_queue(self, post_url: str, post_text: str, comment_text: str, 
                        post_type: str, post_screenshot: str = None, 
                        post_images: List[str] = None, post_author: str = None, 
                        post_engagement: str = None, image_pack_id: str = None,
                        detected_categories: List[str] = None) -> int:
    """Add a comment to the moderation queue with detected categories"""
    
    # Convert categories to JSON string
    categories_json = json.dumps(detected_categories or [])
    
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comment_queue 
            (post_url, post_text, comment_text, post_type, post_screenshot, 
             post_images, post_author, post_engagement, image_pack_id, 
             detected_categories, queued_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_url, post_text, comment_text, post_type, post_screenshot,
            json.dumps(post_images or []), post_author, post_engagement, image_pack_id,
            categories_json,  # NEW: Store detected categories
            datetime.now(), "pending"
        ))
        
        comment_id = cursor.lastrowid
        conn.commit()
        return comment_id
```

#### 2.3 Add Helper Method to Retrieve Categories

```python
def get_comment_categories(self, comment_id: int) -> List[str]:
    """Get detected categories for a specific comment"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT detected_categories FROM comment_queue 
                WHERE id = ?
            """, (comment_id,))
            
            result = cursor.fetchone()
            if result and result[0]:
                return json.loads(result[0])
            return []
            
    except Exception as e:
        logger.error(f"Error getting comment categories: {e}")
        return []
```

#### 2.4 Run Database Migration

Add this to the `Database.__init__()` method or run manually:

```python
# In Database.__init__ after create_tables():
self.add_categories_column()
```

---

### Step 3: Backend API Integration (30 minutes)

**File**: `bot/api.py`

#### 3.1 Update Comment Generation Endpoint

Find the `generate_comment` function and modify it to include category detection:

```python
@app.post("/api/comments/generate", response_model=CommentResponse)
async def generate_comment(request: CommentRequest):
    """Generate a comment for the given post with category detection"""
    try:
        # ... existing code until classification ...
        
        # Existing classification
        logger.info(f"🏷️ Classifying post...")
        classification = bot_instance.classifier.classify_post(post_text)
        logger.info(f"✅ Classification complete - Type: {classification.post_type}")
        
        # NEW: Detect jewelry categories
        detected_categories = bot_instance.classifier.detect_jewelry_categories(post_text, classification)
        logger.info(f"🎯 Detected categories: {detected_categories}")
        
        if classification.should_skip:
            logger.info(f"⏭️ Post filtered out: {classification.post_type}")
            return CommentResponse(success=False, message=f"Post filtered out: {classification.post_type}")
        
        # ... existing comment generation ...
        
        # Modified queue addition with categories
        queue_id = add_comment_to_queue(
            clean_url, post_text, comment, classification.post_type,
            post_screenshot=post_screenshot, post_images=post_images,
            post_author=post_author, post_engagement=post_engagement,
            detected_categories=detected_categories  # NEW: Pass detected categories
        )
        
        # ... rest of existing code ...
        
    except Exception as e:
        # ... existing error handling ...
```

#### 3.2 Add New Endpoint for Category Retrieval

Add this new endpoint:

```python
@app.get("/api/comments/{comment_id}/categories")
async def get_comment_categories(comment_id: int):
    """Get detected categories for a specific comment"""
    try:
        categories = db.get_comment_categories(comment_id)
        return {
            "success": True,
            "comment_id": comment_id,
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Error getting categories for comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comment categories")
```

---

### Step 4: Frontend Toggle Implementation (1 hour)

**File**: `src/components/CommentCard.tsx`

#### 4.1 Add New State Variables

Add these to the component state (around line 35):

```typescript
// Existing state...
const [selectedImages, setSelectedImages] = useState<string[]>([]);
const [imagePacks, setImagePacks] = useState<ImagePack[]>([]);
const [loading, setLoading] = useState(false);

// NEW: Smart categorization state
const [smartMode, setSmartMode] = useState(false);
const [detectedCategories, setDetectedCategories] = useState<string[]>([]);
const [isLoadingCategories, setIsLoadingCategories] = useState(false);

const isPending = comment.status === 'pending';
```

#### 4.2 Add Category Loading Function

Add this function after the existing `loadImagePacks`:

```typescript
// Load detected categories for this comment
const loadDetectedCategories = async () => {
  setIsLoadingCategories(true);
  try {
    const response = await fetch(`http://localhost:8000/api/comments/${comment.id}/categories`);
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
```

#### 4.3 Update useEffect to Load Categories

Modify the existing useEffect:

```typescript
// Load image packs and categories when component mounts
useEffect(() => {
  const loadData = async () => {
    setLoading(true);
    
    // Load image packs (existing code)
    try {
      const response = await fetch('http://localhost:8000/api/image-packs');
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
```

#### 4.4 Add Smart Filtering Function

Add this function:

```typescript
// Filter image packs based on detected categories
const getFilteredImagePacks = () => {
  if (!smartMode || detectedCategories.length === 0) {
    return imagePacks;
  }
  
  // Map categories to pack names (you may need to adjust based on your pack names)
  const categoryMapping: Record<string, string[]> = {
    'RINGS': ['Generic Card', 'Ring Designs', 'Wedding Rings'],
    'NECKLACES': ['Generic Card', 'Necklace Gallery'],
    'BRACELETS': ['Generic Card', 'Bracelet Styles'], 
    'EARRINGS': ['Generic Card', 'Earring Collection'],
    'CASTING': ['Casting Services', 'Manufacturing'],
    'CAD': ['CAD Designs', '3D Models'],
    'SETTING': ['Stone Setting', 'Setting Examples'],
    'ENGRAVING': ['Engraving Samples'],
    'ENAMEL': ['Enamel Work', 'Color Fill'],
    'GENERIC': ['Generic Card']
  };
  
  // Get relevant pack names
  const relevantPackNames = detectedCategories
    .flatMap(category => categoryMapping[category] || [])
    .concat(['Generic Card']); // Always include generic
  
  // Filter packs
  const filtered = imagePacks.filter(pack => 
    relevantPackNames.some(name => 
      pack.name.toLowerCase().includes(name.toLowerCase())
    )
  );
  
  // If no matches, return all packs
  return filtered.length > 0 ? filtered : imagePacks;
};
```

#### 4.5 Update the Header with Toggle Switch

Replace the existing header section (around line 101):

```typescript
<div className="flex items-center justify-between">
  <h4 className="font-medium text-sm">Suggested Comment:</h4>
  {isPending && (
    <div className="flex items-center gap-2">
      {/* NEW: Smart categorization toggle */}
      <div className="flex items-center gap-1">
        <Switch
          id="smart-mode"
          checked={smartMode}
          onCheckedChange={setSmartMode}
          size="sm"
          disabled={isLoadingCategories || detectedCategories.length === 0}
        />
        <Label htmlFor="smart-mode" className="text-xs text-muted-foreground">
          Smart
        </Label>
        {detectedCategories.length > 0 && (
          <span className="text-xs text-blue-600">
            ({detectedCategories.length})
          </span>
        )}
      </div>
      
      {/* Existing Images button */}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowImageSelector(!showImageSelector)}
        className="h-7 px-2"
      >
        <Image className="h-3 w-3 mr-1" />
        Images ({selectedImages.length})
      </Button>
    </div>
  )}
</div>
```

#### 4.6 Update Image Pack Display

Modify the image pack selection section:

```typescript
{/* Image Pack Selection */}
{showImageSelector && isPending && (
  <div className="border rounded-md p-3 bg-muted/30 space-y-3">
    <div className="flex items-center justify-between">
      <h5 className="font-medium text-sm">Select Images to Attach:</h5>
      
      {/* NEW: Category indicators */}
      {smartMode && detectedCategories.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {detectedCategories.slice(0, 3).map(category => (
            <Badge key={category} variant="secondary" className="text-xs">
              {category}
            </Badge>
          ))}
          {detectedCategories.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{detectedCategories.length - 3} more
            </Badge>
          )}
        </div>
      )}
    </div>
    
    {loading ? (
      <div className="text-sm text-muted-foreground">Loading image packs...</div>
    ) : (
      <div className="space-y-2">
        {/* Use filtered image packs when smart mode is enabled */}
        {getFilteredImagePacks().map(pack => (
          <Collapsible key={pack.id}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="justify-between h-8 w-full px-2 text-left">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{pack.name}</span>
                  {/* NEW: Smart mode indicator */}
                  {smartMode && (
                    <Badge variant="outline" className="text-xs text-blue-600">
                      suggested
                    </Badge>
                  )}
                </div>
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
        
        {/* NEW: Show message when smart mode filters everything out */}
        {smartMode && getFilteredImagePacks().length === 0 && (
          <div className="text-sm text-muted-foreground text-center py-4">
            No image packs match the detected categories. Toggle off Smart mode to see all packs.
          </div>
        )}
      </div>
    )}
  </div>
)}
```

---

### Step 5: Testing & Validation (30 minutes)

#### 5.1 Create Test Script

**File**: `test_auto_category.py`

```python
"""Test script for auto-category functionality"""

def test_category_detection():
    """Test the category detection system"""
    from bot.classifier import PostClassifier
    from bot.bravo_config import CONFIG
    
    classifier = PostClassifier(CONFIG)
    
    test_cases = [
        {
            "text": "Looking for someone to cast this engagement ring design",
            "expected_categories": ["RINGS", "CASTING"]
        },
        {
            "text": "Need help with stone setting on custom necklace",
            "expected_categories": ["NECKLACES", "SETTING"]
        },
        {
            "text": "ISO CAD designer for bracelet project", 
            "expected_categories": ["BRACELETS", "CAD"]
        },
        {
            "text": "Beautiful earrings! Love the engraving work",
            "expected_categories": ["EARRINGS", "ENGRAVING"]
        },
        {
            "text": "Generic jewelry question",
            "expected_categories": ["GENERIC"]
        }
    ]
    
    print("🧪 Testing Category Detection System")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['text'][:40]}...")
        
        # Run classification
        classification = classifier.classify_post(case["text"])
        categories = classifier.detect_jewelry_categories(case["text"], classification)
        
        print(f"  Post Type: {classification.post_type}")
        print(f"  Detected: {categories}")
        print(f"  Expected: {case['expected_categories']}")
        
        # Check if any expected category was found
        found_expected = any(cat in categories for cat in case['expected_categories'])
        print(f"  Result: {'✅ PASS' if found_expected else '❌ FAIL'}")

if __name__ == "__main__":
    test_category_detection()
```

#### 5.2 Database Testing

```python
def test_database_integration():
    """Test database category storage and retrieval"""
    from bot.database import db
    
    # Test adding categories
    categories = ["RINGS", "CASTING"]
    comment_id = db.add_to_comment_queue(
        post_url="https://facebook.com/test",
        post_text="Test ring casting post", 
        comment_text="Test comment",
        post_type="service",
        detected_categories=categories
    )
    
    # Test retrieving categories
    retrieved = db.get_comment_categories(comment_id)
    
    print(f"Stored: {categories}")
    print(f"Retrieved: {retrieved}")
    print(f"Match: {'✅ PASS' if categories == retrieved else '❌ FAIL'}")

if __name__ == "__main__":
    test_database_integration()
```

#### 5.3 Frontend Testing Checklist

- [ ] Toggle switch appears in comment card header
- [ ] Categories load when comment is displayed  
- [ ] Smart mode filters image packs correctly
- [ ] Toggle between smart and normal mode works
- [ ] Category badges show when smart mode is enabled
- [ ] "suggested" badges appear on relevant packs
- [ ] Fallback message shows when no packs match

---

## 🚀 Deployment Steps

### 1. Pre-deployment Testing
```bash
# Test category detection
cd bot
python test_auto_category.py

# Test database migration
python -c "from database import Database; db = Database(); db.add_categories_column()"

# Restart API server
python api.py
```

### 2. Frontend Build
```bash
# Build frontend with new components
npm run build
```

### 3. Production Deployment
1. Run database migration on production
2. Deploy updated API code
3. Deploy updated frontend
4. Test with real posts

---

## 📊 Success Metrics

- [ ] **Category Detection**: 80%+ accuracy on test cases
- [ ] **UI Responsiveness**: Toggle works smoothly without lag
- [ ] **Smart Filtering**: Shows 2-5 relevant packs instead of all 10+
- [ ] **Fallback Handling**: Generic packs shown when no matches
- [ ] **User Experience**: Clear visual indicators for smart suggestions

---

## 🐛 Troubleshooting

### Common Issues

**1. Categories not detected**
- Check if `detected_categories` column exists in database
- Verify classification system is working
- Check API endpoint returns categories

**2. Toggle not working** 
- Ensure Switch component is imported
- Check state management in React component
- Verify categories are loaded before enabling toggle

**3. No image packs shown in smart mode**
- Check category mapping in `getFilteredImagePacks()`
- Verify image pack names match mapping
- Ensure fallback to all packs works

**4. Database errors**
- Run `add_categories_column()` migration
- Check JSON serialization of categories
- Verify database connection

### Debug Commands
```bash
# Check database schema
python -c "from database import Database; db = Database(); print([col[1] for col in db.cursor.execute('PRAGMA table_info(comment_queue)').fetchall()])"

# Test classification directly  
python -c "from bot.classifier import PostClassifier; from bot.bravo_config import CONFIG; classifier = PostClassifier(CONFIG); print(classifier.classify_post('test ring post'))"

# Check API endpoint
curl http://localhost:8000/api/comments/1/categories
```

---

## 🎯 Future Enhancements

### Phase 2 Features (Optional)
- **Confidence Scoring**: Show relevance percentages
- **Learning System**: Improve based on user selections
- **Custom Categories**: User-defined category mappings
- **Analytics**: Track which suggestions are most helpful

### Performance Optimizations
- **Caching**: Cache category detection results
- **Bulk Processing**: Analyze multiple comments at once
- **Smart Defaults**: Remember user preferences

---

## ✅ Completion Checklist

### Backend
- [ ] Category detection method added to `classifier.py`
- [ ] Database schema updated with `detected_categories` column
- [ ] API endpoint modified to store categories
- [ ] Category retrieval endpoint added
- [ ] Migration script run successfully

### Frontend  
- [ ] Smart mode toggle added to comment card
- [ ] Category loading implemented
- [ ] Image pack filtering logic added
- [ ] UI indicators for smart suggestions added
- [ ] Error handling for edge cases added

### Testing
- [ ] Category detection accuracy tested
- [ ] Database integration verified  
- [ ] Frontend toggle functionality tested
- [ ] End-to-end flow validated
- [ ] Edge cases handled

### Documentation
- [ ] Implementation guide completed
- [ ] Troubleshooting guide added
- [ ] Success metrics defined
- [ ] Future enhancements outlined

---

**🎉 Once completed, users will see a "Smart" toggle in their comment cards that automatically suggests the most relevant image packs based on what the AI detects in the post content!**