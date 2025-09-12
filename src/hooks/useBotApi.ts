import { useState, useCallback } from "react";
import { API_BASE_URL } from "../config/api";

export interface BotStatus {
  is_running: boolean;
  start_time: string | null;
  last_activity: string | null;
  posts_processed: number;
  comments_posted: number;
  current_status: string;
}

export interface CommentRequest {
  post_url: string;
  post_text?: string;
}

export interface CommentResponse {
  success: boolean;
  comment?: string;
  message: string;
  post_type?: string;
}

export interface BotStartRequest {
  post_url?: string;
  max_scrolls?: number;
  continuous_mode?: boolean;
}

export const useBotApi = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApiError = useCallback((error: any) => {
    console.error("API Error:", error);
    if (error.response?.data?.detail) {
      setError(error.response.data.detail);
    } else if (error.message) {
      setError(error.message);
    } else {
      setError("An unexpected error occurred");
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Get bot status
  const getBotStatus = useCallback(async (): Promise<BotStatus> => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/bot/status`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      handleApiError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [handleApiError]);

  // Start bot
  const startBot = useCallback(
    async (request: BotStartRequest = {}): Promise<void> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/bot/start`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`
          );
        }

        const data = await response.json();
        console.log("Bot started:", data);
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [handleApiError]
  );

  // Stop bot
  const stopBot = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/bot/stop`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ force: false }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const data = await response.json();
      console.log("Bot stopped:", data);
    } catch (error) {
      handleApiError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [handleApiError]);

  // Generate comment
  const generateComment = useCallback(
    async (request: CommentRequest): Promise<CommentResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/bot/comment`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`
          );
        }

        const data = await response.json();
        return data;
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [handleApiError]
  );

  // Get configuration
  const getConfig = useCallback(async (): Promise<any> => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/config`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      handleApiError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [handleApiError]);

  // Health check
  const healthCheck = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return response.ok;
    } catch (error) {
      console.error("Health check failed:", error);
      return false;
    }
  }, []);

  // Get logs
  const getLogs = useCallback(
    async (limit: number = 100): Promise<any> => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/logs?limit=${limit}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [handleApiError]
  );

  return {
    loading,
    error,
    clearError,
    getBotStatus,
    startBot,
    stopBot,
    generateComment,
    getConfig,
    healthCheck,
    getLogs,
  };
};
