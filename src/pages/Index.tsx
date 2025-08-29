import { BotControl } from "../components/BotControl";
import { Button } from "@/components/ui/button";
import { RefreshCw, Bot, Settings, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

const Index = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                Bravo Bot Control Center
              </h1>
              <p className="text-muted-foreground mt-1">
                Control your Facebook comment bot and manage posts through the
                integrated CRM Dashboard
              </p>
            </div>
            <Button variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Status
            </Button>
          </div>

          {/* Navigation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <Link to="/settings">
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <Settings className="h-8 w-8 text-green-600" />
                    <div>
                      <CardTitle>Settings</CardTitle>
                      <CardDescription>
                        Configure templates, keywords, and system preferences
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            </Link>

            <Card className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <MessageSquare className="h-8 w-8 text-purple-600" />
                  <div>
                    <CardTitle>Bot Control</CardTitle>
                    <CardDescription>
                      Start, stop, and monitor your Facebook bot
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Card>
          </div>

          {/* Bot Control Section */}
          <div className="mt-8 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Bot className="h-6 w-6 text-blue-600" />
              <h2 className="text-xl font-semibold text-gray-900">
                Bot Control
              </h2>
            </div>
            <BotControl />
          </div>

          {/* Info Section */}
          <div className="mt-8">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">
                How It Works
              </h3>
              <div className="space-y-2 text-blue-800">
                <p>
                  1. <strong>Bot scans Facebook groups</strong> and applies your
                  rules to detect relevant posts
                </p>
                <p>
                  2. <strong>Posts appear in CRM Dashboard</strong> with
                  AI-drafted comments using templates
                </p>
                <p>
                  3. <strong>Review and edit</strong> - view post content, edit
                  comments, and attach images
                </p>
                <p>
                  4. <strong>Approve and post</strong> - one-click approval
                  sends comments to Facebook
                </p>
                <p>
                  5. <strong>Track everything</strong> - from initial scan to
                  final engagement
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
