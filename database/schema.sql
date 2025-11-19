-- RapidAid Database Schema
-- Emergency Response System Database Structure

-- Create database
CREATE DATABASE IF NOT EXISTS rapidaid;
USE rapidaid;

-- Users table (for authentication and role management)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role ENUM('patient', 'hospital_admin', 'superadmin') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Hospitals table
CREATE TABLE hospitals (
    hospital_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    phone VARCHAR(20),
    total_ambulances INT DEFAULT 5,
    available_ambulances INT DEFAULT 5,
    total_doctors INT DEFAULT 10,
    available_doctors INT DEFAULT 10,
    total_rooms INT DEFAULT 20,
    available_rooms INT DEFAULT 20,
    scheduling_algorithm ENUM('priority', 'fcfs', 'sjf') DEFAULT 'priority',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_location (latitude, longitude),
    INDEX idx_availability (available_ambulances)
);

-- Ambulances table
CREATE TABLE ambulances (
    ambulance_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT NOT NULL,
    vehicle_number VARCHAR(20) UNIQUE NOT NULL,
    status ENUM('available', 'assigned', 'in_transit', 'at_patient', 'returning') DEFAULT 'available',
    current_latitude DECIMAL(10, 8),
    current_longitude DECIMAL(11, 8),
    driver_name VARCHAR(100),
    driver_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_hospital (hospital_id)
);

-- Patients table
CREATE TABLE patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    blood_group VARCHAR(10),
    medical_history TEXT,
    default_latitude DECIMAL(10, 8),
    default_longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Emergency requests table
CREATE TABLE emergency_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    hospital_id INT,
    symptoms TEXT NOT NULL,
    priority_level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    status ENUM('pending', 'assigned', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    distance_to_hospital DECIMAL(8, 3),
    estimated_arrival_time INT, -- in minutes
    ambulance_id INT,
    assigned_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id),
    FOREIGN KEY (ambulance_id) REFERENCES ambulances(ambulance_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority_level),
    INDEX idx_patient (patient_id),
    INDEX idx_hospital (hospital_id),
    INDEX idx_created (created_at)
);

-- Resource allocation tracking (for Banker's Algorithm)
CREATE TABLE resource_allocation (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    hospital_id INT NOT NULL,
    resource_type ENUM('ambulance', 'doctor', 'room') NOT NULL,
    allocated_count INT NOT NULL DEFAULT 1,
    max_needed INT NOT NULL DEFAULT 1,
    status ENUM('requested', 'allocated', 'released') DEFAULT 'requested',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES emergency_requests(request_id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    INDEX idx_request (request_id),
    INDEX idx_hospital_resource (hospital_id, resource_type)
);

-- System logs for auditing
CREATE TABLE system_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
);

-- Hospital scheduling preferences
CREATE TABLE hospital_scheduling (
    preference_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT UNIQUE NOT NULL,
    algorithm ENUM('priority', 'fcfs', 'sjf') NOT NULL DEFAULT 'priority',
    priority_weights JSON, -- Store weights for different priority levels
    max_queue_size INT DEFAULT 50,
    average_response_time DECIMAL(8, 2) DEFAULT 0, -- in minutes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE
);

-- Insert default superadmin
INSERT INTO users (username, password_hash, email, role) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'admin@rapidaid.com', 'superadmin');

-- Insert sample hospitals
INSERT INTO hospitals (name, address, latitude, longitude, phone, total_ambulances, available_ambulances, total_doctors, available_doctors, total_rooms, available_rooms) VALUES 
('City General Hospital', '123 Main St, City Center', 40.7128, -74.0060, '+1234567890', 8, 8, 15, 15, 30, 30),
('St. Mary Medical Center', '456 Oak Ave, West District', 40.7589, -73.9851, '+1234567891', 6, 6, 12, 12, 25, 25),
('Riverside Emergency Care', '789 River Rd, East Side', 40.7489, -73.9680, '+1234567892', 5, 5, 10, 10, 20, 20);

-- Insert sample scheduling preferences
INSERT INTO hospital_scheduling (hospital_id, algorithm, priority_weights) VALUES 
(1, 'priority', '{"critical": 4, "high": 3, "medium": 2, "low": 1}'),
(2, 'fcfs', '{}'),
(3, 'sjf', '{}');
