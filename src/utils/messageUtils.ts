/**
 * Utility functions for Smart Launcher message system
 * Handles clipboard operations and Messenger URL launching
 */

import { API_BASE_URL } from '../config/api';

/**
 * Fetch image from URL and convert to Blob
 * Handles CORS issues and Facebook CDN images
 */
export const fetchImageAsBlob = async (imageUrl: string): Promise<Blob | null> => {
  try {
    console.log(`🖼️ Fetching image: ${imageUrl}`);
    
    // Validate URL
    if (!imageUrl || imageUrl === 'null' || imageUrl === 'undefined') {
      console.warn('⚠️ Invalid image URL provided');
      return null;
    }
    
    // Handle base64 data URLs directly
    if (imageUrl.startsWith('data:image')) {
      console.log('📸 Processing base64 image...');
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      console.log(`✅ Converted base64 image to blob (${blob.size} bytes, type: ${blob.type})`);
      return blob;
    }
    
    // For Facebook CDN URLs, use proxy immediately (skip direct fetch)
    if (imageUrl.includes('scontent') || imageUrl.includes('fbcdn.net')) {
      console.log('🔄 Facebook CDN detected, using proxy directly...');
      const cleanUrl = imageUrl.trim();
      try {
        const proxyUrl = `${API_BASE_URL}/proxy-image?url=${encodeURIComponent(cleanUrl)}`;
        const response = await fetch(proxyUrl);
        
        if (response.ok) {
          const blob = await response.blob();
          console.log(`✅ Fetched Facebook image via proxy (${blob.size} bytes)`);
          return blob;
        }
      } catch (proxyError) {
        console.error('❌ Proxy fetch failed:', proxyError);
      }
      return null;
    }
    
    // Clean up URL if needed
    const cleanUrl = imageUrl.trim();
    console.log(`🔗 Attempting to fetch from: ${cleanUrl.substring(0, 100)}...`);
    
    // Try direct fetch first
    try {
      const response = await fetch(cleanUrl, {
        mode: 'cors',
        credentials: 'omit'
      });
      
      console.log(`📡 Direct fetch response: ${response.status} ${response.statusText}`);
      
      if (response.ok) {
        const blob = await response.blob();
        console.log(`✅ Fetched image directly (${blob.size} bytes, type: ${blob.type})`);
        return blob;
      } else {
        console.warn(`⚠️ Direct fetch failed with status: ${response.status}`);
      }
    } catch (corsError) {
      console.warn('⚠️ Direct fetch failed (likely CORS):', corsError.message || corsError);
      
      // Try backend proxy as fallback
      try {
        const proxyUrl = `${API_BASE_URL}/proxy-image?url=${encodeURIComponent(cleanUrl)}`;
        console.log(`🔄 Trying proxy: ${proxyUrl.substring(0, 80)}...`);
        const response = await fetch(proxyUrl);
        
        if (response.ok) {
          const blob = await response.blob();
          console.log(`✅ Fetched image via proxy (${blob.size} bytes)`);
          return blob;
        }
      } catch (proxyError) {
        console.error('❌ Proxy fetch also failed:', proxyError);
      }
    }
    
    return null;
  } catch (error) {
    console.error('❌ Failed to fetch image:', error);
    return null;
  }
};

/**
 * Copy text and image to clipboard using modern Clipboard API
 * Supports multi-format clipboard for single paste operation
 */
export const copyTextAndImageToClipboard = async (
  text: string, 
  imageBlob: Blob | null
): Promise<boolean> => {
  try {
    // Check for modern clipboard API support
    if (!navigator.clipboard || !window.ClipboardItem) {
      console.warn('⚠️ Modern clipboard API not supported, falling back to text-only');
      return copyToClipboard(text);
    }
    
    // Build clipboard items based on available data
    const clipboardItems: Record<string, Blob> = {
      'text/plain': new Blob([text], { type: 'text/plain' })
    };
    
    if (imageBlob) {
      // Ensure image is in a supported format
      const imageType = imageBlob.type || 'image/png';
      if (imageType.startsWith('image/')) {
        clipboardItems[imageType] = imageBlob;
        console.log(`📋 Preparing clipboard with text and ${imageType}`);
      } else {
        console.warn(`⚠️ Unsupported image type: ${imageType}`);
      }
    } else {
      console.log('📋 Preparing clipboard with text only (no image)');
    }
    
    // Write to clipboard
    const clipboardItem = new ClipboardItem(clipboardItems);
    await navigator.clipboard.write([clipboardItem]);
    
    console.log('✅ Successfully copied text and image to clipboard');
    return true;
    
  } catch (error) {
    console.error('❌ Multi-format clipboard failed, trying text-only fallback:', error);
    // Fallback to text-only copy
    return copyToClipboard(text);
  }
};

/**
 * Copy text to clipboard using modern Clipboard API with fallback
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    // Modern Clipboard API (preferred)
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      console.log('✅ Message copied to clipboard via Clipboard API');
      return true;
    }
    
    // Fallback for older browsers or non-HTTPS
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    
    if (successful) {
      console.log('✅ Message copied to clipboard via fallback method');
      return true;
    } else {
      throw new Error('Copy command failed');
    }
  } catch (error) {
    console.error('❌ Failed to copy to clipboard:', error);
    return false;
  }
};

/**
 * Open Facebook Messenger conversation in new tab
 */
export const openMessengerConversation = (messengerUrl: string, allowRedirect: boolean = true): boolean => {
  try {
    if (!messengerUrl) {
      console.error('❌ No Messenger URL provided');
      return false;
    }
    
    console.log(`🔗 Attempting to open: ${messengerUrl}`);
    
    // Open Messenger in new tab
    const newWindow = window.open(messengerUrl, '_blank', 'noopener,noreferrer');
    
    if (newWindow) {
      console.log(`✅ Opened Messenger conversation in new tab: ${messengerUrl}`);
      // Focus the new window (if popup blockers allow)
      newWindow.focus();
      return true;
    } else {
      // Fallback if popup is blocked - only redirect if allowed
      if (allowRedirect) {
        console.warn('⚠️ Popup blocked, redirecting main window');
        window.location.href = messengerUrl;
        return true;
      } else {
        console.warn('⚠️ Popup blocked, redirect disabled for Selenium mode - staying on current page');
        return false; // Failed to open, but don't redirect main page
      }
    }
  } catch (error) {
    console.error('❌ Failed to open Messenger conversation:', error);
    return false;
  }
};

/**
 * Extract Facebook ID from profile URL (reusing existing logic)
 */
export const extractFacebookIdFromProfileUrl = (profileUrl: string): string | null => {
  if (!profileUrl || !profileUrl.includes('facebook.com')) {
    return null;
  }
  
  console.debug(`FRONTEND_ID_EXTRACTION: Processing URL: '${profileUrl}' (length: ${profileUrl.length})`);
  
  try {
    if (profileUrl.includes('profile.php?id=')) {
      // Extract numeric ID: facebook.com/profile.php?id=123456789
      const match = profileUrl.match(/id=([^&]+)/);
      const result = match ? match[1] : null;
      console.debug(`FRONTEND_ID_EXTRACTION: Traditional profile - extracted: '${result}'`);
      return result;
    } else if (profileUrl.includes('/messages/')) {
      // Handle messenger URLs: /messages/t/123456789 or /messages/e2ee/t/123456789
      console.debug(`FRONTEND_ID_EXTRACTION: Processing messenger URL: '${profileUrl}'`);
      
      const messengerMatch = profileUrl.match(/\/messages\/(?:e2ee\/)?t\/([^/?]+)/);
      const result = messengerMatch ? messengerMatch[1] : null;
      console.debug(`FRONTEND_ID_EXTRACTION: Messenger - extracted: '${result}'`);
      return result;
    } else if (profileUrl.includes('/groups/') && profileUrl.includes('/user/')) {
      // Handle group-based profile URLs
      // Extract from: /groups/[groupid]/user/[userid]/
      console.debug(`FRONTEND_ID_EXTRACTION: Processing group-based URL: '${profileUrl}'`);
      
      const userMatch = profileUrl.match(/\/user\/([^/?]+)/);
      const result = userMatch ? userMatch[1] : null;
      console.debug(`FRONTEND_ID_EXTRACTION: Group-based - extracted: '${result}'`);
      return result;
    } else {
      // Extract username: facebook.com/john.smith
      const pathMatch = profileUrl.match(/facebook\.com\/([^/?]+)/);
      const path = pathMatch ? pathMatch[1] : null;
      
      // Filter out obvious non-profile paths
      if (path && !['profile.php', 'photo', 'events', 'pages', 'messages'].includes(path)) {
        console.debug(`FRONTEND_ID_EXTRACTION: Username - extracted: '${path}'`);
        return path;
      }
    }
  } catch (error) {
    console.error('FRONTEND_ID_EXTRACTION: Exception during extraction:', error);
  }
  
  console.debug('FRONTEND_ID_EXTRACTION: No valid ID found');
  return null;
};

/**
 * Create Facebook Messenger link from profile URL
 */
export const createMessengerLink = (profileUrl: string): string | null => {
  const facebookId = extractFacebookIdFromProfileUrl(profileUrl);
  if (facebookId) {
    const messengerUrl = `https://www.facebook.com/messages/t/${facebookId}`;
    console.debug(`FRONTEND_MESSENGER: Created link: ${messengerUrl}`);
    return messengerUrl;
  }
  console.debug('FRONTEND_MESSENGER: Could not create link - no valid Facebook ID');
  return null;
};

/**
 * Main Smart Launcher function: Generate message, copy to clipboard, open Messenger
 */
export interface SmartLauncherResult {
  success: boolean;
  message?: string;
  clipboardSuccess: boolean;
  messengerSuccess: boolean;
  hasImage: boolean;
  error?: string;
}

export const executeSmartLauncher = async (
  message: string,
  messengerUrl: string,
  imageUrls?: string[],
  debugMode: boolean = false,
  allowRedirect: boolean = true
): Promise<SmartLauncherResult> => {
  console.log('🚀 Executing Smart Launcher with images...');
  
  let imageBlob: Blob | null = null;
  let hasImage = false;
  
  // Step 1: Try to fetch the first available image
  if (imageUrls && imageUrls.length > 0) {
    console.log(`📷 Processing ${imageUrls.length} image(s)...`);
    
    for (const imageUrl of imageUrls) {
      if (imageUrl) {
        imageBlob = await fetchImageAsBlob(imageUrl);
        if (imageBlob) {
          hasImage = true;
          console.log(`✅ Successfully fetched image (${imageBlob.size} bytes)`);
          break; // Use first successful image
        }
      }
    }
    
    if (!hasImage) {
      console.warn('⚠️ No images could be fetched, proceeding with text-only');
    }
  }
  
  // Step 2: Copy message (and image if available) to clipboard
  const clipboardSuccess = await copyTextAndImageToClipboard(message, imageBlob);
  
  // Step 3: Small delay to ensure clipboard write completes
  // This is crucial for multi-format clipboard to work properly
  if (hasImage && clipboardSuccess) {
    console.log('⏳ Waiting for clipboard to settle...');
    await new Promise(resolve => setTimeout(resolve, 500)); // 500ms delay
  }
  
  // Step 4: Open Messenger conversation (unless in debug mode)
  let messengerSuccess = true;
  if (!debugMode) {
    messengerSuccess = openMessengerConversation(messengerUrl, allowRedirect);
  } else {
    console.log('🐛 Debug mode: Messenger not opened. Manually navigate to:', messengerUrl);
    console.log('📋 Clipboard should contain:', hasImage ? 'Text + Image' : 'Text only');
    console.log('🎯 Try pasting in any app to test');
  }
  
  const result: SmartLauncherResult = {
    success: clipboardSuccess && messengerSuccess,
    message: message,
    clipboardSuccess,
    messengerSuccess,
    hasImage
  };
  
  if (result.success) {
    console.log(`✅ Smart Launcher executed successfully ${hasImage ? 'with image' : 'text-only'}`);
  } else {
    const issues = [];
    if (!clipboardSuccess) issues.push('clipboard');
    if (!messengerSuccess) issues.push('messenger');
    console.warn(`⚠️ Smart Launcher partial failure: ${issues.join(', ')}`);
  }
  
  return result;
};

/**
 * Get user-friendly instructions based on Smart Launcher result
 */
export const getInstructionMessage = (result: SmartLauncherResult): string => {
  const imageText = result.hasImage ? " (with image)" : "";
  
  if (result.success) {
    return `Message${imageText} copied to clipboard! Messenger opened - just paste (Ctrl+V) and send.`;
  } else if (result.clipboardSuccess && !result.messengerSuccess) {
    return `Message${imageText} copied to clipboard! Please manually navigate to Facebook Messenger and paste.`;
  } else if (!result.clipboardSuccess && result.messengerSuccess) {
    return "Messenger opened! Please copy the message manually and paste it.";
  } else {
    return "Please copy the message manually and navigate to Facebook Messenger.";
  }
};

/**
 * Selenium Automation Result interface
 */
export interface SeleniumAutomationResult {
  success: boolean;
  message: string;
  duration?: string;
  error?: string;
  method: 'selenium';
}

/**
 * Execute full Selenium automation - paste message and upload images automatically
 */
export const executeSeleniumAutomation = async (
  message: string,
  messengerUrl: string,
  imageUrls?: string[],
  sessionId?: string
): Promise<SeleniumAutomationResult> => {
  console.log('🚀 Executing Selenium automation...');
  
  try {
    // Extract recipient from messenger URL
    const recipient = extractFacebookIdFromProfileUrl(messengerUrl) || messengerUrl;
    
    if (!recipient) {
      throw new Error('Could not extract recipient from Messenger URL');
    }
    
    // Separate base64 images from file paths
    const base64Images: string[] = [];
    const filePaths: string[] = [];
    
    if (imageUrls && imageUrls.length > 0) {
      for (const url of imageUrls) {
        if (url.startsWith('data:image')) {
          base64Images.push(url);
        } else {
          filePaths.push(url);
        }
      }
    }
    
    console.log(`📷 Image analysis: ${base64Images.length} base64 images, ${filePaths.length} file paths`);
    
    // Convert base64 images to temporary files if needed
    let convertedFilePaths: string[] = [];
    if (base64Images.length > 0) {
      console.log('🔄 Converting base64 post images to temporary files...');
      
      const conversionResponse = await fetch(`${API_BASE_URL}/convert-base64-images`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base64_images: base64Images
        })
      });
      
      if (!conversionResponse.ok) {
        throw new Error(`Base64 conversion failed: ${conversionResponse.status}`);
      }
      
      const conversionResult = await conversionResponse.json();
      if (conversionResult.success) {
        convertedFilePaths = conversionResult.file_paths;
        console.log(`✅ Converted ${convertedFilePaths.length} base64 images to temporary files`);
      } else {
        console.warn(`⚠️ Base64 conversion failed: ${conversionResult.error}`);
      }
    }
    
    // Combine all image paths (converted base64 + original file paths)
    const imagePaths = [...convertedFilePaths, ...filePaths];
    
    // Generate unique session ID if not provided
    const actualSessionId = sessionId || `user_${Date.now()}`;
    
    console.log(`🎯 Sending via Selenium - Recipient: ${recipient}, Session: ${actualSessionId}`);
    console.log(`📝 Message: ${message.substring(0, 100)}...`);
    console.log(`🖼️ Total images: ${imagePaths.length} (${convertedFilePaths.length} post images + ${filePaths.length} gallery images)`);
    console.log(`🔗 Target URL: ${messengerUrl}`);
    
    // Call the messenger automation API
    console.log('📡 Making API request to Selenium backend...');
    const response = await fetch(`${API_BASE_URL}/messenger/send-message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      mode: 'cors',
      body: JSON.stringify({
        session_id: actualSessionId,
        recipient: recipient,
        message: message,
        images: imagePaths
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (data.status === 'success') {
      console.log(`✅ Selenium automation completed successfully in ${data.duration}`);
      return {
        success: true,
        message: `Message sent automatically via browser automation in ${data.duration}!`,
        duration: data.duration,
        method: 'selenium'
      };
    } else {
      console.error(`❌ Selenium automation failed: ${data.error}`);
      return {
        success: false,
        message: `Automation failed: ${data.error}`,
        error: data.error,
        method: 'selenium'
      };
    }
    
  } catch (error) {
    console.error('❌ Selenium automation error:', error);
    return {
      success: false,
      message: `Automation error: ${error.message}`,
      error: error.message,
      method: 'selenium'
    };
  }
};

/**
 * Enhanced Smart Launcher with automation mode selection
 */
export interface EnhancedSmartLauncherResult {
  success: boolean;
  message: string;
  method: 'clipboard' | 'selenium';
  clipboardSuccess?: boolean;
  messengerSuccess?: boolean;
  hasImage?: boolean;
  duration?: string;
  error?: string;
}

export const executeEnhancedSmartLauncher = async (
  message: string,
  messengerUrl: string,
  imageUrls?: string[],
  options: {
    method: 'clipboard' | 'selenium';
    debugMode?: boolean;
    sessionId?: string;
  } = { method: 'clipboard' }
): Promise<EnhancedSmartLauncherResult> => {
  console.log(`🚀 Executing Enhanced Smart Launcher - Method: ${options.method}`);
  
  if (options.method === 'selenium') {
    // For Selenium mode: Open Messenger tab AND run automation
    console.log('🎯 Selenium mode: Opening Messenger tab + running browser automation');
    
    // Step 1: Open Messenger tab for reference (but don't redirect main page if popup blocked)
    console.log(`🌐 Opening reference Messenger tab: ${messengerUrl}`);
    const messengerTabSuccess = openMessengerConversation(messengerUrl, false);
    
    if (messengerTabSuccess) {
      console.log('✅ Successfully opened Messenger reference tab');
    } else {
      console.log('⚠️ Messenger reference tab blocked by popup blocker');
    }
    
    // Step 2: Run Selenium automation 
    const result = await executeSeleniumAutomation(
      message, 
      messengerUrl, 
      imageUrls, 
      options.sessionId
    );
    
    // Combine results
    let finalMessage = result.message;
    if (messengerTabSuccess) {
      finalMessage += " (Messenger tab also opened for reference)";
    } else {
      finalMessage += " (Note: Messenger tab blocked by popup blocker)";
    }
    
    return {
      success: result.success,
      message: finalMessage,
      method: 'selenium',
      duration: result.duration,
      error: result.error,
      hasImage: imageUrls && imageUrls.length > 0
    };
  } else {
    // Use existing clipboard method - allow redirect since user needs to manually paste
    const result = await executeSmartLauncher(
      message, 
      messengerUrl, 
      imageUrls, 
      options.debugMode,
      true  // allowRedirect = true for clipboard mode
    );
    
    return {
      success: result.success,
      message: getInstructionMessage(result),
      method: 'clipboard',
      clipboardSuccess: result.clipboardSuccess,
      messengerSuccess: result.messengerSuccess,
      hasImage: result.hasImage,
      error: result.error
    };
  }
};