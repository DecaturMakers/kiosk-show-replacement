import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import SlideshowDetail from '../pages/SlideshowDetail';
import AuthContext from '../contexts/AuthContext';

// Mock react-router-dom hooks
const mockNavigate = vi.fn();
const mockUseParams = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockUseParams()
  };
});

// Mock the useApi hook
const mockApiCall = vi.fn();
vi.mock('../hooks/useApi', () => ({
  useApi: () => ({
    apiCall: mockApiCall
  })
}));

const mockUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  is_admin: true,
  is_active: true,
  created_at: '2023-01-01T00:00:00Z',
  last_login_at: '2023-01-01T00:00:00Z'
};

const mockAuthContext = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  checkAuth: vi.fn()
};

const mockSlideshow = {
  id: 1,
  name: 'Test Slideshow',
  description: 'A test slideshow',
  is_active: true,
  is_default: false,
  default_item_duration: 10,
  transition_type: 'fade',
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  total_duration: 60,
  item_count: 3,
  items: []
};

const mockItems = [
  {
    id: 1,
    slideshow_id: 1,
    title: 'Test Image',
    content_type: 'image' as const,
    content_url: null,
    content_file_path: 'images/test.jpg',
    content_text: null,
    display_url: '/uploads/images/test.jpg',
    display_duration: 10,
    order_index: 1,
    is_active: true,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  },
  {
    id: 2,
    slideshow_id: 1,
    title: 'Test Video',
    content_type: 'video' as const,
    content_url: null,
    content_file_path: 'videos/test.mp4',
    content_text: null,
    display_url: '/uploads/videos/test.mp4',
    display_duration: 15,
    order_index: 2,
    is_active: true,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  },
  {
    id: 3,
    slideshow_id: 1,
    title: 'Test URL',
    content_type: 'url' as const,
    content_url: 'https://example.com',
    content_file_path: null,
    content_text: null,
    display_url: 'https://example.com',
    display_duration: 20,
    order_index: 3,
    is_active: true,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  }
];

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthContext.Provider value={mockAuthContext}>
    <BrowserRouter>
      {children}
    </BrowserRouter>
  </AuthContext.Provider>
);

describe('SlideshowDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    // Restore window.confirm/window.prompt spies even if a test fails
    vi.restoreAllMocks();
  });

  it('renders slideshow details correctly', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow')).toBeInTheDocument();
    });

    expect(screen.getByText('A test slideshow')).toBeInTheDocument();
    expect(screen.getAllByText('Active')).toHaveLength(4); // 1 slideshow + 3 active items
    
    // Check for stats specifically
    expect(screen.getByText('Active Items')).toBeInTheDocument();
    expect(screen.getByText('Total Duration')).toBeInTheDocument();
    expect(screen.getByText('1m')).toBeInTheDocument(); // total duration
  });

  it('renders slideshow items correctly', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Image')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Video')).toBeInTheDocument();
    expect(screen.getByText('Test URL')).toBeInTheDocument();
    expect(screen.getAllByText('image')).toHaveLength(1);
    expect(screen.getAllByText('video')).toHaveLength(1);
    expect(screen.getAllByText('url')).toHaveLength(1);
  });

  it('shows empty state when no items', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: [] });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('No Items Yet')).toBeInTheDocument();
    });

    expect(screen.getByText('Add some content to this slideshow to get started.')).toBeInTheDocument();
    expect(screen.getByText('Add Your First Item')).toBeInTheDocument();
  });

  it('handles delete item', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems })
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems.slice(1) });

    // Mock window.confirm
    const originalConfirm = window.confirm;
    window.confirm = vi.fn(() => true);

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Image')).toBeInTheDocument();
    });

    // Click delete button for first item
    const deleteButtons = screen.getAllByTitle('Delete');
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete "Test Image"?');

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith('/api/v1/slideshow-items/1', { method: 'DELETE' });
    });

    // Cleanup
    window.confirm = originalConfirm;
  });

  it('handles delete of inactive item with permanent-delete confirmation', async () => {
    const inactiveItem = { ...mockItems[0], is_active: false };
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: [inactiveItem] })
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: [] });

    // Spy on window.confirm; restored by afterEach even if the test fails
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Image')).toBeInTheDocument();
    });

    // Click delete button for the inactive item
    const deleteButtons = screen.getAllByTitle('Delete');
    fireEvent.click(deleteButtons[0]);

    expect(confirmSpy).toHaveBeenCalledWith(
      'Are you sure you want to permanently delete "Test Image"? This cannot be undone.'
    );

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith('/api/v1/slideshow-items/1', { method: 'DELETE' });
    });
  });

  it('handles add new item', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow')).toBeInTheDocument();
    });

    // Click add item button
    fireEvent.click(screen.getByText('Add Item'));

    // Should show the modal form
    await waitFor(() => {
      expect(screen.getByText('Add New Item')).toBeInTheDocument();
    });
  });

  it('handles edit item', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Image')).toBeInTheDocument();
    });

    // Click edit button for first item
    const editButtons = screen.getAllByTitle('Edit');
    fireEvent.click(editButtons[0]);

    // Should show the modal form
    await waitFor(() => {
      expect(screen.getByText('Edit Slideshow Item')).toBeInTheDocument();
    });
  });

  it('shows loading state', () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    expect(screen.getByText('Loading slideshow...')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('handles API error', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({
        success: false,
        error: 'Slideshow not found'
      })
      .mockResolvedValueOnce({
        success: false,
        error: 'Items not found'
      });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Slideshow not found or you don\'t have permission to view it.')).toBeInTheDocument();
    });

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('formats content source correctly', async () => {
    mockUseParams.mockReturnValue({ id: '1' });
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshow })
      .mockResolvedValueOnce({ success: true, data: mockItems });

    render(
      <TestWrapper>
        <SlideshowDetail />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('images/test.jpg')).toBeInTheDocument();
    });

    expect(screen.getByText('videos/test.mp4')).toBeInTheDocument();
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
  });
});
