import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { API_BASE_URL } from "../config/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Switch } from "./ui/switch";
import { Separator } from "./ui/separator";
import { Alert, AlertDescription } from "./ui/alert";
import {
  Loader2,
  Play,
  Square,
  MessageSquare,
  Settings,
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  EyeOff,
  RefreshCw,
  FileText,
  MessageCircle,
  Globe,
  User,
  Calendar,
  Check,
  X,
  ExternalLink,
  Database,
} from "lucide-react";

interface ActivityLog {
  id: string;
  timestamp: string;
  type:
    | "info"
    | "success"
    | "warning"
    | "error"
    | "post"
    | "comment"
    | "facebook";
  message: string;
  details?: any;
}

export const BotControl: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [postUrl, setPostUrl] = useState("");
  const [postText, setPostText] = useState("");
  const [maxScrolls, setMaxScrolls] = useState(20);
  const [continuousMode, setContinuousMode] = useState(true);
  const [clearDatabase, setClearDatabase] = useState(false);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const [isRefreshingLogs, setIsRefreshingLogs] = useState(false);
  const [showBrowserView, setShowBrowserView] = useState(false);
  const [browserScreenshot, setBrowserScreenshot] = useState<string | null>(
    null
  );
  const [browserInfo, setBrowserInfo] = useState<any>(null);
  const [isCapturingScreenshots, setIsCapturingScreenshots] = useState(false);

  const [liveScreenshot, setLiveScreenshot] = useState<string | null>(null);
  const [screenshotTimestamp, setScreenshotTimestamp] = useState<string | null>(
    null
  );
  const [currentUrl, setCurrentUrl] = useState<string | null>(null);
  const [isLoadingScreenshot, setIsLoadingScreenshot] = useState(false);

  const [isRefreshingComments, setIsRefreshingComments] = useState(false);
  const [retryLoading, setRetryLoading] = useState(false);

  const checkConnection = async () => {
    setRetryLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      setIsConnected(response.ok);
      if (response.ok) {
        fetchBotStatus();
      }
    } catch (error) {
      setIsConnected(false);
    } finally {
      setRetryLoading(false);
    }
  };

  const fetchBotStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/bot/status`);
      if (response.ok) {
        const status = await response.json();
        setBotStatus(status);

        // Add status update to activity log
        addActivityLog("info", `Bot status: ${status.current_status}`, status);
      }
    } catch (error) {
      console.error("Failed to fetch bot status:", error);
    }
  };

  const captureBrowserScreenshot = async () => {
    if (!isConnected) return;

    try {
      const response = await fetch(`${API_BASE_URL}/bot/screenshot`);
      if (response.ok) {
        const data = await response.json();
        setBrowserScreenshot(data.screenshot);
        setBrowserInfo({
          url: data.url,
          title: data.title,
          timestamp: data.timestamp,
        });
        addActivityLog("facebook", "Browser screenshot captured", data);
      }
    } catch (error) {
      console.error("Failed to capture screenshot:", error);
      addActivityLog("error", "Failed to capture browser screenshot", {
        error: error.toString(),
      });
    }
  };

  const fetchBrowserInfo = async () => {
    if (!isConnected) return;

    try {
      const response = await fetch(`${API_BASE_URL}/bot/browser-info`);
      if (response.ok) {
        const data = await response.json();
        setBrowserInfo(data);
      }
    } catch (error) {
      console.error("Failed to fetch browser info:", error);
    }
  };

  const fetchLiveScreenshot = async () => {
    if (!isConnected) return;

    setIsLoadingScreenshot(true);
    try {
      const response = await fetch(`${API_BASE_URL}/bot/live-screenshot`);
      if (response.ok) {
        const data = await response.json();
        setLiveScreenshot(data.screenshot);
        setScreenshotTimestamp(data.timestamp);
        setCurrentUrl(data.url);
        addActivityLog("facebook", "Live screenshot captured", data);
      } else {
        setLiveScreenshot(null);
        addActivityLog("warning", "Live screenshot not available", {
          error: "No screenshot data",
        });
      }
    } catch (error) {
      console.error("Failed to fetch live screenshot:", error);
      addActivityLog("error", "Failed to fetch live screenshot", {
        error: error.toString(),
      });
    } finally {
      setIsLoadingScreenshot(false);
    }
  };

  const startScreenshotCapture = () => {
    if (!isBotRunning) return;

    setIsCapturingScreenshots(true);
    addActivityLog("info", "Started capturing browser screenshots");

    // Capture first screenshot immediately
    captureBrowserScreenshot();

    // Set up interval for continuous capture
    const interval = setInterval(() => {
      if (isBotRunning && isCapturingScreenshots) {
        captureBrowserScreenshot();
      } else {
        clearInterval(interval);
      }
    }, 2000); // Capture every 2 seconds

    // Store interval ID for cleanup
    return () => clearInterval(interval);
  };

  const stopScreenshotCapture = () => {
    setIsCapturingScreenshots(false);
    addActivityLog("info", "Stopped capturing browser screenshots");
  };

  const addActivityLog = (
    type: ActivityLog["type"],
    message: string,
    details?: any
  ) => {
    const newLog: ActivityLog = {
      id: `log-${Date.now()}-${Math.random()}`,
      timestamp: new Date().toISOString(),
      type,
      message,
      details,
    };
  };

  useEffect(() => {
    checkConnection();
    // Poll bot status every 5 seconds
    const statusInterval = setInterval(() => {
      if (isConnected) {
        fetchBotStatus();
      }
    }, 5000);

    // Poll live screenshot every 5 seconds when bot is running
    const liveScreenshotInterval = setInterval(() => {
      if (isConnected && botStatus?.is_running) {
        fetchLiveScreenshot();
      }
    }, 5000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(liveScreenshotInterval);
    };
  }, [isConnected, botStatus?.is_running]);

  // Automatically start screenshot capture when bot starts running
  useEffect(() => {
    if (botStatus?.is_running && !isCapturingScreenshots) {
      setIsCapturingScreenshots(true);
      addActivityLog("info", "Auto-started browser screenshot capture");
    }
  }, [botStatus?.is_running, isCapturingScreenshots]);

  // Automatically stop screenshot capture when bot stops
  useEffect(() => {
    if (!botStatus?.is_running && isCapturingScreenshots) {
      setIsCapturingScreenshots(false);
      addActivityLog("info", "Auto-stopped browser screenshot capture");
    }
  }, [botStatus?.is_running, isCapturingScreenshots]);

  const handleStartBot = async () => {
    setLoading(true);
    setError(null);
    addActivityLog("info", "Starting bot...", {
      postUrl,
      maxScrolls,
      continuousMode,
    });

    try {
      const response = await fetch(`${API_BASE_URL}/bot/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          post_url: postUrl || undefined,
          max_scrolls: maxScrolls,
          continuous_mode: continuousMode,
          clear_database: clearDatabase,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Bot started successfully:", result);
        setError(null);
        addActivityLog("success", "Bot started successfully!", result);
        // Automatically show browser view when bot starts
        setShowBrowserView(true);

        // Start automatic screenshot capture
        setIsCapturingScreenshots(true);
        // Refresh status
        setTimeout(fetchBotStatus, 1000);
      } else {
        const errorData = await response.json();
        const errorMsg = `Failed to start bot: ${
          errorData.detail || "Unknown error"
        }`;
        setError(errorMsg);
        addActivityLog("error", errorMsg, errorData);
        console.error("Bot start failed:", errorData);
      }
    } catch (error) {
      const errorMsg = "Network error - failed to start bot";
      setError(errorMsg);
      addActivityLog("error", errorMsg, { error: error.toString() });
      console.error("Failed to start bot:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleStopBot = async () => {
    setLoading(true);
    setError(null);
    addActivityLog("warning", "Stopping bot...");

    try {
      const response = await fetch(`${API_BASE_URL}/bot/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: false }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Bot stopped successfully:", result);
        setError(null);
        addActivityLog("success", "Bot stopped successfully!", result);
        // Stop screenshot capture when bot stops
        setIsCapturingScreenshots(false);
        // Refresh status
        setTimeout(fetchBotStatus, 1000);
      } else {
        const errorData = await response.json();
        const errorMsg = `Failed to stop bot: ${
          errorData.detail || "Unknown error"
        }`;
        setError(errorMsg);
        addActivityLog("error", errorMsg, errorData);
        console.error("Bot stop failed:", errorData);
      }
    } catch (error) {
      const errorMsg = "Network error - failed to stop bot";
      setError(errorMsg);
      addActivityLog("error", errorMsg, { error: error.toString() });
      console.error("Failed to stop bot:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearDatabase = async () => {
    if (!isConnected) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/bot/database/clear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        const result = await response.json();
        addActivityLog("success", "Database cleared successfully", result);

        // Reset bot status if it exists
        if (botStatus) {
          setBotStatus((prev) => ({
            ...prev,
            posts_processed: 0,
            comments_posted: 0,
            comments_queued: 0,
          }));
        }
      } else {
        const errorData = await response.json();
        const errorMsg = `Failed to clear database: ${
          errorData.detail || "Unknown error"
        }`;
        addActivityLog("error", errorMsg, errorData);
      }
    } catch (error) {
      const errorMsg = "Network error - failed to clear database";
      addActivityLog("error", errorMsg, { error: error.toString() });
      console.error("Failed to clear database:", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "text-green-600";
      case "stopped":
        return "text-red-600";
      case "starting":
        return "text-yellow-600";
      case "error":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <CheckCircle className="h-4 w-4" />;
      case "stopped":
        return <XCircle className="h-4 w-4" />;
      case "starting":
        return <Clock className="h-4 w-4" />;
      case "error":
        return <XCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getActivityIcon = (type: ActivityLog["type"]) => {
    switch (type) {
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case "error":
        return <XCircle className="h-4 w-4 text-red-600" />;
      case "warning":
        return <Clock className="h-4 w-4 text-yellow-600" />;
      case "post":
        return <FileText className="h-4 w-4 text-blue-600" />;
      case "comment":
        return <MessageCircle className="h-4 w-4 text-purple-600" />;
      case "facebook":
        return <Globe className="h-4 w-4 text-blue-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  if (!isConnected) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Bot Control
          </CardTitle>
          <CardDescription>
            Connect to the bot API to control the Facebook comment bot
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <Activity className="h-4 w-4" />
            <AlertDescription>
              Cannot connect to the bot API. Please ensure the API server is
              running on{" "}
              <code className="bg-gray-100 px-2 py-1 rounded">
                {API_BASE_URL}
              </code>
            </AlertDescription>
          </Alert>
          <Button
            onClick={checkConnection}
            className="mt-4"
            disabled={retryLoading}
          >
            {retryLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing Connection...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry Connection
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isBotRunning = botStatus?.is_running || false;

  return (
    <div className="w-full space-y-6 max-w-none">
      {/* Bot Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Bot Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          {botStatus ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div
                  className={`text-2xl font-bold ${getStatusColor(
                    botStatus.current_status
                  )}`}
                >
                  {getStatusIcon(botStatus.current_status)}
                </div>
                <p className="text-sm text-gray-600 mt-1">Status</p>
                <p className="font-medium">{botStatus.current_status}</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {botStatus.posts_processed || 0}
                </div>
                <p className="text-sm text-gray-600 mt-1">Posts Processed</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {botStatus.comments_queued || 0}
                </div>
                <p className="text-sm text-gray-600 mt-1">Comments Queued</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {botStatus.comments_posted || 0}
                </div>
                <p className="text-sm text-gray-600 mt-1">Comments Posted</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
              <p className="text-gray-600">Loading bot status...</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bot Control Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Bot Control
          </CardTitle>
          <CardDescription>
            Start or stop the Facebook comment bot
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="postUrl">
                Facebook Group/Post URL (Optional)
              </Label>
              <Input
                id="postUrl"
                placeholder="https://www.facebook.com/groups/..."
                value={postUrl}
                onChange={(e) => setPostUrl(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="maxScrolls">Max Scrolls</Label>
              <Input
                id="maxScrolls"
                type="number"
                min="1"
                max="100"
                value={maxScrolls}
                onChange={(e) => setMaxScrolls(parseInt(e.target.value) || 20)}
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="continuousMode"
              checked={continuousMode}
              onCheckedChange={setContinuousMode}
            />
            <Label htmlFor="continuousMode">Continuous Mode</Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="clearDatabase"
              checked={clearDatabase}
              onCheckedChange={setClearDatabase}
            />
            <Label
              htmlFor="clearDatabase"
              className="text-orange-600 font-medium"
            >
              Clear Database on Startup (Testing)
            </Label>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleStartBot}
              disabled={loading || isBotRunning}
              className="flex-1"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {isBotRunning ? "Bot Running" : "Start Bot"}
            </Button>
            <Button
              onClick={handleStopBot}
              disabled={loading || !isBotRunning}
              variant="destructive"
              className="flex-1"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2" />
              ) : (
                <Square className="h-4 w-4 mr-2" />
              )}
              Stop Bot
            </Button>
          </div>

          {/* Database Management */}
          <div className="flex gap-2">
            <Button
              onClick={handleClearDatabase}
              disabled={loading || isBotRunning}
              variant="outline"
              className="flex-1 border-orange-300 text-orange-700 hover:bg-orange-50"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Clear Database Now
            </Button>
          </div>

          {/* Status Info */}
          {botStatus && (
            <div className="text-sm text-gray-600">
              <p>
                <strong>Last Activity:</strong>{" "}
                {botStatus.last_activity
                  ? new Date(botStatus.last_activity).toLocaleString()
                  : "Never"}
              </p>
              {botStatus.start_time && (
                <p>
                  <strong>Started:</strong>{" "}
                  {new Date(botStatus.start_time).toLocaleString()}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Live Browser View */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Live Browser View
            </CardTitle>
          </div>
          <CardDescription>
            Watch the bot navigate Facebook in real-time
          </CardDescription>
        </CardHeader>
        <CardContent>
          {showBrowserView ? (
            <div className="space-y-4">
              {/* Browser Info */}
              {browserInfo && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <strong className="text-blue-900">Current URL:</strong>
                      <p className="text-blue-800 break-all">
                        {browserInfo.url || "Unknown"}
                      </p>
                    </div>
                    <div>
                      <strong className="text-blue-900">Page Title:</strong>
                      <p className="text-blue-800">
                        {browserInfo.title || "Unknown"}
                      </p>
                    </div>
                    <div>
                      <strong className="text-blue-900">Last Updated:</strong>
                      <p className="text-blue-800">
                        {browserInfo.timestamp
                          ? new Date(browserInfo.timestamp).toLocaleTimeString()
                          : "Never"}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Browser Screenshot */}
              {browserScreenshot ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">Live Browser View</h4>
                    <Badge variant="outline">Auto-capturing every 2s</Badge>
                  </div>
                  <div className="border rounded-lg overflow-hidden bg-white">
                    <img
                      src={browserScreenshot}
                      alt="Live browser view"
                      className="w-full h-auto max-h-96 object-contain"
                      style={{ imageRendering: "pixelated" }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 text-center">
                    This is what the bot currently sees in the browser
                  </p>
                </div>
              ) : !isBotRunning ? (
                <div className="text-center py-12 text-gray-500">
                  <Globe className="h-12 w-12 mx-auto mb-4" />
                  <p className="mb-4">No browser view available</p>
                  <div className="space-y-2 text-sm">
                    <p>• Start the bot first</p>
                    <p>
                      • Browser view will automatically appear once the bot is
                      running
                    </p>
                  </div>
                </div>
              ) : null}

              {/* Live Browser View */}
              {liveScreenshot && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">Live Browser Window</h4>
                    <div className="flex items-center gap-2">
                      {screenshotTimestamp && (
                        <span className="text-xs text-gray-500">
                          {new Date(screenshotTimestamp).toLocaleTimeString()}
                        </span>
                      )}

                      <Badge variant="outline" className="text-green-600">
                        Live View
                      </Badge>
                    </div>
                  </div>
                  <div className="border rounded-lg overflow-hidden bg-white">
                    <img
                      src={liveScreenshot}
                      alt="Live Browser View"
                      className="w-full h-96 border-0 object-contain"
                    />
                  </div>
                  {currentUrl && (
                    <p className="text-xs text-gray-500 text-center">
                      Current URL: {currentUrl}
                    </p>
                  )}
                  <p className="text-xs text-gray-500 text-center">
                    Live screenshot of the Chrome browser the bot is using -
                    updates every 5 seconds!
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Eye className="h-8 w-8 mx-auto mb-2" />
              <p>Browser view will appear automatically when the bot starts</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
