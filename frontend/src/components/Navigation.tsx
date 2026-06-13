import React from 'react';
import { Navbar, Nav, Container, Dropdown } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Navigation: React.FC = () => {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="mb-4">
      <Container>
        <Navbar.Brand as={Link} to="/admin">Kiosk Show Replacement</Navbar.Brand>
        
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/admin">Dashboard</Nav.Link>
            <Nav.Link as={Link} to="/admin/slideshows">Slideshows</Nav.Link>
            <Nav.Link as={Link} to="/admin/displays">Displays</Nav.Link>
            <Nav.Link as={Link} to="/admin/assignment-history">Assignment History</Nav.Link>
            <Nav.Link as={Link} to="/admin/monitoring">System Monitoring</Nav.Link>
            {user?.is_admin && (
              <Nav.Link as={Link} to="/admin/users">User Management</Nav.Link>
            )}
          </Nav>
          
          <Nav>
            <Nav.Link
              href="https://decaturmakers.github.io/kiosk-show-replacement/usage.html"
              target="_blank"
              rel="noopener noreferrer"
              className="me-2"
            >
              Help
            </Nav.Link>
            <Dropdown align="end">
              <Dropdown.Toggle variant="outline-light" id="user-dropdown">
                {user?.username || 'User'}
              </Dropdown.Toggle>
              
              <Dropdown.Menu>
                <Dropdown.ItemText>
                  <div>
                    <div><strong>{user?.username}</strong></div>
                    <div className="text-muted small">
                      {user?.is_admin ? 'Administrator' : 'User'}
                    </div>
                  </div>
                </Dropdown.ItemText>
                <Dropdown.Divider />
                <Dropdown.Item as={Link} to="/admin/profile">
                  Profile Settings
                </Dropdown.Item>
                <Dropdown.Divider />
                <Dropdown.Item onClick={handleLogout}>
                  Sign Out
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default Navigation;
