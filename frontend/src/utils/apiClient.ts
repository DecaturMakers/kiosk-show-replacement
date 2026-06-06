import type {
  ApiResponse,
  User,
  Display,
  Slideshow,
  SlideshowItem,
  SlideshowFormData,
  SlideshowItemFormData,
  AssignmentHistory,
  VideoUrlValidationResult
} from '../types';

/**
 * Retry configuration for API requests.
 */
interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryOn: number[];
}

/**
 * Extended request options with retry configuration.
 */
interface ExtendedRequestInit extends RequestInit {
  retry?: boolean;
  retryConfig?: Partial<RetryConfig>;
}

/**
 * Default retry configuration.
 */
const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryOn: [408, 429, 500, 502, 503, 504], // Timeout, rate limit, server errors
};

/**
 * Calculate delay with exponential backoff and jitter.
 */
const calculateBackoff = (
  attempt: number,
  baseDelay: number,
  maxDelay: number
): number => {
  // Exponential backoff: baseDelay * 2^attempt
  const exponentialDelay = baseDelay * Math.pow(2, attempt);
  // Add jitter (±25%)
  const jitter = exponentialDelay * (0.75 + Math.random() * 0.5);
  // Cap at maxDelay
  return Math.min(jitter, maxDelay);
};

/**
 * Sleep for a specified number of milliseconds.
 */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Check if an error is retryable.
 */
const isRetryableError = (error: Error): boolean => {
  // Network errors are retryable
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    return true;
  }
  // Timeout errors are retryable
  if (error.name === 'AbortError') {
    return true;
  }
  return false;
};

class ApiClient {
  private baseURL: string;
  private timeout: number;
  private defaultRetryConfig: RetryConfig;

  constructor(
    baseURL = '',
    timeout = 10000,
    retryConfig: Partial<RetryConfig> = {}
  ) {
    this.baseURL = baseURL;
    this.timeout = timeout;
    this.defaultRetryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };
  }

  /**
   * Make an HTTP request with retry logic.
   */
  private async request<T>(
    endpoint: string,
    options: ExtendedRequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const { retry = true, retryConfig: customRetryConfig, ...fetchOptions } = options;

    const retryConfig = { ...this.defaultRetryConfig, ...customRetryConfig };

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
      credentials: 'include', // Include cookies for session-based auth
      ...fetchOptions,
    };

    let lastError: Error | null = null;
    let lastResponse: ApiResponse<T> | null = null;

    for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url, {
          ...config,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Parse response
        let data: ApiResponse<T>;
        try {
          data = await response.json();
        } catch {
          // Response is not JSON
          if (!response.ok) {
            data = {
              success: false,
              error: `HTTP ${response.status}: ${response.statusText}`,
            };
          } else {
            data = { success: true } as ApiResponse<T>;
          }
        }

        // Check if we should retry based on status code
        if (
          !response.ok &&
          retry &&
          attempt < retryConfig.maxRetries &&
          retryConfig.retryOn.includes(response.status)
        ) {
          lastResponse = {
            success: false,
            error: data.error || `HTTP ${response.status}: ${response.statusText}`,
          };
          const delay = calculateBackoff(
            attempt,
            retryConfig.baseDelay,
            retryConfig.maxDelay
          );
          console.warn(
            `Request to ${endpoint} failed with status ${response.status}. ` +
            `Retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${retryConfig.maxRetries})`
          );
          await sleep(delay);
          continue;
        }

        if (!response.ok) {
          return {
            success: false,
            error: data.error || `HTTP ${response.status}: ${response.statusText}`,
          };
        }

        return data;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Check if we should retry
        if (
          retry &&
          attempt < retryConfig.maxRetries &&
          isRetryableError(lastError)
        ) {
          const delay = calculateBackoff(
            attempt,
            retryConfig.baseDelay,
            retryConfig.maxDelay
          );
          console.warn(
            `Request to ${endpoint} failed with error: ${lastError.message}. ` +
            `Retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${retryConfig.maxRetries})`
          );
          await sleep(delay);
          continue;
        }

        // Not retryable or out of retries
        if (lastError.name === 'AbortError') {
          return {
            success: false,
            error: 'Request timeout',
          };
        }
        return {
          success: false,
          error: lastError.message || 'Unknown error occurred',
        };
      }
    }

    // All retries exhausted
    if (lastResponse) {
      return lastResponse;
    }
    return {
      success: false,
      error: lastError?.message || 'Request failed after retries',
    };
  }

  /**
   * Make a request without retry (for mutations that shouldn't be retried).
   */
  private async requestNoRetry<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, retry: false });
  }

  // Authentication methods
  async login(username: string, password: string): Promise<ApiResponse<User>> {
    return this.requestNoRetry<User>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async logout(): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>('/api/v1/auth/logout', {
      method: 'POST',
    });
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request<User>('/api/v1/auth/user');
  }

  // Profile methods
  async updateProfile(data: { email?: string }): Promise<ApiResponse<User>> {
    return this.requestNoRetry<User>('/api/v1/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>('/api/v1/auth/password', {
      method: 'PUT',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  }

  // Slideshow methods
  async getSlideshows(): Promise<ApiResponse<Slideshow[]>> {
    return this.request<Slideshow[]>('/api/v1/slideshows');
  }

  async getSlideshow(id: number): Promise<ApiResponse<Slideshow>> {
    return this.request<Slideshow>(`/api/v1/slideshows/${id}`);
  }

  async createSlideshow(data: SlideshowFormData): Promise<ApiResponse<Slideshow>> {
    return this.requestNoRetry<Slideshow>('/api/v1/slideshows', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSlideshow(id: number, data: Partial<SlideshowFormData>): Promise<ApiResponse<Slideshow>> {
    return this.requestNoRetry<Slideshow>(`/api/v1/slideshows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSlideshow(id: number): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>(`/api/v1/slideshows/${id}`, {
      method: 'DELETE',
    });
  }

  async setDefaultSlideshow(id: number): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>(`/api/v1/slideshows/${id}/set-default`, {
      method: 'POST',
    });
  }

  async duplicateSlideshow(id: number, name: string): Promise<ApiResponse<Slideshow>> {
    return this.requestNoRetry<Slideshow>(`/api/v1/slideshows/${id}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  // Slideshow item methods
  async getSlideshowItems(slideshowId: number): Promise<ApiResponse<SlideshowItem[]>> {
    return this.request<SlideshowItem[]>(`/api/v1/slideshows/${slideshowId}/items`);
  }

  async createSlideshowItem(
    slideshowId: number,
    data: SlideshowItemFormData
  ): Promise<ApiResponse<SlideshowItem>> {
    return this.requestNoRetry<SlideshowItem>(`/api/v1/slideshows/${slideshowId}/items`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSlideshowItem(
    id: number,
    data: Partial<SlideshowItemFormData>
  ): Promise<ApiResponse<SlideshowItem>> {
    return this.requestNoRetry<SlideshowItem>(`/api/v1/slideshow-items/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSlideshowItem(id: number): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>(`/api/v1/slideshow-items/${id}`, {
      method: 'DELETE',
    });
  }

  async reorderSlideshowItem(id: number, newOrder: number): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>(`/api/v1/slideshow-items/${id}/reorder`, {
      method: 'POST',
      body: JSON.stringify({ new_order: newOrder }),
    });
  }

  // Display methods
  async getDisplays(): Promise<ApiResponse<Display[]>> {
    return this.request<Display[]>('/api/v1/displays');
  }

  async getDisplay(id: number): Promise<ApiResponse<Display>> {
    return this.request<Display>(`/api/v1/displays/${id}`);
  }

  async updateDisplay(id: number, data: Partial<Display>): Promise<ApiResponse<Display>> {
    return this.requestNoRetry<Display>(`/api/v1/displays/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDisplay(id: number): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>(`/api/v1/displays/${id}`, {
      method: 'DELETE',
    });
  }

  async assignSlideshowToDisplay(
    displayName: string,
    slideshowId: number
  ): Promise<ApiResponse<void>> {
    return this.requestNoRetry<void>(`/api/v1/displays/${displayName}/assign-slideshow`, {
      method: 'POST',
      body: JSON.stringify({ slideshow_id: slideshowId }),
    });
  }

  async reloadDisplay(id: number): Promise<ApiResponse<{ display_id: number; connections_notified: number }>> {
    return this.requestNoRetry<{ display_id: number; connections_notified: number }>(`/api/v1/displays/${id}/reload`, {
      method: 'POST',
    });
  }

  // Assignment History methods
  async getAssignmentHistory(params?: {
    limit?: number;
    offset?: number;
    display_id?: number;
    action?: string;
    user_id?: number;
  }): Promise<ApiResponse<AssignmentHistory[]>> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.offset) searchParams.append('offset', params.offset.toString());
    if (params?.display_id) searchParams.append('display_id', params.display_id.toString());
    if (params?.action) searchParams.append('action', params.action);
    if (params?.user_id) searchParams.append('user_id', params.user_id.toString());

    const query = searchParams.toString();
    const endpoint = query ? `/api/v1/assignment-history?${query}` : '/api/v1/assignment-history';

    return this.request<AssignmentHistory[]>(endpoint);
  }

  async getDisplayAssignmentHistory(displayId: number): Promise<ApiResponse<AssignmentHistory[]>> {
    return this.request<AssignmentHistory[]>(`/api/v1/displays/${displayId}/assignment-history`);
  }

  async createAssignmentHistory(data: {
    display_id: number;
    previous_slideshow_id?: number | null;
    new_slideshow_id?: number | null;
    action: 'assign' | 'unassign' | 'change';
    reason?: string;
  }): Promise<ApiResponse<AssignmentHistory>> {
    return this.requestNoRetry<AssignmentHistory>('/api/v1/assignment-history', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // File upload methods (no retry for file uploads)
  async uploadImage(file: File, slideshowId?: number): Promise<ApiResponse<{ file_path: string; url: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    if (slideshowId) {
      formData.append('slideshow_id', slideshowId.toString());
    }

    return this.requestNoRetry<{ file_path: string; url: string }>('/api/v1/uploads/image', {
      method: 'POST',
      body: formData,
      headers: {}, // Don't set Content-Type for FormData
    });
  }

  async uploadVideo(file: File, slideshowId?: number): Promise<ApiResponse<{ file_path: string; url: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    if (slideshowId) {
      formData.append('slideshow_id', slideshowId.toString());
    }

    return this.requestNoRetry<{ file_path: string; url: string }>('/api/v1/uploads/video', {
      method: 'POST',
      body: formData,
      headers: {}, // Don't set Content-Type for FormData
    });
  }

  // Video URL validation
  async validateVideoUrl(url: string): Promise<ApiResponse<VideoUrlValidationResult>> {
    // Use a longer timeout for video URL validation since ffprobe needs to probe the remote URL
    const originalTimeout = this.timeout;
    this.timeout = 70000; // 70 seconds to allow for 60s ffprobe timeout + overhead

    try {
      return await this.requestNoRetry<VideoUrlValidationResult>('/api/v1/validate/video-url', {
        method: 'POST',
        body: JSON.stringify({ url }),
      });
    } finally {
      this.timeout = originalTimeout;
    }
  }

  // Health check (with retry for monitoring)
  async getStatus(): Promise<ApiResponse<{ status: string; timestamp: string }>> {
    return this.request<{ status: string; timestamp: string }>('/api/v1/status');
  }

  // Health endpoints for monitoring
  async getHealth(): Promise<ApiResponse<{
    status: string;
    checks: Record<string, { status: string; latency_ms?: number }>;
  }>> {
    return this.request('/health');
  }

  async getHealthReady(): Promise<ApiResponse<{
    status: string;
    reason?: string;
    message?: string;
    database_initialized?: boolean;
  }>> {
    // Don't retry for health checks - we want to know immediately if the system is down
    return this.request('/health/ready', {
      retryConfig: { maxRetries: 0, baseDelay: 500, maxDelay: 1000, retryOn: [] },
    });
  }

  async getHealthLive(): Promise<ApiResponse<{ status: string }>> {
    return this.request('/health/live', { retry: false });
  }

  // Admin user management methods
  async getUsers(): Promise<ApiResponse<User[]>> {
    return this.request<User[]>('/api/v1/admin/users');
  }

  async getUser(id: number): Promise<ApiResponse<User>> {
    return this.request<User>(`/api/v1/admin/users/${id}`);
  }

  async createUser(data: {
    username: string;
    email?: string;
    is_admin?: boolean;
  }): Promise<ApiResponse<User & { temporary_password: string }>> {
    return this.requestNoRetry<User & { temporary_password: string }>('/api/v1/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(id: number, data: {
    email?: string;
    is_admin?: boolean;
    is_active?: boolean;
  }): Promise<ApiResponse<User>> {
    return this.requestNoRetry<User>(`/api/v1/admin/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async resetUserPassword(id: number): Promise<ApiResponse<{ temporary_password: string }>> {
    return this.requestNoRetry<{ temporary_password: string }>(`/api/v1/admin/users/${id}/reset-password`, {
      method: 'POST',
    });
  }
}

// Create singleton instance
export const apiClient = new ApiClient();
export default apiClient;
