// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../api';

export const HospitalDashboard = () => {
  const [hospitals, setHospitals] = useState([]);
  const [selectedHospitalId, setSelectedHospitalId] = useState('');
  const [queue, setQueue] = useState([]);
  const [ambulances, setAmbulances] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getHospitals().then(setHospitals).catch(err => setError(err.message));
  }, []);

  const loadHospitalData = async hospitalId => {
    setError(null);
    setLoading(true);
    try {
      const [queueData, ambulanceData, statusData] = await Promise.all([
        api.getHospitalQueue(hospitalId),
        api.getAmbulances(hospitalId),
        api.getHospitalStatus(hospitalId),
      ]);
      setQueue(queueData);
      setAmbulances(ambulanceData as Ambulance[]);
      setStatus(statusData);
    } catch (err) {
      setError(err.message || 'Failed to load hospital data');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async requestId => {
    setError(null);
    setMessage(null);
    try {
      await api.completeRequest(requestId);
      setMessage(`Request ${requestId} marked as completed.`);
      if (selectedHospitalId) {
        await loadHospitalData(Number(selectedHospitalId));
      }
    } catch (err) {
      setError(err.message || 'Failed to complete request');
    }
  };

  const availableAmbulances = useMemo(
    () =>
      (ambulances || []).filter(
        a => (a.status || '').trim().toLowerCase() === 'available'
      ),
    [ambulances]
  );

  const handleHospitalChange = value => {
    const id = value ? Number(value) : '';
    setSelectedHospitalId(id);
    if (id) {
      loadHospitalData(id);
    } else {
      setQueue([]);
      setAmbulances([]);
      setStatus(null);
    }
  };

  const handleAssign = async (reqId, ambId) => {
    setError(null);
    setMessage(null);
    try {
      await api.assignAmbulance(reqId, ambId);
      setMessage(`Ambulance ${ambId} assigned to request ${reqId}.`);
      if (selectedHospitalId) {
        await loadHospitalData(Number(selectedHospitalId));
      }
    } catch (err) {
      setError(err.message || 'Failed to assign ambulance');
    }
  };

  return (
    <div className="dashboard">
      <h2>Hospital Dashboard</h2>

      <section className="card">
        <h3>Select Hospital & Scheduling</h3>
        <label>
          Hospital
          <select
            value={selectedHospitalId}
            onChange={e => handleHospitalChange(e.target.value)}
          >
            <option value="">Choose hospital</option>
            {hospitals.map(h => (
              <option key={h.hospital_id} value={h.hospital_id}>
                {h.name} - Algo: {h.scheduling_algorithm?.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
        {status && (
          <div className="stats-grid">
            <div>Ambulances: {status.available_ambulances}/{status.total_ambulances}</div>
            <div>Active Ambulances: {status.active_ambulances}</div>
            <div>Doctors: {status.available_doctors}/{status.total_doctors}</div>
            <div>Rooms: {status.available_rooms}/{status.total_rooms}</div>
            <div>Pending Requests: {status.pending_requests}</div>
            <div>Active Requests: {status.active_requests}</div>
            <div>Avg Response (min): {status.avg_response_time ?? '-'}</div>
          </div>
        )}
        {loading && <div className="hint">Loading hospital data...</div>}
      </section>

      <section className="card">
        <h3>Incoming Queue</h3>
        {error && <div className="error">{error}</div>}
        {queue.length === 0 && <p>No pending requests.</p>}
        {queue.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Patient</th>
                <th>Priority</th>
                <th>Symptoms</th>
                <th>Status</th>
                <th>Assign Ambulance</th>
              </tr>
            </thead>
            <tbody>
              {queue.map(r => (
                <tr key={r.request_id}>
                  <td>{r.request_id}</td>
                  <td>{r.patient_id}</td>
                  <td>{r.priority_level.toUpperCase()}</td>
                  <td>{r.symptoms}</td>
                  <td>{r.status}</td>
                  <td>
                    {r.status === 'pending' ? (
                      <select
                        onChange={e => {
                          const ambId = Number(e.target.value);
                          if (ambId) handleAssign(r.request_id, ambId);
                        }}
                        defaultValue=""
                      >
                        <option value="">Select ambulance</option>
                        {availableAmbulances.map(a => (
                          <option key={a.ambulance_id} value={a.ambulance_id}>
                            {a.vehicle_number}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <button
                        className="btn secondary"
                        onClick={() => handleComplete(r.request_id)}
                        disabled={r.status === 'completed'}
                      >
                        {r.status === 'completed' ? 'Completed' : 'Mark complete'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {message && <div className="success">{message}</div>}
      </section>

      <section className="card">
        <h3>Ambulances</h3>
        {(ambulances || []).length === 0 && <p>No ambulances loaded.</p>}
        {(ambulances || []).length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Vehicle</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(ambulances || []).map(a => (
                <tr key={a.ambulance_id}>
                  <td>{a.ambulance_id}</td>
                  <td>{a.vehicle_number}</td>
                  <td>{a.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default HospitalDashboard;
