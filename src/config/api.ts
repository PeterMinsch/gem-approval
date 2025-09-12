// API Configuration
// This file handles the API base URL configuration for different environments

// Get API base URL from environment variables
const getApiBaseUrl = (): string => {
  // In Vite, environment variables are prefixed with VITE_
  const apiUrl = import.meta.env.VITE_API_URL;
  
  if (apiUrl) {
    return apiUrl;
  }
  
  // Fallback to current hostname with port 8000 for development
  if (typeof window !== 'undefined') {
    const { hostname, protocol } = window.location;
    return `${protocol}//${hostname}:8000`;
  }
  
  // Final fallback to localhost
  return 'http://localhost:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export default API_BASE_URL;