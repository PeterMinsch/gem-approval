/**
 * Custom hook for AI message generation
 * Handles API calls, loading states, and error handling for Smart Launcher
 */

import { useState, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

export interface MessageGenerationResult {
  success: boolean;
  message: string;
  author_name: string;
  generation_method: 'ai' | 'template';
  character_count: number;
  generation_time_seconds: number;
  post_type: string;
  messenger_url: string | null;
  post_images: string[];
  post_screenshot: string | null;
  has_images: boolean;
}

export interface MessageGenerationError {
  message: string;
  details?: string;
}

export interface UseMessageGenerationReturn {
  generateMessage: (commentId: string) => Promise<MessageGenerationResult | null>;
  isGenerating: boolean;
  error: MessageGenerationError | null;
  clearError: () => void;
}

export const useMessageGeneration = (): UseMessageGenerationReturn => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<MessageGenerationError | null>(null);

  const generateMessage = useCallback(async (commentId: string): Promise<MessageGenerationResult | null> => {
    console.log(`🎯 Starting message generation for comment ${commentId}`);
    
    setIsGenerating(true);
    setError(null);

    try {
      const startTime = performance.now();
      
      // Call the message generation API
      const response = await fetch(`${API_BASE_URL}/generate-message/${commentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors', // Explicitly handle CORS
      });

      const endTime = performance.now();
      const requestTime = Math.round(endTime - startTime);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || 
          `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const result: MessageGenerationResult = await response.json();
      
      console.log(`✅ Message generated successfully in ${requestTime}ms:`, {
        method: result.generation_method,
        chars: result.character_count,
        author: result.author_name
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      
      console.error('❌ Message generation failed:', errorMessage);
      
      setError({
        message: 'Failed to generate message',
        details: errorMessage
      });
      
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    generateMessage,
    isGenerating,
    error,
    clearError
  };
};