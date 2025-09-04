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

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Settings saved successfully",
        });
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

  const addBrand = () => {
    if (
      newBrand.trim() &&
      !settings.brand_blacklist.includes(newBrand.trim())
    ) {
      setSettings((prev) => ({
        ...prev,
        brand_blacklist: [...prev.brand_blacklist, newBrand.trim()],
      }));
      setNewBrand("");
    }
  };

  const removeBrand = (brand: string) => {
    setSettings((prev) => ({
      ...prev,
      brand_blacklist: prev.brand_blacklist.filter((b) => b !== brand),
    }));
  };

  const addKeyword = (type: "negative" | "service" | "iso") => {
    if (newKeyword.trim()) {
      const field = `${type}_keywords` as keyof Settings;
      const currentKeywords = settings[field] as string[];
      if (!currentKeywords.includes(newKeyword.trim())) {
        setSettings((prev) => ({
          ...prev,
          [field]: [...currentKeywords, newKeyword.trim()],
        }));
        setNewKeyword("");
      }
    }
  };

  const removeKeyword = (
    type: "negative" | "service" | "iso",
    keyword: string
  ) => {
    const field = `${type}_keywords` as keyof Settings;
    const currentKeywords = settings[field] as string[];
    setSettings((prev) => ({
      ...prev,
      [field]: currentKeywords.filter((k) => k !== keyword),
    }));
  };

  const addModifier = () => {
    if (
      newModifier.trim() &&
      !settings.allowed_brand_modifiers.includes(newModifier.trim())
    ) {
      setSettings((prev) => ({
        ...prev,
        allowed_brand_modifiers: [
          ...prev.allowed_brand_modifiers,
          newModifier.trim(),
        ],
      }));
      setNewModifier("");
    }
  };

  const removeModifier = (modifier: string) => {
    setSettings((prev) => ({
      ...prev,
      allowed_brand_modifiers: prev.allowed_brand_modifiers.filter(
        (m) => m !== modifier
      ),
    }));
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
                  <Button
                    onClick={() => {
                      /* Handle new image pack */
                    }}
                  >
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
                placeholder="Enter template text. Use {{author_name}} for personalization, {{phone}} for phone number, {{register_url}} for website, and {{ask_for}} for contact name."
                rows={4}
              />
              <p className="text-sm text-muted-foreground mt-1">
                Use placeholders: {{author_name}}, {{phone}}, {{register_url}}, {{ask_for}}
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
    </div>
  );
};

export default Settings;
