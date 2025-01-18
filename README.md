# Storage Agent

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/github/actions/workflow/status/your-username/storage-agent/ci.yml?branch=main)](https://github.com/your-username/storage-agent/actions)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-%3E%3D20.10-blue)](https://www.docker.com/)

## Overview
The Storage Agent is an AI-powered system designed to handle customer inquiries, sales, and facility management for self-storage businesses. It provides natural language conversation capabilities, business logic integration, and real-time monitoring through a comprehensive dashboard.

## Key Features
- AI-powered voice and text conversations
- Integration with property management systems
- Real-time monitoring and analytics
- Customizable business rules and pricing
- Secure payment processing
- Comprehensive reporting and insights

## Technical Architecture
The system is built using a microservices architecture with the following components:
- **API Gateway**: Handles incoming requests and routes them to appropriate services
- **Conversation Service**: Manages AI-powered conversations using natural language processing
- **Storage Management Service**: Handles storage unit inventory and pricing
- **Analytics Service**: Provides real-time monitoring and reporting
- **Integration Service**: Connects with external systems like Twilio and payment gateways

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

## License
This project is licensed under the GNU General Public License v3.0 (GPLv3). Key points of this license include:

- **Freedom to Use**: You are free to use this software for any purpose
- **Freedom to Study**: You can study how the program works and change it
- **Freedom to Distribute**: You can redistribute copies of the software
- **Copyleft**: Any derivative works must also be licensed under GPLv3

The full license text is available in the [LICENSE](LICENSE) file. If you need to use this software under different licensing terms, please contact the project maintainers.

Note: The GPLv3 license requires that any modifications to this software must also be open source and licensed under GPLv3. This ensures that the software remains free and open for all users.

## Security
Please review our [security policy](SECURITY.md) for information on how to report vulnerabilities.
