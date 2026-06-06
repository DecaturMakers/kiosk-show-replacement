import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Table, Badge, Spinner, Alert } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { Slideshow } from '../types';

const Slideshows: React.FC = () => {
  const [slideshows, setSlideshows] = useState<Slideshow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { apiCall } = useApi();

  useEffect(() => {
    fetchSlideshows();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchSlideshows = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiCall('/api/v1/slideshows');
      if (response.success) {
        setSlideshows(response.data as Slideshow[]);
      } else {
        setError(response.error || 'Failed to fetch slideshows');
      }
    } catch (err) {
      setError('Failed to fetch slideshows');
      console.error('Error fetching slideshows:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete the slideshow "${name}"?`)) {
      return;
    }

    try {
      const response = await apiCall(`/api/v1/slideshows/${id}`, {
        method: 'DELETE'
      });
      
      if (response.success) {
        // Refresh the list
        fetchSlideshows();
      } else {
        setError(response.error || 'Failed to delete slideshow');
      }
    } catch (err) {
      setError('Failed to delete slideshow');
      console.error('Error deleting slideshow:', err);
    }
  };

  const handleDuplicate = async (id: number, name: string) => {
    const newName = window.prompt(
      'Enter a name for the duplicated slideshow:',
      `${name} (Copy)`
    );
    if (newName === null) {
      return;
    }
    if (!newName.trim()) {
      setError('A name is required to duplicate a slideshow');
      return;
    }

    try {
      const response = await apiCall(`/api/v1/slideshows/${id}/duplicate`, {
        method: 'POST',
        body: JSON.stringify({ name: newName.trim() })
      });

      if (response.success) {
        // Refresh the list to show the new slideshow
        fetchSlideshows();
      } else {
        setError(response.error || 'Failed to duplicate slideshow');
      }
    } catch (err) {
      setError('Failed to duplicate slideshow');
      console.error('Error duplicating slideshow:', err);
    }
  };

  const handleSetDefault = async (id: number, _name: string) => {
    try {
      const response = await apiCall(`/api/v1/slideshows/${id}/set-default`, {
        method: 'POST'
      });
      
      if (response.success) {
        // Refresh the list to update default status
        fetchSlideshows();
      } else {
        setError(response.error || 'Failed to set default slideshow');
      }
    } catch (err) {
      setError('Failed to set default slideshow');
      console.error('Error setting default slideshow:', err);
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

  if (loading) {
    return (
      <Container className="mt-4">
        <div className="text-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
          <p className="mt-2">Loading slideshows...</p>
        </div>
      </Container>
    );
  }

  return (
    <Container className="mt-4">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h1>Slideshows</h1>
            <Link to="/admin/slideshows/new" className="btn btn-primary">
              <i className="bi bi-plus-circle me-2"></i>
              Create New Slideshow
            </Link>
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

      {slideshows.length === 0 ? (
        <Row>
          <Col>
            <Card>
              <Card.Body className="text-center py-5">
                <i className="bi bi-collection-play display-4 text-muted mb-3"></i>
                <h3 className="text-muted mb-3">No Slideshows Found</h3>
                <p className="text-muted mb-4">
                  Get started by creating your first slideshow to display on your kiosk devices.
                </p>
                <Link to="/admin/slideshows/new" className="btn btn-primary">
                  Create Your First Slideshow
                </Link>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      ) : (
        <Row>
          <Col>
            <Card>
              <Card.Header>
                <h5 className="mb-0">All Slideshows ({slideshows.length})</h5>
              </Card.Header>
              <Card.Body className="p-0">
                <Table responsive striped hover className="mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>Name</th>
                      <th>Status</th>
                      <th>Items</th>
                      <th>Duration</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {slideshows.map((slideshow) => (
                      <tr key={slideshow.id}>
                        <td>
                          <div>
                            <strong>{slideshow.name}</strong>
                            {slideshow.description && (
                              <div className="text-muted small">
                                {slideshow.description}
                              </div>
                            )}
                          </div>
                        </td>
                        <td>
                          <div>
                            <Badge 
                              bg={slideshow.is_active ? 'success' : 'secondary'}
                              className="me-1"
                            >
                              {slideshow.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                            {slideshow.is_default && (
                              <Badge bg="primary">Default</Badge>
                            )}
                          </div>
                        </td>
                        <td>
                          <span className="badge bg-light text-dark">
                            {slideshow.item_count || 0} items
                          </span>
                        </td>
                        <td>
                          {slideshow.total_duration ? formatDuration(slideshow.total_duration) : 'N/A'}
                        </td>
                        <td>
                          <small className="text-muted">
                            {new Date(slideshow.created_at).toLocaleDateString()}
                          </small>
                        </td>
                        <td>
                          <div className="btn-group" role="group">
                            <Link
                              to={`/admin/slideshows/${slideshow.id}`}
                              className="btn btn-outline-primary btn-sm"
                              title="Edit Slides"
                            >
                              <i className="bi bi-eye"></i>
                            </Link>
                            <Link
                              to={`/admin/slideshows/${slideshow.id}/edit`}
                              className="btn btn-outline-secondary btn-sm"
                              title="Edit Slideshow"
                            >
                              <i className="bi bi-pencil"></i>
                            </Link>
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              onClick={() => handleDuplicate(slideshow.id, slideshow.name)}
                              title="Duplicate"
                            >
                              <i className="bi bi-copy"></i>
                            </Button>
                            {!slideshow.is_default && (
                              <Button
                                variant="outline-info"
                                size="sm"
                                onClick={() => handleSetDefault(slideshow.id, slideshow.name)}
                                title="Set as Default"
                              >
                                <i className="bi bi-star"></i>
                              </Button>
                            )}
                            <Button
                              variant="outline-danger"
                              size="sm"
                              onClick={() => handleDelete(slideshow.id, slideshow.name)}
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
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </Container>
  );
};

export default Slideshows;
