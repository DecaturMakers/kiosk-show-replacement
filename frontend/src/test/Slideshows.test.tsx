import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import Slideshows from '../pages/Slideshows';
import AuthContext from '../contexts/AuthContext';

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

const mockSlideshows = [
  {
    id: 1,
    name: 'Test Slideshow 1',
    description: 'A test slideshow',
    is_active: true,
    is_default: false,
    default_item_duration: 10,
    transition_type: 'fade',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    total_duration: 60,
    item_count: 6,
    items: []
  },
  {
    id: 2,
    name: 'Test Slideshow 2',
    description: 'Another test slideshow',
    is_active: false,
    is_default: true,
    default_item_duration: 15,
    transition_type: 'slide',
    created_at: '2023-01-02T00:00:00Z',
    updated_at: '2023-01-02T00:00:00Z',
    total_duration: 120,
    item_count: 8,
    items: []
  }
];

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthContext.Provider value={mockAuthContext}>
    <BrowserRouter>
      {children}
    </BrowserRouter>
  </AuthContext.Provider>
);

describe('Slideshows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Restore window.confirm/window.prompt spies even if a test fails
    vi.restoreAllMocks();
  });

  it('renders loading state initially', () => {
    mockApiCall.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    expect(screen.getByText('Loading slideshows...')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders slideshows list when loaded', async () => {
    mockApiCall.mockResolvedValueOnce({
      success: true,
      data: mockSlideshows
    });

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
      expect(screen.getByText('Test Slideshow 2')).toBeInTheDocument();
    });

    expect(screen.getByText('All Slideshows (2)')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Inactive')).toBeInTheDocument();
    expect(screen.getByText('Default')).toBeInTheDocument();
  });

  it('renders empty state when no slideshows', async () => {
    mockApiCall.mockResolvedValueOnce({
      success: true,
      data: []
    });

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('No Slideshows Found')).toBeInTheDocument();
    });

    expect(screen.getByText('Get started by creating your first slideshow to display on your kiosk devices.')).toBeInTheDocument();
    expect(screen.getByText('Create Your First Slideshow')).toBeInTheDocument();
  });

  it('handles delete slideshow', async () => {
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshows })
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({ success: true, data: mockSlideshows.slice(1) });

    // Spy on window.confirm; restored by afterEach even if the test fails
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
    });

    // Click delete button for first slideshow
    const deleteButtons = screen.getAllByTitle('Delete');
    fireEvent.click(deleteButtons[0]);

    expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to delete the slideshow "Test Slideshow 1"?');

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith('/api/v1/slideshows/1', { method: 'DELETE' });
    });
  });

  it('handles duplicate slideshow', async () => {
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshows })
      .mockResolvedValueOnce({ success: true, data: { ...mockSlideshows[0], id: 3, name: 'My Copy' } })
      .mockResolvedValueOnce({ success: true, data: mockSlideshows });

    // Spy on window.prompt; restored by afterEach even if the test fails
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('My Copy');

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
    });

    // Click duplicate button for first slideshow
    const duplicateButtons = screen.getAllByTitle('Duplicate');
    fireEvent.click(duplicateButtons[0]);

    expect(promptSpy).toHaveBeenCalledWith(
      'Enter a name for the duplicated slideshow:',
      'Test Slideshow 1 (Copy)'
    );

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith('/api/v1/slideshows/1/duplicate', {
        method: 'POST',
        body: JSON.stringify({ name: 'My Copy' })
      });
    });
  });

  it('does not duplicate when prompt is cancelled', async () => {
    mockApiCall.mockResolvedValueOnce({ success: true, data: mockSlideshows });

    // Spy on window.prompt returning null (cancelled)
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue(null);

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
    });

    const duplicateButtons = screen.getAllByTitle('Duplicate');
    fireEvent.click(duplicateButtons[0]);

    expect(promptSpy).toHaveBeenCalled();
    // Only the initial fetch should have happened - no duplicate API call
    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });

  it('shows error when duplicate name is empty', async () => {
    mockApiCall.mockResolvedValueOnce({ success: true, data: mockSlideshows });

    vi.spyOn(window, 'prompt').mockReturnValue('   ');

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
    });

    const duplicateButtons = screen.getAllByTitle('Duplicate');
    fireEvent.click(duplicateButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('A name is required to duplicate a slideshow')).toBeInTheDocument();
    });
    // Only the initial fetch should have happened - no duplicate API call
    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });

  it('shows error when duplicate fails', async () => {
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshows })
      .mockResolvedValueOnce({
        success: false,
        error: 'A slideshow with this name already exists'
      });

    vi.spyOn(window, 'prompt').mockReturnValue('Test Slideshow 2');

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
    });

    const duplicateButtons = screen.getAllByTitle('Duplicate');
    fireEvent.click(duplicateButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('A slideshow with this name already exists')).toBeInTheDocument();
    });
  });

  it('handles set default slideshow', async () => {
    mockApiCall
      .mockResolvedValueOnce({ success: true, data: mockSlideshows })
      .mockResolvedValueOnce({ success: true })
      .mockResolvedValueOnce({ success: true, data: mockSlideshows });

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Slideshow 1')).toBeInTheDocument();
    });

    // Click set default button for first slideshow (which is not default)
    const defaultButton = screen.getByTitle('Set as Default');
    fireEvent.click(defaultButton);

    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledWith('/api/v1/slideshows/1/set-default', { method: 'POST' });
    });
  });

  it('handles API error', async () => {
    mockApiCall.mockResolvedValueOnce({
      success: false,
      error: 'Failed to fetch slideshows'
    });

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch slideshows')).toBeInTheDocument();
    });

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('formats duration correctly', async () => {
    const slideshowWithDurations = [
      { ...mockSlideshows[0], total_duration: 45 }, // 45 seconds
      { ...mockSlideshows[1], total_duration: 125 }, // 2 minutes 5 seconds
    ];

    mockApiCall.mockResolvedValueOnce({
      success: true,
      data: slideshowWithDurations
    });

    render(
      <TestWrapper>
        <Slideshows />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('45s')).toBeInTheDocument();
      expect(screen.getByText('2m 5s')).toBeInTheDocument();
    });
  });
});
