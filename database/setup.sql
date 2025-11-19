-- RapidAid Database Setup Script
-- Run this script to initialize the database with sample data

USE rapidaid;

-- Insert sample patients
INSERT INTO patients (user_id, name, phone, blood_group, medical_history, default_latitude, default_longitude) VALUES 
(2, 'John Doe', '+1234567893', 'O+', 'Diabetes Type 2', 40.7260, -73.9897),
(3, 'Jane Smith', '+1234567894', 'A+', 'Hypertension', 40.7549, -73.9840),
(4, 'Robert Johnson', '+1234567895', 'B+', 'Asthma', 40.7614, -73.9776);

-- Create sample users for patients
INSERT INTO users (username, password_hash, email, role) VALUES 
('johndoe', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'john@example.com', 'patient'),
('janesmith', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'jane@example.com', 'patient'),
('robertjohnson', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'robert@example.com', 'patient');

-- Update patients with correct user_ids
UPDATE patients SET user_id = 5 WHERE name = 'John Doe';
UPDATE patients SET user_id = 6 WHERE name = 'Jane Smith';
UPDATE patients SET user_id = 7 WHERE name = 'Robert Johnson';

-- Insert sample ambulances for each hospital
INSERT INTO ambulances (hospital_id, vehicle_number, driver_name, driver_phone) VALUES 
(1, 'AMB-001', 'Mike Wilson', '+1234567896'),
(1, 'AMB-002', 'Sarah Davis', '+1234567897'),
(1, 'AMB-003', 'Tom Brown', '+1234567898'),
(1, 'AMB-004', 'Lisa Anderson', '+1234567899'),
(1, 'AMB-005', 'James Taylor', '+1234567900'),
(1, 'AMB-006', 'Emma White', '+1234567901'),
(1, 'AMB-007', 'David Miller', '+1234567902'),
(1, 'AMB-008', 'Jennifer Garcia', '+1234567903'),
(2, 'AMB-009', 'Robert Martinez', '+1234567904'),
(2, 'AMB-010', 'Maria Rodriguez', '+1234567905'),
(2, 'AMB-011', 'William Lopez', '+1234567906'),
(2, 'AMB-012', 'Patricia Hernandez', '+1234567907'),
(2, 'AMB-013', 'Charles Gonzalez', '+1234567908'),
(2, 'AMB-014', 'Linda Wilson', '+1234567909'),
(3, 'AMB-015', 'Joseph Moore', '+1234567910'),
(3, 'AMB-016', 'Barbara Taylor', '+1234567911'),
(3, 'AMB-017', 'Thomas Anderson', '+1234567912'),
(3, 'AMB-018', 'Nancy Thomas', '+1234567913'),
(3, 'AMB-019', 'Christopher Jackson', '+1234567914');

-- Insert sample emergency requests
INSERT INTO emergency_requests (patient_id, hospital_id, symptoms, priority_level, status, latitude, longitude, distance_to_hospital, estimated_arrival_time) VALUES 
(1, 1, 'Chest pain, difficulty breathing', 'critical', 'pending', 40.7260, -73.9897, 2.5, 8),
(2, 2, 'Broken leg, severe bleeding', 'high', 'assigned', 40.7549, -73.9840, 1.8, 6),
(3, 3, 'Minor cuts, dizziness', 'medium', 'completed', 40.7614, -73.9776, 1.2, 4);

-- Insert sample resource allocations
INSERT INTO resource_allocation (request_id, hospital_id, resource_type, allocated_count, max_needed, status) VALUES 
(1, 1, 'ambulance', 1, 1, 'allocated'),
(1, 1, 'doctor', 1, 2, 'allocated'),
(1, 1, 'room', 1, 1, 'requested'),
(2, 2, 'ambulance', 1, 1, 'allocated'),
(2, 2, 'doctor', 1, 1, 'allocated'),
(3, 3, 'ambulance', 1, 1, 'released'),
(3, 3, 'doctor', 1, 1, 'released');

-- Create hospital admin users
INSERT INTO users (username, password_hash, email, role) VALUES 
('hospital1_admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'admin@hospital1.com', 'hospital_admin'),
('hospital2_admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'admin@hospital2.com', 'hospital_admin'),
('hospital3_admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO.', 'admin@hospital3.com', 'hospital_admin');

-- Create a mapping table for hospital administrators
CREATE TABLE hospital_admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    hospital_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE
);

-- Assign hospital admins to hospitals
INSERT INTO hospital_admins (user_id, hospital_id) VALUES 
(8, 1),
(9, 2),
(10, 3);

-- Insert sample system logs
INSERT INTO system_logs (user_id, action, details, ip_address) VALUES 
(1, 'LOGIN', 'Superadmin logged in', '127.0.0.1'),
(5, 'CREATE_REQUEST', 'Emergency request created for chest pain', '192.168.1.100'),
(8, 'ASSIGN_AMBULANCE', 'Ambulance AMB-001 assigned to request #1', '192.168.1.200'),
(1, 'ADD_HOSPITAL', 'New hospital added: St. Mary Medical Center', '127.0.0.1');

-- Create views for common queries
CREATE VIEW hospital_status AS
SELECT 
    h.hospital_id,
    h.name,
    h.total_ambulances,
    h.available_ambulances,
    h.total_doctors,
    h.available_doctors,
    h.total_rooms,
    h.available_rooms,
    h.scheduling_algorithm,
    COUNT(CASE WHEN er.status = 'pending' THEN 1 END) as pending_requests,
    COUNT(CASE WHEN er.status = 'in_progress' THEN 1 END) as active_requests,
    ROUND(AVG(CASE WHEN er.status = 'completed' 
        THEN TIMESTAMPDIFF(MINUTE, er.created_at, er.completed_at) 
        END), 2) as avg_response_time
FROM hospitals h
LEFT JOIN emergency_requests er ON h.hospital_id = er.hospital_id
GROUP BY h.hospital_id, h.name, h.total_ambulances, h.available_ambulances, 
         h.total_doctors, h.available_doctors, h.total_rooms, h.available_rooms,
         h.scheduling_algorithm;

CREATE VIEW patient_request_history AS
SELECT 
    p.patient_id,
    p.name as patient_name,
    p.phone,
    er.request_id,
    er.symptoms,
    er.priority_level,
    er.status,
    er.created_at,
    er.assigned_at,
    er.completed_at,
    h.name as hospital_name,
    a.vehicle_number as ambulance_number,
    TIMESTAMPDIFF(MINUTE, er.created_at, COALESCE(er.completed_at, NOW())) as duration_minutes
FROM patients p
JOIN emergency_requests er ON p.patient_id = er.patient_id
LEFT JOIN hospitals h ON er.hospital_id = h.hospital_id
LEFT JOIN ambulances a ON er.ambulance_id = a.ambulance_id
ORDER BY er.created_at DESC;
