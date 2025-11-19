# RapidAid - Emergency Response System

RapidAid is an intelligent emergency response platform that combines OS scheduling principles with healthcare resource management to optimize ambulance dispatch and hospital resource allocation.

## Core Concepts

- **Patient Requests** → Treated as processes
- **Resources** → Ambulances, doctors, hospital rooms (limited resources)
- **Scheduling Algorithms** → Priority, FCFS, SJF (based on distance)
- **Deadlock Avoidance** → Banker's Algorithm for resource allocation

## System Architecture

### 1. Patient Dashboard
- Hospital selection with real-time ambulance availability
- Symptom-based priority assignment
- Real-time distance calculation using GPS coordinates
- Interactive map integration
- Request submission and tracking

### 2. Hospital Dashboard
- Queue management with configurable scheduling algorithms
- Real-time ambulance allocation
- Resource monitoring (total, available, active ambulances)
- Deadlock prevention using Banker's Algorithm

### 3. SuperAdmin Dashboard
- Hospital management (CRUD operations)
- System-wide statistics
- Global request flow monitoring

## Technology Stack

### Frontend
- **React.js** - Component-based UI
- **Interactive Maps** - Real-time location services
- **Responsive Design** - Modern UI/UX

### Backend
- **Python/Flask** - REST API server
- **Scheduling Algorithms** - Priority, FCFS, SJF implementation
- **Banker's Algorithm** - Deadlock avoidance
- **Real-time Processing** - Request management

### Database
- **MySQL** - Structured data storage
- **Optimized Queries** - Performance-focused design

## Project Structure

```
rapidaid1/
├── backend/          # Flask API server
├── frontend/         # React application
├── database/         # MySQL schemas and scripts
└── README.md         # Project documentation
```

## Installation & Setup

1. Clone the repository
2. Set up MySQL database using scripts in `/database`
3. Install backend dependencies and run Flask server
4. Install frontend dependencies and run React app
5. Access the application via browser

## Key Features

- **OS-based Scheduling**: Proven algorithms for efficient resource allocation
- **Real-time Tracking**: Live ambulance and request status updates
- **Map Integration**: Visual distance calculation and route planning
- **Deadlock Prevention**: Banker's Algorithm ensures system stability
- **Multi-role Interface**: Specialized dashboards for patients, hospitals, and admins

## Algorithm Implementation

### Scheduling Algorithms
- **Priority**: Emergency severity-based allocation
- **FCFS**: First Come First Serve for fair queuing
- **SJF**: Shortest Job First based on distance optimization

### Banker's Algorithm
- Resource allocation safety checks
- Deadlock detection and avoidance
- Optimal resource utilization

## Contributing

This project demonstrates the practical application of OS concepts in real-world healthcare emergency response systems.
