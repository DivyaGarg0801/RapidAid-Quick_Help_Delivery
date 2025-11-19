from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import hashlib
import os
from datetime import datetime
import math
from functools import wraps
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'rapidaid'
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Establish a fresh MySQL connection. Keep connection None on failure."""
        try:
            # small timeout helps detect dead server quickly
            self.connection = mysql.connector.connect(**DB_CONFIG, autocommit=True, connection_timeout=10)
            print("Connected to MySQL")
        except Exception as e:
            print("Error connecting to MySQL:", repr(e))
            self.connection = None

    def ensure_connection(self):
        """Ensure connection is alive; reconnect if broken."""
        if self.connection is None:
            self.connect()
            return

        try:
            # Ping server; reconnect=True attempts an automatic reconnect
            self.connection.ping(reconnect=True, attempts=2, delay=0.5)
        except Exception as e:
            print("Ping failed, reconnecting:", repr(e))
            self.connect()

    def execute_query(self, query, params=None, fetch=True):
        """
        Execute SQL query with safe reconnect + single retry.
        Returns fetched rows (list of dicts) or lastrowid (when fetch=False).
        Raises Exception on unrecoverable failure.
        """
        # normalize params to tuple (mysql-connector expects sequence)
        if params is None:
            params_tuple = ()
        elif isinstance(params, (list, tuple)):
            params_tuple = tuple(params)
        else:
            # single value -> wrap in tuple
            params_tuple = (params,)

        # Ensure there is a usable connection
        self.ensure_connection()
        if self.connection is None:
            raise RuntimeError("Database connection not available")

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params_tuple)
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                last_id = cursor.lastrowid
                # commit already enabled by autocommit, but keep commit for safety
                try:
                    self.connection.commit()
                except Exception:
                    pass
                cursor.close()
                return last_id

        except Exception as first_err:
            # Log the first error
            print("First query attempt failed:", repr(first_err))

            # Try to reconnect and retry once
            try:
                self.connect()
                if self.connection is None:
                    raise RuntimeError("Reconnect failed")

                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(query, params_tuple)
                if fetch:
                    result = cursor.fetchall()
                    cursor.close()
                    return result
                else:
                    last_id = cursor.lastrowid
                    try:
                        self.connection.commit()
                    except Exception:
                        pass
                    cursor.close()
                    return last_id

            except Exception as second_err:
                # Give a clear error (do NOT swallow)
                print("Retry query attempt failed:", repr(second_err))
                # Re-raise an exception so routes can return 500 and log the error
                raise

db = DatabaseManager()

# Supported scheduling algorithms
ALLOWED_SCHEDULING_ALGORITHMS = ['priority', 'fcfs', 'sjf', 'hrrn']

# Authentication middleware
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = session['user_id']
            query = "SELECT role FROM users WHERE user_id = %s"
            result = db.execute_query(query, (user_id,))
            
            if result is None:
                return jsonify({'error': 'Database error'}), 500

            if len(result) == 0 or result[0]['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Utility functions
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def determine_priority(symptoms):
    """Determine priority level based on symptoms"""
    critical_keywords = ['heart attack', 'cardiac arrest', 'unconscious', 'severe bleeding', 'difficulty breathing', 'chest pain']
    high_keywords = ['broken bone', 'fracture', 'severe pain', 'head injury', 'burn']
    medium_keywords = ['dizziness', 'nausea', 'fever', 'moderate pain', 'cuts']
    
    symptoms_lower = symptoms.lower()
    
    for keyword in critical_keywords:
        if keyword in symptoms_lower:
            return 'critical'
    
    for keyword in high_keywords:
        if keyword in symptoms_lower:
            return 'high'
    
    for keyword in medium_keywords:
        if keyword in symptoms_lower:
            return 'medium'
    
    return 'low'

# Scheduling Algorithms
class SchedulingAlgorithms:
    @staticmethod
    def priority_scheduling(requests, hospital_id):
        """Priority-based scheduling algorithm"""
        query = """
        SELECT er.*, p.name as patient_name, p.phone 
        FROM emergency_requests er 
        JOIN patients p ON er.patient_id = p.patient_id 
        WHERE er.hospital_id = %s AND er.status = 'pending'
        ORDER BY 
            CASE er.priority_level
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            er.created_at ASC
        """
        return db.execute_query(query, (hospital_id,))
    
    @staticmethod
    def hrrn_scheduling(requests, hospital_id):
        """Highest Response Ratio Next scheduling algorithm (fair, non-preemptive)"""
        query = """
        SELECT er.*, p.name as patient_name, p.phone,
               TIMESTAMPDIFF(MINUTE, er.created_at, NOW()) AS waiting_time,
               (
                   (TIMESTAMPDIFF(MINUTE, er.created_at, NOW()) + GREATEST(er.estimated_arrival_time, 1))
                   / GREATEST(er.estimated_arrival_time, 1)
               ) AS response_ratio
        FROM emergency_requests er
        JOIN patients p ON er.patient_id = p.patient_id
        WHERE er.hospital_id = %s AND er.status = 'pending'
        ORDER BY response_ratio DESC, er.created_at ASC
        """
        return db.execute_query(query, (hospital_id,))
    
    @staticmethod
    def fcfs_scheduling(requests, hospital_id):
        """First Come First Serve scheduling algorithm"""
        query = """
        SELECT er.*, p.name as patient_name, p.phone 
        FROM emergency_requests er 
        JOIN patients p ON er.patient_id = p.patient_id 
        WHERE er.hospital_id = %s AND er.status = 'pending'
        ORDER BY er.created_at ASC
        """
        return db.execute_query(query, (hospital_id,))
    
    @staticmethod
    def sjf_scheduling(requests, hospital_id):
        """Shortest Job First scheduling algorithm (based on distance)"""
        query = """
        SELECT er.*, p.name as patient_name, p.phone,
               h.latitude as hospital_lat, h.longitude as hospital_lon
        FROM emergency_requests er 
        JOIN patients p ON er.patient_id = p.patient_id 
        JOIN hospitals h ON er.hospital_id = h.hospital_id
        WHERE er.hospital_id = %s AND er.status = 'pending'
        ORDER BY er.distance_to_hospital ASC, er.created_at ASC
        """
        return db.execute_query(query, (hospital_id,))

# Banker's Algorithm for Deadlock Avoidance
class BankersAlgorithm:
    def __init__(self, hospital_id):
        self.hospital_id = hospital_id
        self.resources = self.get_available_resources()
    
    def get_available_resources(self):
        """Get current available resources for the hospital"""
        query = """
        SELECT available_ambulances, available_doctors, available_rooms 
        FROM hospitals WHERE hospital_id = %s
        """
        result = db.execute_query(query, (self.hospital_id,))
        if result:
            return {
                'ambulance': result[0]['available_ambulances'],
                'doctor': result[0]['available_doctors'],
                'room': result[0]['available_rooms']
            }
        return {'ambulance': 0, 'doctor': 0, 'room': 0}
    
    def is_safe_allocation(self, requested_resources):
        """Check if resource allocation is safe using Banker's Algorithm"""
        # Calculate need = max - allocation
        # Check if requested_resources <= available_resources
        for resource_type, requested_count in requested_resources.items():
            if self.resources.get(resource_type, 0) < requested_count:
                return False, f"Insufficient {resource_type}s"
        
        # Simulate allocation to check for safe state
        temp_resources = self.resources.copy()
        for resource_type, count in requested_resources.items():
            temp_resources[resource_type] -= count
        
        # Simple safety check: ensure no resource goes negative
        for resource_type, count in temp_resources.items():
            if count < 0:
                return False, f"Unsafe allocation: {resource_type}"
        
        return True, "Safe allocation"
    
    def allocate_resources(self, request_id, requested_resources):
        """Allocate resources if safe"""
        is_safe, message = self.is_safe_allocation(requested_resources)
        
        if not is_safe:
            return False, message
        
        # Update hospital resources
        for resource_type, count in requested_resources.items():
            if resource_type == 'ambulance':
                query = "UPDATE hospitals SET available_ambulances = available_ambulances - %s WHERE hospital_id = %s"
            elif resource_type == 'doctor':
                query = "UPDATE hospitals SET available_doctors = available_doctors - %s WHERE hospital_id = %s"
            elif resource_type == 'room':
                query = "UPDATE hospitals SET available_rooms = available_rooms - %s WHERE hospital_id = %s"
            else:
                continue
            
            db.execute_query(query, (count, self.hospital_id), fetch=False)
        
        # Record allocation
        for resource_type, count in requested_resources.items():
            query = """
            INSERT INTO resource_allocation (request_id, hospital_id, resource_type, allocated_count, max_needed, status)
            VALUES (%s, %s, %s, %s, %s, 'allocated')
            """
            db.execute_query(query, (request_id, self.hospital_id, resource_type, count, count), fetch=False)
        
        return True, "Resources allocated successfully"
    
    def release_resources(self, request_id):
        """Release allocated resources"""
        query = """
        SELECT resource_type, allocated_count 
        FROM resource_allocation 
        WHERE request_id = %s AND status = 'allocated' AND hospital_id = %s
        """
        allocations = db.execute_query(query, (request_id, self.hospital_id))
        
        if allocations:
            for allocation in allocations:
                resource_type = allocation['resource_type']
                count = allocation['allocated_count']
                
                # Update hospital resources
                if resource_type == 'ambulance':
                    query = "UPDATE hospitals SET available_ambulances = available_ambulances + %s WHERE hospital_id = %s"
                elif resource_type == 'doctor':
                    query = "UPDATE hospitals SET available_doctors = available_doctors + %s WHERE hospital_id = %s"
                elif resource_type == 'room':
                    query = "UPDATE hospitals SET available_rooms = available_rooms + %s WHERE hospital_id = %s"
                else:
                    continue
                
                db.execute_query(query, (count, self.hospital_id), fetch=False)
                
                # Update allocation status
                update_query = "UPDATE resource_allocation SET status = 'released' WHERE request_id = %s AND resource_type = %s"
                db.execute_query(update_query, (request_id, resource_type), fetch=False)
        
        return True, "Resources released successfully"

# Authentication Routes
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    query = "SELECT user_id, username, password_hash, role FROM users WHERE username = %s"
    result = db.execute_query(query, (username,))
    
    if result and len(result) > 0:
        user = result[0]
        # NOTE: For this academic/demo project we skip password hash verification
        # so that sample users (admin, hospital1_admin, johndoe, etc.) can log in
        # without having to align database hashes. Any password will work
        # for an existing username. Do NOT use this pattern in production.
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        # Log the login
        log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
        db.execute_query(log_query, (user['user_id'], 'LOGIN', f'User {username} logged in'), fetch=False)
        
        return jsonify({
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role']
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
        db.execute_query(log_query, (session['user_id'], 'LOGOUT', f'User {session["username"]} logged out'), fetch=False)
    
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/current_user', methods=['GET'])
def current_user():
    if 'user_id' in session:
        return jsonify({
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session['role']
        })
    return jsonify({'error': 'Not authenticated'}), 401

# Hospital Routes
@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    query = """
    SELECT h.*, hs.algorithm as scheduling_algorithm,
           COUNT(CASE WHEN er.status = 'pending' THEN 1 END) as pending_requests
    FROM hospitals h
    LEFT JOIN hospital_scheduling hs ON h.hospital_id = hs.hospital_id
    LEFT JOIN emergency_requests er ON h.hospital_id = er.hospital_id AND er.status = 'pending'
    GROUP BY h.hospital_id
    ORDER BY h.name
    """
    hospitals = db.execute_query(query)
    return jsonify(hospitals)

@app.route('/api/hospitals/<int:hospital_id>', methods=['GET'])
def get_hospital(hospital_id):
    query = """
    SELECT h.*, hs.algorithm as scheduling_algorithm, hs.priority_weights
    FROM hospitals h
    LEFT JOIN hospital_scheduling hs ON h.hospital_id = hs.hospital_id
    WHERE h.hospital_id = %s
    """
    result = db.execute_query(query, (hospital_id,))
    if result:
        return jsonify(result[0])
    return jsonify({'error': 'Hospital not found'}), 404

@app.route('/api/hospitals/<int:hospital_id>/algorithm', methods=['PUT'])
@role_required('superadmin')
def update_hospital_algorithm(hospital_id):
    data = request.get_json() or {}
    algorithm = data.get('algorithm')

    if algorithm not in ALLOWED_SCHEDULING_ALGORITHMS:
        return jsonify({'error': 'Invalid algorithm'}), 400

    try:
        # Ensure scheduling row exists
        existing = db.execute_query(
            "SELECT preference_id FROM hospital_scheduling WHERE hospital_id = %s",
            (hospital_id,)
        )

        if existing:
            query = "UPDATE hospital_scheduling SET algorithm = %s WHERE hospital_id = %s"
            db.execute_query(query, (algorithm, hospital_id), fetch=False)
        else:
            query = "INSERT INTO hospital_scheduling (hospital_id, algorithm) VALUES (%s, %s)"
            db.execute_query(query, (hospital_id, algorithm), fetch=False)

        if 'user_id' in session:
            log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
            db.execute_query(
                log_query,
                (session['user_id'], 'UPDATE_ALGORITHM', f'Updated algorithm for hospital {hospital_id} to {algorithm}'),
                fetch=False,
            )

        return jsonify({'message': 'Algorithm updated successfully'})
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/hospitals', methods=['POST'])
@role_required('superadmin')
def create_hospital():
    data = request.get_json()
    
    required_fields = ['name', 'address', 'latitude', 'longitude']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Insert hospital
        query = """
        INSERT INTO hospitals (name, address, latitude, longitude, phone, 
                              total_ambulances, available_ambulances,
                              total_doctors, available_doctors,
                              total_rooms, available_rooms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['name'], data['address'], data['latitude'], data['longitude'],
            data.get('phone', ''), data.get('total_ambulances', 5),
            data.get('total_ambulances', 5), data.get('total_doctors', 10),
            data.get('total_doctors', 10), data.get('total_rooms', 20),
            data.get('total_rooms', 20)
        )
        
        hospital_id = db.execute_query(query, params, fetch=False)
        
        # Set scheduling preference
        algorithm = data.get('scheduling_algorithm', 'priority')
        if algorithm not in ALLOWED_SCHEDULING_ALGORITHMS:
            algorithm = 'priority'
        priority_weights = data.get('priority_weights', '{"critical": 4, "high": 3, "medium": 2, "low": 1}')
        
        scheduling_query = """
        INSERT INTO hospital_scheduling (hospital_id, algorithm, priority_weights)
        VALUES (%s, %s, %s)
        """
        db.execute_query(scheduling_query, (hospital_id, algorithm, priority_weights), fetch=False)
        
        # Log the action
        if 'user_id' in session:
            log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
            db.execute_query(log_query, (session['user_id'], 'ADD_HOSPITAL', f'Added hospital: {data["name"]}'), fetch=False)
        
        return jsonify({'message': 'Hospital created successfully', 'hospital_id': hospital_id}), 201
        
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/hospitals/<int:hospital_id>', methods=['PUT'])
@role_required('superadmin')
def update_hospital(hospital_id):
    data = request.get_json() or {}
    allowed_fields = [
        'name', 'address', 'latitude', 'longitude', 'phone',
        'total_ambulances', 'available_ambulances',
        'total_doctors', 'available_doctors',
        'total_rooms', 'available_rooms'
    ]

    set_clauses = []
    params = []
    for field in allowed_fields:
        if field in data:
            set_clauses.append(f"{field} = %s")
            params.append(data[field])

    if not set_clauses:
        return jsonify({'error': 'No fields to update'}), 400

    params.append(hospital_id)

    query = f"UPDATE hospitals SET {', '.join(set_clauses)} WHERE hospital_id = %s"
    try:
        db.execute_query(query, tuple(params), fetch=False)

        if 'user_id' in session:
            log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
            db.execute_query(
                log_query,
                (session['user_id'], 'UPDATE_HOSPITAL', f'Updated hospital {hospital_id}'),
                fetch=False,
            )

        return jsonify({'message': 'Hospital updated successfully'})
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/hospitals/<int:hospital_id>', methods=['DELETE'])
@role_required('superadmin')
def delete_hospital(hospital_id):
    try:
        query = "DELETE FROM hospitals WHERE hospital_id = %s"
        db.execute_query(query, (hospital_id,), fetch=False)

        if 'user_id' in session:
            log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
            db.execute_query(
                log_query,
                (session['user_id'], 'DELETE_HOSPITAL', f'Deleted hospital {hospital_id}'),
                fetch=False,
            )

        return jsonify({'message': 'Hospital deleted successfully'})
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# Emergency Request Routes
@app.route('/api/emergency_requests', methods=['POST'])
def create_emergency_request():
    data = request.get_json()
    
    required_fields = ['symptoms', 'latitude', 'longitude', 'hospital_id', 'name', 'phone']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Find or create a patient profile based on phone number (no login required)
        patient_query = "SELECT patient_id FROM patients WHERE phone = %s ORDER BY patient_id DESC LIMIT 1"
        patient_result = db.execute_query(patient_query, (data['phone'],))

        if not patient_result:
            insert_patient = "INSERT INTO patients (user_id, name, phone) VALUES (NULL, %s, %s)"
            db.execute_query(insert_patient, (data['name'], data['phone']), fetch=False)
            patient_result = db.execute_query(patient_query, (data['phone'],))

        patient_id = patient_result[0]['patient_id']
        
        # Determine priority level
        priority_level = determine_priority(data['symptoms'])
        
        # Calculate distance to hospital
        hospital_query = "SELECT latitude, longitude FROM hospitals WHERE hospital_id = %s"
        hospital_result = db.execute_query(hospital_query, (data['hospital_id'],))
        
        if not hospital_result:
            return jsonify({'error': 'Hospital not found'}), 404
        
        hospital_lat = hospital_result[0]['latitude']
        hospital_lon = hospital_result[0]['longitude']
        distance = calculate_distance(data['latitude'], data['longitude'], hospital_lat, hospital_lon)
        
        # Estimate arrival time (simplified: 3 minutes per km)
        estimated_arrival = int(distance * 3)
        
        # Create emergency request
        query = """
        INSERT INTO emergency_requests (patient_id, hospital_id, symptoms, priority_level, 
                                      latitude, longitude, distance_to_hospital, estimated_arrival_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            patient_id, data['hospital_id'], data['symptoms'], priority_level,
            data['latitude'], data['longitude'], distance, estimated_arrival
        )
        
        request_id = db.execute_query(query, params, fetch=False)
        
        # Log the action (if a logged-in user exists; anonymous patients will have no session)
        if 'user_id' in session:
            log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
            db.execute_query(log_query, (session['user_id'], 'CREATE_REQUEST', f'Emergency request created: {data["symptoms"][:50]}'), fetch=False)
        
        return jsonify({
            'message': 'Emergency request created successfully',
            'request_id': request_id,
            'priority_level': priority_level,
            'distance_to_hospital': distance,
            'estimated_arrival_time': estimated_arrival
        }), 201
        
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/emergency_requests/<int:hospital_id>/queue', methods=['GET'])
@role_required('hospital_admin', 'superadmin')
def get_request_queue(hospital_id):
    # Get hospital's scheduling algorithm
    query = "SELECT algorithm FROM hospital_scheduling WHERE hospital_id = %s"
    result = db.execute_query(query, (hospital_id,))
    
    if not result:
        return jsonify({'error': 'Hospital scheduling preferences not found'}), 404
    
    algorithm = result[0]['algorithm']
    
    # Get requests based on scheduling algorithm
    if algorithm == 'priority':
        requests = SchedulingAlgorithms.priority_scheduling(None, hospital_id)
    elif algorithm == 'fcfs':
        requests = SchedulingAlgorithms.fcfs_scheduling(None, hospital_id)
    elif algorithm == 'sjf':
        requests = SchedulingAlgorithms.sjf_scheduling(None, hospital_id)
    elif algorithm == 'hrrn':
        requests = SchedulingAlgorithms.hrrn_scheduling(None, hospital_id)
    else:
        requests = []
    
    return jsonify(requests)

@app.route('/api/emergency_requests/<int:request_id>/assign', methods=['POST'])
@role_required('hospital_admin')
def assign_ambulance(request_id):
    data = request.get_json()
    ambulance_id = data.get('ambulance_id')
    
    if not ambulance_id:
        return jsonify({'error': 'Ambulance ID required'}), 400
    
    try:
        # Get request details
        request_query = "SELECT * FROM emergency_requests WHERE request_id = %s"
        request_result = db.execute_query(request_query, (request_id,))
        
        if not request_result:
            return jsonify({'error': 'Request not found'}), 404
        
        emergency_request = request_result[0]
        hospital_id = emergency_request['hospital_id']
        
        # Check if ambulance is available
        ambulance_query = "SELECT * FROM ambulances WHERE ambulance_id = %s AND hospital_id = %s AND status = 'available'"
        ambulance_result = db.execute_query(ambulance_query, (ambulance_id, hospital_id))
        
        if not ambulance_result:
            return jsonify({'error': 'Ambulance not available'}), 400
        
        # Apply Banker's Algorithm for resource allocation
        banker = BankersAlgorithm(hospital_id)
        requested_resources = {
            'ambulance': 1,
            'doctor': 1,
            'room': 1 if emergency_request['priority_level'] in ['critical', 'high'] else 0
        }
        
        allocation_success, allocation_message = banker.allocate_resources(request_id, requested_resources)
        
        if not allocation_success:
            return jsonify({'error': allocation_message}), 400
        
        # Update ambulance status
        update_ambulance_query = "UPDATE ambulances SET status = 'assigned' WHERE ambulance_id = %s"
        db.execute_query(update_ambulance_query, (ambulance_id,), fetch=False)
        
        # Update request status
        update_request_query = """
        UPDATE emergency_requests 
        SET status = 'assigned', ambulance_id = %s, assigned_at = NOW() 
        WHERE request_id = %s
        """
        db.execute_query(update_request_query, (ambulance_id, request_id), fetch=False)
        
        # Log the action
        log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
        db.execute_query(log_query, (session['user_id'], 'ASSIGN_AMBULANCE', f'Ambulance {ambulance_id} assigned to request {request_id}'), fetch=False)
        
        return jsonify({'message': 'Ambulance assigned successfully'})
        
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/emergency_requests/<int:request_id>/complete', methods=['POST'])
@role_required('hospital_admin')
def complete_request(request_id):
    try:
        request_query = "SELECT * FROM emergency_requests WHERE request_id = %s"
        request_result = db.execute_query(request_query, (request_id,))

        if not request_result:
            return jsonify({'error': 'Request not found'}), 404

        emergency_request = request_result[0]
        if emergency_request['status'] not in ('assigned', 'in_progress'):
            return jsonify({'error': 'Request is not active'}), 400

        ambulance_id = emergency_request.get('ambulance_id')
        hospital_id = emergency_request['hospital_id']

        if ambulance_id:
            update_ambulance_query = "UPDATE ambulances SET status = 'available' WHERE ambulance_id = %s"
            db.execute_query(update_ambulance_query, (ambulance_id,), fetch=False)

        banker = BankersAlgorithm(hospital_id)
        banker.release_resources(request_id)

        update_request_query = """
        UPDATE emergency_requests
        SET status = 'completed', completed_at = NOW()
        WHERE request_id = %s
        """
        db.execute_query(update_request_query, (request_id,), fetch=False)

        if 'user_id' in session:
            log_query = "INSERT INTO system_logs (user_id, action, details) VALUES (%s, %s, %s)"
            db.execute_query(
                log_query,
                (session['user_id'], 'COMPLETE_REQUEST', f'Request {request_id} marked completed'),
                fetch=False,
            )

        return jsonify({'message': 'Request completed and resources released'})
    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/ambulances/<int:hospital_id>', methods=['GET'])
@role_required('hospital_admin')
def get_ambulances(hospital_id):
    query = "SELECT * FROM ambulances WHERE hospital_id = %s ORDER BY vehicle_number"
    ambulances = db.execute_query(query, (hospital_id,))
    return jsonify(ambulances)

@app.route('/api/hospitals/<int:hospital_id>/status', methods=['GET'])
@role_required('hospital_admin', 'superadmin')
def get_hospital_status(hospital_id):
    hospital_query = """
    SELECT hospital_id, name, total_ambulances, available_ambulances,
           total_doctors, available_doctors,
           total_rooms, available_rooms
    FROM hospitals
    WHERE hospital_id = %s
    """
    hospital = db.execute_query(hospital_query, (hospital_id,))

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    hospital_data = hospital[0]

    stats_query = """
    SELECT 
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_requests,
        COUNT(CASE WHEN status IN ('assigned', 'in_progress') THEN 1 END) as active_requests,
        AVG(CASE 
                WHEN completed_at IS NOT NULL 
                THEN TIMESTAMPDIFF(MINUTE, created_at, completed_at)
            END) as avg_response_time
    FROM emergency_requests
    WHERE hospital_id = %s
    """
    stats = db.execute_query(stats_query, (hospital_id,))
    stats_data = stats[0] if stats else {}

    response = {
        **hospital_data,
        'active_ambulances': max(
            0,
            hospital_data['total_ambulances'] - hospital_data['available_ambulances']
        ),
        'pending_requests': stats_data.get('pending_requests', 0),
        'active_requests': stats_data.get('active_requests', 0),
        'avg_response_time': stats_data.get('avg_response_time')
    }

    return jsonify(response)

# Patient Routes
@app.route('/api/patient/requests', methods=['GET'])
def get_patient_requests():
    # Identify patient by phone number (no authentication required)
    phone = request.args.get('phone')
    if not phone:
        return jsonify({'error': 'Phone number is required'}), 400

    patient_query = "SELECT patient_id FROM patients WHERE phone = %s ORDER BY patient_id DESC LIMIT 1"
    patient_result = db.execute_query(patient_query, (phone,))
    
    if not patient_result:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    patient_id = patient_result[0]['patient_id']
    
    query = """
    SELECT er.*, h.name as hospital_name, a.vehicle_number
    FROM emergency_requests er
    LEFT JOIN hospitals h ON er.hospital_id = h.hospital_id
    LEFT JOIN ambulances a ON er.ambulance_id = a.ambulance_id
    WHERE er.patient_id = %s
    ORDER BY er.created_at DESC
    """
    requests = db.execute_query(query, (patient_id,))
    return jsonify(requests)

# SuperAdmin Routes
@app.route('/api/admin/dashboard', methods=['GET'])
@role_required('superadmin')
def get_admin_dashboard():
    # Get system statistics
    stats_query = """
    SELECT 
        COUNT(DISTINCT h.hospital_id) as total_hospitals,
        SUM(h.total_ambulances) as total_ambulances,
        SUM(h.available_ambulances) as available_ambulances,
        COUNT(CASE WHEN er.status = 'pending' THEN 1 END) as pending_requests,
        COUNT(CASE WHEN er.status = 'in_progress' THEN 1 END) as active_requests,
        COUNT(CASE WHEN er.status = 'completed' THEN 1 END) as completed_requests
    FROM hospitals h
    LEFT JOIN emergency_requests er ON h.hospital_id = er.hospital_id
    """
    stats = db.execute_query(stats_query)
    
    # Get recent requests
    recent_query = """
    SELECT er.*, p.name as patient_name, h.name as hospital_name
    FROM emergency_requests er
    JOIN patients p ON er.patient_id = p.patient_id
    LEFT JOIN hospitals h ON er.hospital_id = h.hospital_id
    ORDER BY er.created_at DESC
    LIMIT 10
    """
    recent_requests = db.execute_query(recent_query)
    
    return jsonify({
        'statistics': stats[0] if stats else {},
        'recent_requests': recent_requests
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
