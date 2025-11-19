// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { api } from '../api';

const emptyForm = () => ({
  name: '',
  address: '',
  latitude: '',
  longitude: '',
  phone: '',
  total_ambulances: '5',
  available_ambulances: '5',
  total_doctors: '10',
  available_doctors: '10',
  total_rooms: '20',
  available_rooms: '20',
});

export const SuperAdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [hospitals, setHospitals] = useState([]);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [editingHospitalId, setEditingHospitalId] = useState(null);

  const [form, setForm] = useState(emptyForm());

  useEffect(() => {
    refreshAll();
  }, []);

  const refreshAll = async () => {
    setError(null);
    try {
      const [adminData, hospitalData] = await Promise.all([
        api.getAdminDashboard(),
        api.getHospitals(),
      ]);
      setStats(adminData.statistics);
      setRecent(adminData.recent_requests || []);
      setHospitals(hospitalData);
    } catch (err) {
      setError(err.message || 'Failed to load admin dashboard');
    }
  };

  const handleChange = e => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const resetForm = () => {
    setEditingHospitalId(null);
    setForm(emptyForm());
  };

  const handleCreateOrUpdateHospital = async e => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const payload = {
        name: form.name,
        address: form.address,
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        phone: form.phone,
        total_ambulances: Number(form.total_ambulances),
        available_ambulances: Number(form.available_ambulances),
        total_doctors: Number(form.total_doctors),
        available_doctors: Number(form.available_doctors),
        total_rooms: Number(form.total_rooms),
        available_rooms: Number(form.available_rooms),
      };

      if (editingHospitalId) {
        await api.updateHospital(editingHospitalId, payload);
        setMessage('Hospital updated successfully.');
      } else {
        await api.createHospital(payload);
        setMessage('Hospital created successfully.');
      }

      resetForm();
      await refreshAll();
    } catch (err) {
      setError(err.message || 'Failed to save hospital');
    }
  };

  const startEditHospital = hospital => {
    setEditingHospitalId(hospital.hospital_id);
    setForm({
      name: hospital.name,
      address: hospital.address,
      latitude: hospital.latitude?.toString() ?? '',
      longitude: hospital.longitude?.toString() ?? '',
      phone: hospital.phone || '',
      total_ambulances: hospital.total_ambulances?.toString() ?? '0',
      available_ambulances: hospital.available_ambulances?.toString() ?? '0',
      total_doctors: hospital.total_doctors?.toString() ?? '0',
      available_doctors: hospital.available_doctors?.toString() ?? '0',
      total_rooms: hospital.total_rooms?.toString() ?? '0',
      available_rooms: hospital.available_rooms?.toString() ?? '0',
    });
  };

  const handleDeleteHospital = async hospitalId => {
    if (!window.confirm('Delete this hospital? This cannot be undone.')) return;
    setError(null);
    setMessage(null);
    try {
      await api.deleteHospital(hospitalId);
      if (editingHospitalId === hospitalId) {
        resetForm();
      }
      setMessage('Hospital deleted.');
      await refreshAll();
    } catch (err) {
      setError(err.message || 'Failed to delete hospital');
    }
  };

  const handleAlgorithmChange = async (hospitalId, value) => {
    if (!value) return;
    setError(null);
    setMessage(null);
    try {
      await api.updateHospitalAlgorithm(hospitalId, value);
      setMessage('Scheduling algorithm updated.');
      await refreshAll();
    } catch (err) {
      setError(err.message || 'Failed to update algorithm');
    }
  };

  return (
    <div className="dashboard">
      <h2>SuperAdmin Dashboard</h2>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}

      <section className="card">
        <h3>System Overview</h3>
        {stats ? (
          <div className="stats-grid">
            <div>Total Hospitals: {stats.total_hospitals}</div>
            <div>Total Ambulances: {stats.total_ambulances}</div>
            <div>Available Ambulances: {stats.available_ambulances}</div>
            <div>Pending Requests: {stats.pending_requests}</div>
            <div>Active Requests: {stats.active_requests}</div>
            <div>Completed Requests: {stats.completed_requests}</div>
          </div>
        ) : (
          <p>No statistics loaded.</p>
        )}
      </section>

      <section className="card">
        <h3>{editingHospitalId ? 'Edit Hospital' : 'Add Hospital'}</h3>
        <form className="form" onSubmit={handleCreateOrUpdateHospital}>
          <label>
            Name
            <input name="name" value={form.name} onChange={handleChange} required />
          </label>
          <label>
            Address
            <input name="address" value={form.address} onChange={handleChange} required />
          </label>
          <label>
            Latitude
            <input name="latitude" value={form.latitude} onChange={handleChange} required />
          </label>
          <label>
            Longitude
            <input name="longitude" value={form.longitude} onChange={handleChange} required />
          </label>
          <label>
            Phone
            <input name="phone" value={form.phone} onChange={handleChange} />
          </label>
          <div className="field-row">
            <label>
              Ambulances
              <input name="total_ambulances" value={form.total_ambulances} onChange={handleChange} />
            </label>
            <label>
              Available Ambulances
              <input
                name="available_ambulances"
                value={form.available_ambulances}
                onChange={handleChange}
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              Doctors
              <input name="total_doctors" value={form.total_doctors} onChange={handleChange} />
            </label>
            <label>
              Available Doctors
              <input
                name="available_doctors"
                value={form.available_doctors}
                onChange={handleChange}
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              Rooms
              <input name="total_rooms" value={form.total_rooms} onChange={handleChange} />
            </label>
            <label>
              Available Rooms
              <input name="available_rooms" value={form.available_rooms} onChange={handleChange} />
            </label>
          </div>
          <div className="field-inline" style={{ marginTop: 12 }}>
            <button type="submit" className="btn primary">
              {editingHospitalId ? 'Save Changes' : 'Create Hospital'}
            </button>
            {editingHospitalId && (
              <button type="button" className="btn" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="card">
        <h3>Hospitals</h3>
        {hospitals.length === 0 && <p>No hospitals found.</p>}
        {hospitals.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Ambulances</th>
                <th>Algorithm</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {hospitals.map(h => (
                <tr key={h.hospital_id}>
                  <td>{h.hospital_id}</td>
                  <td>{h.name}</td>
                  <td>
                    {h.available_ambulances}/{h.total_ambulances}
                  </td>
                  <td>
                    <select
                      value={h.scheduling_algorithm || 'priority'}
                      onChange={e => handleAlgorithmChange(h.hospital_id, e.target.value)}
                    >
                      <option value="priority">PRIORITY</option>
                      <option value="fcfs">FCFS</option>
                      <option value="sjf">SJF</option>
                      <option value="hrrn">HRRN</option>
                    </select>
                  </td>
                  <td>
                    <button className="btn" onClick={() => startEditHospital(h)}>
                      Edit
                    </button>
                    <button
                      className="btn"
                      style={{ marginLeft: 6 }}
                      onClick={() => handleDeleteHospital(h.hospital_id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h3>Recent Requests</h3>
        {recent.length === 0 && <p>No recent requests.</p>}
        {recent.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Patient</th>
                <th>Hospital</th>
                <th>Priority</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recent.map(r => (
                <tr key={r.request_id}>
                  <td>{r.request_id}</td>
                  <td>{r.patient_name}</td>
                  <td>{r.hospital_name}</td>
                  <td>{r.priority_level}</td>
                  <td>{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default SuperAdminDashboard;
