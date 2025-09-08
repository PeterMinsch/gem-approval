import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Settings as SettingsIcon,
  FileText,
  Image,
  Users,
  Save,
  Plus,
  Trash2,
  Edit,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Settings {
  register_url: string;
  phone: string;
  ask_for: string;
  openai_api_key: string;
  brand_blacklist: string[];
  allowed_brand_modifiers: string[];
  negative_keywords: string[];
  service_keywords: string[];
  iso_keywords: string[];
  scan_refresh_minutes: number;
  max_comments_per_account_per_day: number;
}

interface Template {
  id: string;
  name: string;
  category: string;
  body: string;
  image_pack_id?: string;
  is_default: boolean;
}

interface ImagePack {
  id: string;
  name: string;
  images: string[];
  is_default: boolean;
}

interface FacebookAccount {
  id: string;
  display_name: string;
  profile_url?: string;
  status: string;
  daily_quota: number;
  last_used_at?: string;
  notes?: string;
}

const Settings = () => {
  const [settings, setSettings] = useState<Settings>({
    register_url: "",
    phone: "",
    ask_for: "",
    openai_api_key: "",
    brand_blacklist: [],
    allowed_brand_modifiers: [],
    negative_keywords: [],
    service_keywords: [],
    iso_keywords: [],
    scan_refresh_minutes: 3,
    max_comments_per_account_per_day: 8,
  });

  const [templates, setTemplates] = useState<Template[]>([]);
  const [imagePacks, setImagePacks] = useState<ImagePack[]>([]);
  const [fbAccounts, setFbAccounts] = useState<FacebookAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  // Form states
  const [newBrand, setNewBrand] = useState("");
  const [newKeyword, setNewKeyword] = useState("");
  const [newModifier, setNewModifier] = useState("");
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [newTemplate, setNewTemplate] = useState({
    name: "",
    category: "GENERIC",
    body: "",
    image_pack_id: "",
    is_default: false,
  });
  const [templateFormOpen, setTemplateFormOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<Template | null>(null);
  const [templateSaving, setTemplateSaving] = useState(false);
  const [imagePackFormOpen, setImagePackFormOpen] = useState(false);
  const [editingImagePack, setEditingImagePack] = useState<ImagePack | null>(null);
  const [newImagePack, setNewImagePack] = useState({
    name: "",
    category: "GENERIC"
  });
  const [imagePackSaving, setImagePackSaving] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [uploadingImages, setUploadingImages] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [settingsRes, templatesRes, imagePacksRes, fbAccountsRes] =
        await Promise.all([
          fetch("/api/settings"),
          fetch("/api/templates"),
          fetch("/api/image-packs"),
          fetch("/api/fb-accounts"),
        ]);

      if (settingsRes.ok) {
        const settingsData = await settingsRes.json();
        setSettings(settingsData);
      }

      if (templatesRes.ok) {
        const templatesData = await templatesRes.json();
        setTemplates(templatesData);
      }

      if (imagePacksRes.ok) {
        const imagePacksData = await imagePacksRes.json();
        setImagePacks(imagePacksData);
      }

      if (fbAccountsRes.ok) {
        const fbAccountsData = await fbAccountsRes.json();
        setFbAccounts(fbAccountsData);
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      toast({
        title: "Error",
        description: "Failed to fetch settings data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const autoSaveSettings = async (updatedSettings: Settings) => {
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedSettings),
      });

      if (response.ok) {
        // Refresh classifier configuration to apply changes immediately
        await fetch("/api/settings/refresh", { method: "POST" });
      } else {
        throw new Error("Failed to save settings");
      }
    } catch (error) {
      console.error("Error auto-saving settings:", error);
      toast({
        title: "Error",
        description: "Failed to save changes automatically",
        variant: "destructive",
      });
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });

      if (response.ok) {
        // Refresh classifier configuration to apply changes immediately
        try {
          await fetch("/api/settings/refresh", { method: "POST" });
          toast({
            title: "Success",
            description: "Settings saved and applied successfully",
          });
        } catch (refreshError) {
          console.warn("Settings saved but failed to refresh classifier:", refreshError);
          toast({
            title: "Partial Success",
            description: "Settings saved but may require restart to take effect",
            variant: "destructive",
          });
        }
      } else {
        throw new Error("Failed to save settings");
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      toast({
        title: "Error",
        description: "Failed to save settings",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const addBrand = async () => {
    if (
      newBrand.trim() &&
      !settings.brand_blacklist.includes(newBrand.trim())
    ) {
      const updatedSettings = {
        ...settings,
        brand_blacklist: [...settings.brand_blacklist, newBrand.trim()],
      };
      setSettings(updatedSettings);
      setNewBrand("");
      await autoSaveSettings(updatedSettings);
    }
  };

  const removeBrand = async (brand: string) => {
    const updatedSettings = {
      ...settings,
      brand_blacklist: settings.brand_blacklist.filter((b) => b !== brand),
    };
    setSettings(updatedSettings);
    await autoSaveSettings(updatedSettings);
  };

  const addKeyword = async (type: "negative" | "service" | "iso") => {
    if (newKeyword.trim()) {
      const field = `${type}_keywords` as keyof Settings;
      const currentKeywords = settings[field] as string[];
      if (!currentKeywords.includes(newKeyword.trim())) {
        const updatedSettings = {
          ...settings,
          [field]: [...currentKeywords, newKeyword.trim()],
        };
        setSettings(updatedSettings);
        setNewKeyword("");
        await autoSaveSettings(updatedSettings);
      }
    }
  };

  const removeKeyword = async (
    type: "negative" | "service" | "iso",
    keyword: string
  ) => {
    const field = `${type}_keywords` as keyof Settings;
    const currentKeywords = settings[field] as string[];
    const updatedSettings = {
      ...settings,
      [field]: currentKeywords.filter((k) => k !== keyword),
    };
    setSettings(updatedSettings);
    await autoSaveSettings(updatedSettings);
  };

  const addModifier = async () => {
    if (
      newModifier.trim() &&
      !settings.allowed_brand_modifiers.includes(newModifier.trim())
    ) {
      const updatedSettings = {
        ...settings,
        allowed_brand_modifiers: [
          ...settings.allowed_brand_modifiers,
          newModifier.trim(),
        ],
      };
      setSettings(updatedSettings);
      setNewModifier("");
      await autoSaveSettings(updatedSettings);
    }
  };

  const removeModifier = async (modifier: string) => {
    const updatedSettings = {
      ...settings,
      allowed_brand_modifiers: settings.allowed_brand_modifiers.filter(
        (m) => m !== modifier
      ),
    };
    setSettings(updatedSettings);
    await autoSaveSettings(updatedSettings);
  };

  // Image pack management functions
  const handleNewImagePack = () => {
    setNewImagePack({ name: "", category: "GENERIC" });
    setEditingImagePack(null);
    setImagePackFormOpen(true);
  };

  const handleSaveImagePack = async () => {
    if (!newImagePack.name.trim()) {
      toast({
        title: "Error",
        description: "Image pack name is required",
        variant: "destructive",
      });
      return;
    }

    setImagePackSaving(true);
    try {
      const response = await fetch("/api/image-packs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newImagePack.name,
          category: newImagePack.category,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        toast({
          title: "Success",
          description: "Image pack created successfully",
        });
        
        // Upload files if selected
        if (selectedFiles && selectedFiles.length > 0) {
          await handleImageUpload(result.image_pack_id);
        }
        
        setImagePackFormOpen(false);
        setSelectedFiles(null);
        fetchData(); // Refresh data
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to create image pack");
      }
    } catch (error) {
      console.error("Error saving image pack:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create image pack",
        variant: "destructive",
      });
    } finally {
      setImagePackSaving(false);
    }
  };

  const handleImageUpload = async (packId: string) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    setUploadingImages(true);
    try {
      const formData = new FormData();
      Array.from(selectedFiles).forEach((file) => {
        formData.append("files", file);
      });
      formData.append("category", newImagePack.category);

      const response = await fetch(`/api/image-packs/${packId}/upload`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        toast({
          title: "Success",
          description: `Successfully uploaded ${result.uploaded_files.length} images`,
        });
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to upload images");
      }
    } catch (error) {
      console.error("Error uploading images:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to upload images",
        variant: "destructive",
      });
    } finally {
      setUploadingImages(false);
    }
  };

  const handleDeleteImagePack = async (packId: string) => {
    if (!confirm("Are you sure you want to delete this image pack? This cannot be undone.")) {
      return;
    }

    try {
      const response = await fetch(`/api/image-packs/${packId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Image pack deleted successfully",
        });
        fetchData(); // Refresh data
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to delete image pack");
      }
    } catch (error) {
      console.error("Error deleting image pack:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to delete image pack",
        variant: "destructive",
      });
    }
  };

  // Template management functions
  const handleNewTemplate = () => {
    setNewTemplate({
      name: "",
      category: "GENERIC",
      body: "",
      image_pack_id: "",
      is_default: false,
    });
    setEditingTemplate(null);
    setTemplateFormOpen(true);
  };

  const handleEditTemplate = (template: Template) => {
    setNewTemplate({
      name: template.name,
      category: template.category,
      body: template.body,
      image_pack_id: template.image_pack_id || "",
      is_default: template.is_default,
    });
    setEditingTemplate(template);
    setTemplateFormOpen(true);
  };

  const handleSaveTemplate = async () => {
    if (!newTemplate.name.trim() || !newTemplate.body.trim()) {
      toast({
        title: "Error",
        description: "Template name and body are required",
        variant: "destructive",
      });
      return;
    }

    setTemplateSaving(true);
    try {
      const url = editingTemplate
        ? `/api/templates/${editingTemplate.id}`
        : "/api/templates";
      const method = editingTemplate ? "PUT" : "POST";

      const payload = {
        name: newTemplate.name,
        category: newTemplate.category,
        body: newTemplate.body,
        image_pack_id: newTemplate.image_pack_id || null,
        is_default: newTemplate.is_default,
      };

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: editingTemplate
            ? "Template updated successfully"
            : "Template created successfully",
        });
        setTemplateFormOpen(false);
        fetchData(); // Refresh the template list
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to save template");
      }
    } catch (error) {
      console.error("Error saving template:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save template",
        variant: "destructive",
      });
    } finally {
      setTemplateSaving(false);
    }
  };

  const handleDeleteTemplate = (template: Template) => {
    setTemplateToDelete(template);
    setDeleteConfirmOpen(true);
  };

  const confirmDeleteTemplate = async () => {
    if (!templateToDelete) return;

    try {
      const response = await fetch(`/api/templates/${templateToDelete.id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Template deleted successfully",
        });
        setDeleteConfirmOpen(false);
        setTemplateToDelete(null);
        fetchData(); // Refresh the template list
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to delete template");
      }
    } catch (error) {
      console.error("Error deleting template:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to delete template",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading Settings...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
            CRM Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure templates, keywords, and system settings
          </p>
        </div>

        <Tabs defaultValue="general" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="general" className="flex items-center gap-2">
              <SettingsIcon className="h-4 w-4" />
              General
            </TabsTrigger>
            <TabsTrigger value="templates" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Templates
            </TabsTrigger>
            <TabsTrigger
              value="image-packs"
              className="flex items-center gap-2"
            >
              <Image className="h-4 w-4" />
              Image Packs
            </TabsTrigger>
            <TabsTrigger value="keywords" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Keywords
            </TabsTrigger>
            <TabsTrigger value="accounts" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Accounts
            </TabsTrigger>
          </TabsList>

          {/* General Settings Tab */}
          <TabsContent value="general" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Basic Configuration</CardTitle>
                <CardDescription>
                  Core settings for your Bravo CRM system
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="register_url">Registration URL</Label>
                    <Input
                      id="register_url"
                      value={settings.register_url}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          register_url: e.target.value,
                        }))
                      }
                      placeholder="https://welcome.bravocreations.com"
                    />
                  </div>
                  <div>
                    <Label htmlFor="phone">Phone Number</Label>
                    <Input
                      id="phone"
                      value={settings.phone}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          phone: e.target.value,
                        }))
                      }
                      placeholder="(760) 431-9977"
                    />
                  </div>
                  <div>
                    <Label htmlFor="ask_for">Ask For</Label>
                    <Input
                      id="ask_for"
                      value={settings.ask_for}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          ask_for: e.target.value,
                        }))
                      }
                      placeholder="Eugene"
                    />
                  </div>
                  <div>
                    <Label htmlFor="openai_api_key">OpenAI API Key</Label>
                    <Input
                      id="openai_api_key"
                      type="password"
                      value={settings.openai_api_key}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          openai_api_key: e.target.value,
                        }))
                      }
                      placeholder="sk-..."
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="scan_refresh">Scan Refresh (minutes)</Label>
                    <Input
                      id="scan_refresh"
                      type="number"
                      value={settings.scan_refresh_minutes}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          scan_refresh_minutes: parseInt(e.target.value),
                        }))
                      }
                      min="1"
                      max="60"
                    />
                  </div>
                  <div>
                    <Label htmlFor="max_comments">
                      Max Comments per Account/Day
                    </Label>
                    <Input
                      id="max_comments"
                      type="number"
                      value={settings.max_comments_per_account_per_day}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          max_comments_per_account_per_day: parseInt(
                            e.target.value
                          ),
                        }))
                      }
                      min="1"
                      max="50"
                    />
                  </div>
                </div>

                <Button
                  onClick={saveSettings}
                  disabled={saving}
                  className="w-full"
                >
                  <Save className="h-4 w-4 mr-2" />
                  {saving ? "Saving..." : "Save Settings"}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Templates Tab */}
          <TabsContent value="templates" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Comment Templates</CardTitle>
                    <CardDescription>
                      Manage comment templates for different post types
                    </CardDescription>
                  </div>
                  <Button onClick={handleNewTemplate}>
                    <Plus className="h-4 w-4 mr-2" />
                    New Template
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">{template.name}</h4>
                          <Badge variant="outline">{template.category}</Badge>
                          {template.is_default && (
                            <Badge variant="secondary">Default</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {template.body}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditTemplate(template)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteTemplate(template)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Image Packs Tab */}
          <TabsContent value="image-packs" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Image Packs</CardTitle>
                    <CardDescription>
                      Manage image collections for comment templates
                    </CardDescription>
                  </div>
                  <Button onClick={handleNewImagePack}>
                    <Plus className="h-4 w-4 mr-2" />
                    New Image Pack
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {imagePacks.map((pack) => (
                    <div
                      key={pack.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">{pack.name}</h4>
                          {pack.is_default && (
                            <Badge variant="secondary">Default</Badge>
                          )}
                        </div>
                        <div className="flex gap-2">
                          {pack.images.slice(0, 3).map((image, index) => (
                            <img
                              key={index}
                              src={image}
                              alt={`Image ${index + 1}`}
                              className="w-16 h-16 object-cover rounded border"
                            />
                          ))}
                          {pack.images.length > 3 && (
                            <div className="w-16 h-16 bg-muted rounded border flex items-center justify-center">
                              <span className="text-sm text-muted-foreground">
                                +{pack.images.length - 3}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            // TODO: Implement edit functionality
                            toast({
                              title: "Coming Soon",
                              description: "Edit functionality will be available in the next update",
                            });
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleDeleteImagePack(pack.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Keywords Tab */}
          <TabsContent value="keywords" className="space-y-6">
            {/* Brand Blacklist */}
            <Card>
              <CardHeader>
                <CardTitle>Brand Blacklist</CardTitle>
                <CardDescription>
                  Brands that will automatically flag posts for review
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Add brand name..."
                    value={newBrand}
                    onChange={(e) => setNewBrand(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && addBrand()}
                  />
                  <Button onClick={addBrand}>Add</Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {settings.brand_blacklist.map((brand) => (
                    <Badge
                      key={brand}
                      variant="outline"
                      className="text-red-700"
                    >
                      {brand}
                      <button
                        onClick={() => removeBrand(brand)}
                        className="ml-2 text-red-500 hover:text-red-700"
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Allowed Brand Modifiers */}
            <Card>
              <CardHeader>
                <CardTitle>Allowed Brand Modifiers</CardTitle>
                <CardDescription>
                  Phrases that allow brand mentions (e.g., "inspired by")
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Add modifier phrase..."
                    value={newModifier}
                    onChange={(e) => setNewModifier(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && addModifier()}
                  />
                  <Button onClick={addModifier}>Add</Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {settings.allowed_brand_modifiers.map((modifier) => (
                    <Badge
                      key={modifier}
                      variant="outline"
                      className="text-green-700"
                    >
                      {modifier}
                      <button
                        onClick={() => removeModifier(modifier)}
                        className="ml-2 text-green-500 hover:text-green-700"
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Keywords */}
            {[
              {
                key: "negative",
                title: "Negative Keywords",
                description: "Words that indicate posts to skip",
                color: "red",
              },
              {
                key: "service",
                title: "Service Keywords",
                description: "Words that indicate service requests",
                color: "blue",
              },
              {
                key: "iso",
                title: "ISO/Buy Keywords",
                description: "Words that indicate ISO or buying requests",
                color: "green",
              },
            ].map(({ key, title, description, color }) => (
              <Card key={key}>
                <CardHeader>
                  <CardTitle>{title}</CardTitle>
                  <CardDescription>{description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder={`Add ${key} keyword...`}
                      value={newKeyword}
                      onChange={(e) => setNewKeyword(e.target.value)}
                      onKeyPress={(e) =>
                        e.key === "Enter" && addKeyword(key as any)
                      }
                    />
                    <Button onClick={() => addKeyword(key as any)}>Add</Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(
                      settings[`${key}_keywords` as keyof Settings] as string[]
                    ).map((keyword) => (
                      <Badge
                        key={keyword}
                        variant="outline"
                        className={`text-${color}-700`}
                      >
                        {keyword}
                        <button
                          onClick={() => removeKeyword(key as any, keyword)}
                          className={`ml-2 text-${color}-500 hover:text-${color}-700`}
                        >
                          ×
                        </button>
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Facebook Accounts Tab */}
          <TabsContent value="accounts" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Facebook Accounts</CardTitle>
                    <CardDescription>
                      Manage Facebook accounts and posting quotas
                    </CardDescription>
                  </div>
                  <Button
                    onClick={() => {
                      /* Handle new account */
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    New Account
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {fbAccounts.map((account) => (
                    <div
                      key={account.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">
                            {account.display_name}
                          </h4>
                          <Badge
                            variant={
                              account.status === "ACTIVE"
                                ? "default"
                                : "secondary"
                            }
                          >
                            {account.status}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground space-y-1">
                          <p>Daily Quota: {account.daily_quota}</p>
                          {account.last_used_at && (
                            <p>
                              Last Used:{" "}
                              {new Date(account.last_used_at).toLocaleString()}
                            </p>
                          )}
                          {account.notes && <p>Notes: {account.notes}</p>}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Template Form Dialog */}
      <Dialog open={templateFormOpen} onOpenChange={setTemplateFormOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingTemplate ? "Edit Template" : "Create New Template"}
            </DialogTitle>
            <DialogDescription>
              {editingTemplate
                ? "Update your template details below."
                : "Create a new comment template with personalization."}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="template-name">Template Name</Label>
              <Input
                id="template-name"
                value={newTemplate.name}
                onChange={(e) =>
                  setNewTemplate((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="Enter template name"
              />
            </div>

            <div>
              <Label htmlFor="template-category">Category</Label>
              <Select
                value={newTemplate.category}
                onValueChange={(value) =>
                  setNewTemplate((prev) => ({ ...prev, category: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GENERIC">Generic</SelectItem>
                  <SelectItem value="ISO_PIVOT">ISO Pivot</SelectItem>
                  <SelectItem value="CAD">CAD</SelectItem>
                  <SelectItem value="CASTING">Casting</SelectItem>
                  <SelectItem value="SETTING">Setting</SelectItem>
                  <SelectItem value="ENGRAVING">Engraving</SelectItem>
                  <SelectItem value="ENAMEL">Enamel</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="template-body">Template Body</Label>
              <Textarea
                id="template-body"
                value={newTemplate.body}
                onChange={(e) =>
                  setNewTemplate((prev) => ({ ...prev, body: e.target.value }))
                }
                placeholder="Enter template text. Use placeholders: {{author_name}}, {{phone}}, {{register_url}}, {{ask_for}}"
                rows={4}
              />
              <p className="text-sm text-muted-foreground mt-1">
                Use placeholders: {"{"}{"{"} author_name {"}"}{"}"},  {"{"}{"{"} phone {"}"}{"}"},  {"{"}{"{"} register_url {"}"}{"}"},  {"{"}{"{"} ask_for {"}"}{"}"} 
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="template-default"
                checked={newTemplate.is_default}
                onCheckedChange={(checked) =>
                  setNewTemplate((prev) => ({ ...prev, is_default: checked }))
                }
              />
              <Label htmlFor="template-default">Set as default template</Label>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setTemplateFormOpen(false)}
              disabled={templateSaving}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveTemplate} disabled={templateSaving}>
              {templateSaving ? "Saving..." : editingTemplate ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Template</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{templateToDelete?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteTemplate}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Image Pack Form Dialog */}
      <Dialog open={imagePackFormOpen} onOpenChange={setImagePackFormOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingImagePack ? "Edit Image Pack" : "Create New Image Pack"}
            </DialogTitle>
            <DialogDescription>
              {editingImagePack
                ? "Update your image pack details below."
                : "Create a new image pack and upload images."}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="imagepack-name">Pack Name</Label>
              <Input
                id="imagepack-name"
                value={newImagePack.name}
                onChange={(e) =>
                  setNewImagePack((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="Enter image pack name"
              />
            </div>

            <div>
              <Label htmlFor="imagepack-category">Category</Label>
              <Select
                value={newImagePack.category}
                onValueChange={(value) =>
                  setNewImagePack((prev) => ({ ...prev, category: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GENERIC">Generic</SelectItem>
                  <SelectItem value="ISO_PIVOT">ISO Pivot</SelectItem>
                  <SelectItem value="CAD">CAD</SelectItem>
                  <SelectItem value="CASTING">Casting</SelectItem>
                  <SelectItem value="SETTING">Setting</SelectItem>
                  <SelectItem value="ENGRAVING">Engraving</SelectItem>
                  <SelectItem value="ENAMEL">Enamel</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="imagepack-files">Upload Images (Optional)</Label>
              <Input
                id="imagepack-files"
                type="file"
                multiple
                accept="image/*"
                onChange={(e) => setSelectedFiles(e.target.files)}
                className="cursor-pointer"
              />
              <p className="text-sm text-muted-foreground mt-1">
                You can upload images now or add them later. Max 10 images per pack, 5MB each.
              </p>
              {selectedFiles && selectedFiles.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm font-medium">Selected files:</p>
                  <div className="text-sm text-muted-foreground">
                    {Array.from(selectedFiles).map((file, index) => (
                      <div key={index}>{file.name} ({(file.size / 1024 / 1024).toFixed(2)}MB)</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setImagePackFormOpen(false);
                setSelectedFiles(null);
              }}
              disabled={imagePackSaving || uploadingImages}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveImagePack} 
              disabled={imagePackSaving || uploadingImages}
            >
              {imagePackSaving 
                ? "Creating..." 
                : uploadingImages 
                ? "Uploading..." 
                : editingImagePack 
                ? "Update" 
                : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Settings;
