import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Container, Row, Col, Card, Button, Badge, Alert, Spinner, Table, Modal } from 'react-bootstrap';
import { useApi } from '../hooks/useApi';
import { Slideshow, SlideshowItem } from '../types';
import SlideshowItemForm from '../components/SlideshowItemForm';
import { sanitizeHtml } from '../utils/sanitizeHtml';

const SlideshowDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { apiCall } = useApi();

  const [slideshow, setSlideshow] = useState<Slideshow | null>(null);
  const [items, setItems] = useState<SlideshowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showItemForm, setShowItemForm] = useState(false);
  const [editingItem, setEditingItem] = useState<SlideshowItem | null>(null);

  useEffect(() => {
    if (id) {
      fetchSlideshowData(parseInt(id));
    }
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchSlideshowData = async (slideshowId: number) => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch slideshow details - include inactive items so they can be viewed/reactivated
      const [slideshowResponse, itemsResponse] = await Promise.all([
        apiCall(`/api/v1/slideshows/${slideshowId}?include_inactive=true`),
        apiCall(`/api/v1/slideshows/${slideshowId}/items?include_inactive=true`)
      ]);

      if (slideshowResponse.success) {
        setSlideshow(slideshowResponse.data as Slideshow);
      } else {
        setError(slideshowResponse.error || 'Failed to fetch slideshow');
        return;
      }

      if (itemsResponse.success) {
        setItems(itemsResponse.data as SlideshowItem[]);
      } else {
        console.warn('Failed to fetch slideshow items:', itemsResponse.error);
        setItems([]);
      }
    } catch (err) {
      setError('Failed to fetch slideshow data');
      console.error('Error fetching slideshow data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteItem = async (itemId: number, itemName: string, isActive: boolean) => {
    const message = isActive
      ? `Are you sure you want to delete "${itemName}"?`
      : `Are you sure you want to permanently delete "${itemName}"? This cannot be undone.`;
    if (!window.confirm(message)) {
      return;
    }

    try {
      const response = await apiCall(`/api/v1/slideshow-items/${itemId}`, {
        method: 'DELETE'
      });
      
      if (response.success) {
        // Refresh the items list
        if (id) {
          fetchSlideshowData(parseInt(id));
        }
      } else {
        setError(response.error || 'Failed to delete item');
      }
    } catch (err) {
      setError('Failed to delete item');
      console.error('Error deleting item:', err);
    }
  };

  const handleItemSaved = () => {
    setShowItemForm(false);
    setEditingItem(null);
    if (id) {
      fetchSlideshowData(parseInt(id));
    }
  };

  const handleEditItem = (item: SlideshowItem) => {
    setEditingItem(item);
    setShowItemForm(true);
  };

  const handleReorderItem = async (itemId: number, newOrder: number) => {
    try {
      const response = await apiCall(`/api/v1/slideshow-items/${itemId}/reorder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ new_order: newOrder }),
      });
      
      if (response.success) {
        // Refresh the items list
        if (id) {
          fetchSlideshowData(parseInt(id));
        }
      } else {
        setError(response.error || 'Failed to reorder item');
      }
    } catch (err) {
      setError('Failed to reorder item');
      console.error('Error reordering item:', err);
    }
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (remainingSeconds === 0) {
      return `${minutes}m`;
    }
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getContentTypeIcon = (contentType: string): string => {
    switch (contentType) {
      case 'image': return 'bi-image';
      case 'video': return 'bi-play-circle';
      case 'url': return 'bi-globe';
      case 'text': return 'bi-type';
      default: return 'bi-file';
    }
  };

  const getContentTypeColor = (contentType: string): string => {
    switch (contentType) {
      case 'image': return 'success';
      case 'video': return 'primary';
      case 'url': return 'info';
      case 'text': return 'warning';
      default: return 'secondary';
    }
  };

  if (loading) {
    return (
      <Container className="mt-4">
        <div className="text-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
          <p className="mt-2">Loading slideshow...</p>
        </div>
      </Container>
    );
  }

  if (!slideshow) {
    return (
      <Container className="mt-4">
        <Alert variant="danger">
          Slideshow not found or you don't have permission to view it.
        </Alert>
      </Container>
    );
  }

  return (
    <Container className="mt-4">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h1 className="mb-1">{slideshow.name}</h1>
              <div className="text-muted">
                <Badge 
                  bg={slideshow.is_active ? 'success' : 'secondary'}
                  className="me-2"
                >
                  {slideshow.is_active ? 'Active' : 'Inactive'}
                </Badge>
                {slideshow.is_default && (
                  <Badge bg="primary" className="me-2">Default</Badge>
                )}
                <span className="small">
                  Created {new Date(slideshow.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="d-flex gap-2">
              <Link 
                to={`/admin/slideshows/${slideshow.id}/edit`}
                className="btn btn-outline-secondary"
              >
                <i className="bi bi-pencil me-2"></i>
                Edit Details
              </Link>
              <Button 
                variant="outline-secondary" 
                onClick={() => navigate('/admin/slideshows')}
              >
                <i className="bi bi-arrow-left me-2"></i>
                Back to Slideshows
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {error && (
        <Row className="mb-3">
          <Col>
            <Alert variant="danger" dismissible onClose={() => setError(null)}>
              {error}
            </Alert>
          </Col>
        </Row>
      )}

      {slideshow.description && (
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <p className="mb-0 text-muted">{slideshow.description}</p>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      <Row className="mb-4">
        <Col md={3}>
          <Card>
            <Card.Body className="text-center">
              <h3 className="text-primary">
                {items.filter(i => i.is_active).length}
                {items.some(i => !i.is_active) && (
                  <span className="text-muted small"> / {items.length}</span>
                )}
              </h3>
              <p className="text-muted mb-0">
                Active Items
                {items.some(i => !i.is_active) && ' / Total'}
              </p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card>
            <Card.Body className="text-center">
              <h3 className="text-success">
                {slideshow.total_duration ? formatDuration(slideshow.total_duration) : 'N/A'}
              </h3>
              <p className="text-muted mb-0">Total Duration</p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card>
            <Card.Body className="text-center">
              <h3 className="text-info">
                {formatDuration(slideshow.default_item_duration)}
              </h3>
              <p className="text-muted mb-0">Default Duration</p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card>
            <Card.Body className="text-center">
              <h3 className="text-warning">
                {slideshow.transition_type || 'None'}
              </h3>
              <p className="text-muted mb-0">Transition</p>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row>
        <Col>
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                  Slideshow Items ({items.filter(i => i.is_active).length}
                  {items.some(i => !i.is_active) && ` / ${items.length} total`})
                </h5>
                <Button 
                  variant="primary" 
                  size="sm"
                  onClick={() => setShowItemForm(true)}
                >
                  <i className="bi bi-plus-circle me-2"></i>
                  Add Item
                </Button>
              </div>
            </Card.Header>
            <Card.Body className="p-0">
              {items.length === 0 ? (
                <div className="text-center py-5">
                  <i className="bi bi-collection display-4 text-muted mb-3"></i>
                  <h5 className="text-muted mb-3">No Items Yet</h5>
                  <p className="text-muted mb-4">
                    Add some content to this slideshow to get started.
                  </p>
                  <Button 
                    variant="primary"
                    onClick={() => setShowItemForm(true)}
                  >
                    Add Your First Item
                  </Button>
                </div>
              ) : (
                <Table responsive striped hover className="mb-0">
                  <thead className="table-light">
                    <tr>
                      <th style={{ width: '60px' }}>Order</th>
                      <th>Content</th>
                      <th>Type</th>
                      <th>Duration</th>
                      <th>Status</th>
                      <th style={{ width: '120px' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, index) => (
                      <tr
                        key={item.id}
                        style={!item.is_active ? { opacity: 0.6, backgroundColor: '#f8f9fa' } : undefined}
                      >
                        <td>
                          <div className="d-flex flex-column gap-1">
                            <span className="badge bg-light text-dark">
                              {item.order_index}
                            </span>
                            <div className="btn-group-vertical btn-group-sm">
                              {index > 0 && item.is_active && (
                                <Button
                                  variant="outline-secondary"
                                  size="sm"
                                  onClick={() => handleReorderItem(item.id, item.order_index - 1)}
                                  title="Move Up"
                                >
                                  <i className="bi bi-arrow-up"></i>
                                </Button>
                              )}
                              {index < items.length - 1 && item.is_active && (
                                <Button
                                  variant="outline-secondary"
                                  size="sm"
                                  onClick={() => handleReorderItem(item.id, item.order_index + 1)}
                                  title="Move Down"
                                >
                                  <i className="bi bi-arrow-down"></i>
                                </Button>
                              )}
                            </div>
                          </div>
                        </td>
                        <td>
                          <div>
                            {item.title && (
                              <div className="fw-bold">{item.title}</div>
                            )}
                            <div className="text-muted small">
                              {item.content_type === 'text' ? (
                                // Render sanitized HTML for text slides (allows <b>, <i>, etc.)
                                <span
                                  dangerouslySetInnerHTML={{
                                    __html: sanitizeHtml(
                                      item.content_text?.substring(0, 50) +
                                        (item.content_text && item.content_text.length > 50 ? '...' : '')
                                    ),
                                  }}
                                />
                              ) : item.content_type === 'url' ? (
                                item.content_url
                              ) : (
                                item.content_file_path || item.content_url
                              )}
                            </div>
                          </div>
                        </td>
                        <td>
                          <Badge 
                            bg={getContentTypeColor(item.content_type)}
                            className="d-flex align-items-center gap-1"
                            style={{ width: 'fit-content' }}
                          >
                            <i className={getContentTypeIcon(item.content_type)}></i>
                            {item.content_type}
                          </Badge>
                        </td>
                        <td>
                          {formatDuration(item.display_duration || slideshow.default_item_duration)}
                        </td>
                        <td>
                          <Badge 
                            bg={item.is_active ? 'success' : 'secondary'}
                          >
                            {item.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </td>
                        <td>
                          <div className="btn-group" role="group">
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              onClick={() => handleEditItem(item)}
                              title="Edit"
                            >
                              <i className="bi bi-pencil"></i>
                            </Button>
                            <Button
                              variant="outline-danger"
                              size="sm"
                              onClick={() => handleDeleteItem(item.id, item.title || 'this item', item.is_active)}
                              title="Delete"
                            >
                              <i className="bi bi-trash"></i>
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Item Form Modal */}
      <Modal 
        show={showItemForm} 
        onHide={() => {
          setShowItemForm(false);
          setEditingItem(null);
        }}
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            {editingItem ? 'Edit Slideshow Item' : 'Add New Item'}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <SlideshowItemForm
            slideshowId={slideshow.id}
            item={editingItem}
            onSave={handleItemSaved}
            onCancel={() => {
              setShowItemForm(false);
              setEditingItem(null);
            }}
          />
        </Modal.Body>
      </Modal>
    </Container>
  );
};

export default SlideshowDetail;
