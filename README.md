# Kiosk Show Replacement

[![CI](https://github.com/Decaturmakers/kiosk-show-replacement/actions/workflows/ci.yml/badge.svg)](https://github.com/Decaturmakers/kiosk-show-replacement/actions/workflows/ci.yml)
[![Release](https://github.com/Decaturmakers/kiosk-show-replacement/actions/workflows/release.yml/badge.svg)](https://github.com/Decaturmakers/kiosk-show-replacement/actions/workflows/release.yml)

A self-hosted digital signage solution built with Flask, serving as a replacement for the defunct kiosk.show service.

## Documentation

**Full documentation is available at [https://decaturmakers.github.io/kiosk-show-replacement/](https://decaturmakers.github.io/kiosk-show-replacement/)**

- [Deployment Guide](https://decaturmakers.github.io/kiosk-show-replacement/deployment.html) - Production setup with Docker
- [Usage Guide](https://decaturmakers.github.io/kiosk-show-replacement/usage.html) - Managing slideshows and displays
- [API Reference](https://decaturmakers.github.io/kiosk-show-replacement/api.html) - REST API documentation
- [Development Guide](https://decaturmakers.github.io/kiosk-show-replacement/development.html) - Local development setup

## Features

- **Web-based Management**: Create and manage slideshows through an intuitive web interface
- **Modern Admin Interface**: React-based admin panel with real-time updates and responsive design
- **Kiosk Display Mode**: Full-screen slideshow display optimized for kiosk devices
- **Multiple Content Types**: Support for images, videos, web pages, text slides, and Skedda calendar displays
- **Flexible Timing**: Customizable display duration for each slide
- **Real-time Updates**: Dynamic slideshow management without restarts
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **RESTful API**: Full API for programmatic management
- **Multi-Architecture Support**: Docker images for x86_64 and ARM64 (including Raspberry Pi)

## Quick Start

Docker is the only supported deployment method for production. See the [Deployment Guide](https://decaturmakers.github.io/kiosk-show-replacement/deployment.html) for detailed instructions.

```bash
# Clone and configure
git clone https://github.com/Decaturmakers/kiosk-show-replacement.git
cd kiosk-show-replacement
cp .env.docker.example .env
# Edit .env with your settings (SECRET_KEY, passwords, etc.)

# Start the application
docker-compose -f docker-compose.prod.yml up -d

# Access at http://localhost:5000/admin (default: admin/admin)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure code quality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

For local development setup, see the [Development Guide](https://decaturmakers.github.io/kiosk-show-replacement/development.html).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the original kiosk.show service
- Built with Flask, React, Bootstrap, and modern web technologies
- Designed for self-hosting and digital signage use cases
