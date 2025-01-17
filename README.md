# Storage Agent

## Overview
The Storage Agent is an AI-powered system designed to handle customer inquiries, sales, and facility management for self-storage businesses. It provides natural language conversation capabilities, business logic integration, and real-time monitoring through a comprehensive dashboard.

## Key Features
- AI-powered voice and text conversations
- Integration with property management systems
- Real-time monitoring and analytics
- Customizable business rules and pricing
- Secure payment processing
- Comprehensive reporting and insights

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Docker
- Twilio account

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/storage-agent.git
   cd storage-agent
   ```

2. Set up environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   source venv/bin/activate      # Unix
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Start the development server:
   ```bash
   docker-compose up -d
   ```

## Usage
1. Access the dashboard at `http://localhost:3000`
2. Configure your storage facility settings
3. Set up call routing in Twilio
4. Monitor performance through the analytics dashboard

## Documentation
Comprehensive documentation is available in the `docs/` directory:
- [Implementation Timeline](docs/implementation/01-implementation-timeline.md)
- [System Architecture](docs/implementation/02-system-architecture.md)
- [Customer Experience](docs/implementation/03-customer-experience.md)
- [Development Roadmap](docs/implementation/04-development-roadmap.md)
- [Progress Tracking](docs/implementation/05-progress-tracking.md)
- [Implementation Guide](docs/implementation/06-implementation-guide.md)

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security
Please review our [security policy](SECURITY.md) for information on how to report vulnerabilities.
