import { useCallback } from 'react';
import { apiClient } from '../utils/apiClient';
import type { ApiResponse } from '../types';

export interface UseApiResult {
  apiCall: (endpoint: string, options?: RequestInit) => Promise<ApiResponse>;
}

export const useApi = (): UseApiResult => {
  const apiCall = useCallback(async (endpoint: string, options?: RequestInit): Promise<ApiResponse> => {
    // This is a generic wrapper around the apiClient request method
    // For now, we'll use the apiClient's private request method functionality
    // by routing through the appropriate specific methods
    
    try {
      const method = options?.method || 'GET';
      const url = endpoint;
      
      // Handle different endpoints by routing to appropriate apiClient methods
      if (url === '/api/v1/slideshows' && method === 'GET') {
        return await apiClient.getSlideshows();
      }
      
      if (url.startsWith('/api/v1/slideshows/') && url.endsWith('/items') && method === 'GET') {
        const slideshowId = parseInt(url.split('/')[4]);
        return await apiClient.getSlideshowItems(slideshowId);
      }

      // Match /api/v1/slideshows/{id} (exactly 5 segments when split)
      const slideshowGetMatch = url.match(/^\/api\/v1\/slideshows\/(\d+)$/);
      if (slideshowGetMatch && method === 'GET') {
        const slideshowId = parseInt(slideshowGetMatch[1]);
        return await apiClient.getSlideshow(slideshowId);
      }
      
      if (url === '/api/v1/slideshows' && method === 'POST') {
        const data = JSON.parse(options?.body as string);
        return await apiClient.createSlideshow(data);
      }
      
      // Match /api/v1/slideshows/{id} for PUT
      const slideshowPutMatch = url.match(/^\/api\/v1\/slideshows\/(\d+)$/);
      if (slideshowPutMatch && method === 'PUT') {
        const slideshowId = parseInt(slideshowPutMatch[1]);
        const data = JSON.parse(options?.body as string);
        return await apiClient.updateSlideshow(slideshowId, data);
      }

      // Match /api/v1/slideshows/{id} for DELETE
      const slideshowDeleteMatch = url.match(/^\/api\/v1\/slideshows\/(\d+)$/);
      if (slideshowDeleteMatch && method === 'DELETE') {
        const slideshowId = parseInt(slideshowDeleteMatch[1]);
        return await apiClient.deleteSlideshow(slideshowId);
      }

      // Match /api/v1/slideshows/{id}/set-default
      const setDefaultMatch = url.match(/^\/api\/v1\/slideshows\/(\d+)\/set-default$/);
      if (setDefaultMatch && method === 'POST') {
        const slideshowId = parseInt(setDefaultMatch[1]);
        return await apiClient.setDefaultSlideshow(slideshowId);
      }

      // Match /api/v1/slideshows/{id}/duplicate
      const duplicateMatch = url.match(/^\/api\/v1\/slideshows\/(\d+)\/duplicate$/);
      if (duplicateMatch && method === 'POST') {
        const slideshowId = parseInt(duplicateMatch[1]);
        const data = JSON.parse(options?.body as string);
        return await apiClient.duplicateSlideshow(slideshowId, data.name);
      }

      // Match /api/v1/slideshows/{id}/items for POST (create item)
      const createItemMatch = url.match(/^\/api\/v1\/slideshows\/(\d+)\/items$/);
      if (createItemMatch && method === 'POST') {
        const slideshowId = parseInt(createItemMatch[1]);
        const data = JSON.parse(options?.body as string);
        return await apiClient.createSlideshowItem(slideshowId, data);
      }

      // Match /api/v1/slideshow-items/{id} for PUT
      const itemPutMatch = url.match(/^\/api\/v1\/slideshow-items\/(\d+)$/);
      if (itemPutMatch && method === 'PUT') {
        const itemId = parseInt(itemPutMatch[1]);
        const data = JSON.parse(options?.body as string);
        return await apiClient.updateSlideshowItem(itemId, data);
      }

      // Match /api/v1/slideshow-items/{id} for DELETE
      const itemDeleteMatch = url.match(/^\/api\/v1\/slideshow-items\/(\d+)$/);
      if (itemDeleteMatch && method === 'DELETE') {
        const itemId = parseInt(itemDeleteMatch[1]);
        return await apiClient.deleteSlideshowItem(itemId);
      }

      // Match /api/v1/slideshow-items/{id}/reorder for POST
      const reorderMatch = url.match(/^\/api\/v1\/slideshow-items\/(\d+)\/reorder$/);
      if (reorderMatch && method === 'POST') {
        const itemId = parseInt(reorderMatch[1]);
        const data = JSON.parse(options?.body as string);
        return await apiClient.reorderSlideshowItem(itemId, data.new_order);
      }
      
      if (url.startsWith('/api/v1/uploads/')) {
        const uploadType = url.split('/')[4];
        if (uploadType === 'image') {
          const formData = options?.body as FormData;
          const file = formData.get('file') as File;
          const slideshowId = formData.get('slideshow_id') ? parseInt(formData.get('slideshow_id') as string) : undefined;
          return await apiClient.uploadImage(file, slideshowId);
        } else if (uploadType === 'video') {
          const formData = options?.body as FormData;
          const file = formData.get('file') as File;
          const slideshowId = formData.get('slideshow_id') ? parseInt(formData.get('slideshow_id') as string) : undefined;
          return await apiClient.uploadVideo(file, slideshowId);
        }
      }

      // Match /api/v1/validate/video-url for POST
      if (url === '/api/v1/validate/video-url' && method === 'POST') {
        const data = JSON.parse(options?.body as string);
        return await apiClient.validateVideoUrl(data.url);
      }
      
      if (url === '/api/v1/auth/user' && method === 'GET') {
        return await apiClient.getCurrentUser();
      }
      
      if (url === '/api/v1/auth/login' && method === 'POST') {
        const data = JSON.parse(options?.body as string);
        return await apiClient.login(data.username, data.password);
      }
      
      if (url === '/api/v1/auth/logout' && method === 'POST') {
        return await apiClient.logout();
      }
      
      if (url === '/api/v1/displays' && method === 'GET') {
        return await apiClient.getDisplays();
      }
      
      // Fallback for unknown endpoints - make a direct request
      // Warn in development when using fallback for endpoints that should have explicit handlers
      if (import.meta.env.DEV) {
        console.warn(
          `[useApi] Unmatched endpoint falling back to generic handler: ${method} ${endpoint}. ` +
          'Consider adding an explicit handler if this endpoint should be routed to apiClient.'
        );
      }

      const baseURL = '';
      const fullUrl = `${baseURL}${endpoint}`;

      // Check if body is FormData - if so, don't set Content-Type header
      // (browser will set correct multipart boundary automatically)
      const isFormData = options?.body instanceof FormData;

      const config: RequestInit = {
        headers: isFormData ? {
          ...options?.headers,
        } : {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        credentials: 'include',
        ...options,
      };

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(fullUrl, {
          ...config,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        const data = await response.json();

        if (!response.ok) {
          return {
            success: false,
            error: data.error || `HTTP ${response.status}: ${response.statusText}`,
          };
        }

        return data;
      } catch (error) {
        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            return {
              success: false,
              error: 'Request timeout',
            };
          }
          return {
            success: false,
            error: error.message,
          };
        }
        return {
          success: false,
          error: 'Unknown error occurred',
        };
      }
      
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }, []);

  return { apiCall };
};
