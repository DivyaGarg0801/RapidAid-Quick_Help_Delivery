// @ts-nocheck
const API_BASE = 'http://localhost:5000/api';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.error || `Request failed with ${res.status}`);
  }

  return res.json();
}

export const api = {
  login(username, password) {
    return request('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },
  logout() {
    return request('/logout', { method: 'POST' });
  },
  currentUser() {
    return request('/current_user');
  },
  getHospitals() {
    return request('/hospitals');
  },
  createHospital(payload) {
    return request('/hospitals', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  updateHospital(hospitalId, payload) {
    return request(`/hospitals/${hospitalId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },
  deleteHospital(hospitalId) {
    return request(`/hospitals/${hospitalId}`, { method: 'DELETE' });
  },
  createEmergencyRequest(payload) {
    return request('/emergency_requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  getPatientRequests(phone) {
    const q = encodeURIComponent(phone);
    return request(`/patient/requests?phone=${q}`);
  },
  getHospitalQueue(hospitalId) {
    return request(`/emergency_requests/${hospitalId}/queue`);
  },
  getHospitalStatus(hospitalId) {
    return request(`/hospitals/${hospitalId}/status`);
  },
  getAmbulances(hospitalId) {
    return request(`/ambulances/${hospitalId}`);
  },
  assignAmbulance(requestId, ambulanceId) {
    return request(`/emergency_requests/${requestId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ ambulance_id: ambulanceId }),
    });
  },
  completeRequest(requestId) {
    return request(`/emergency_requests/${requestId}/complete`, {
      method: 'POST',
    });
  },
  getAdminDashboard() {
    return request('/admin/dashboard');
  },
  updateHospitalAlgorithm(hospitalId, algorithm) {
    return request(`/hospitals/${hospitalId}/algorithm`, {
      method: 'PUT',
      body: JSON.stringify({ algorithm }),
    });
  },
};
