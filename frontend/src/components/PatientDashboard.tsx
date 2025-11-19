// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, Marker, Polyline, TileLayer } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../api';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

export const PatientDashboard = () => {
  const [hospitals, setHospitals] = useState([]);
  const [selectedHospitalId, setSelectedHospitalId] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState({ lat: 0, lon: 0, hasLocation: false });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [requests, setRequests] = useState([]);
  const mapRef = useRef(null);

  const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const toRad = value => (value * Math.PI) / 180;
    const R = 6371;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  useEffect(() => {
    api.getHospitals().then(setHospitals).catch(err => setError(err.message));

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => {
          setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude, hasLocation: true });
        },
        () => {
          setLocation({ lat: 0, lon: 0, hasLocation: false });
        }
      );
    }
  }, []);

  const refreshRequests = async targetPhone => {
    if (!targetPhone) return;
    try {
      const updated = await api.getPatientRequests(targetPhone);
      setRequests(updated);
    } catch (err) {
      setError(err.message || 'Failed to fetch requests');
    }
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!selectedHospitalId || !symptoms.trim() || !name.trim() || !phone.trim()) {
      setError('Please fill your name, phone, select a hospital and symptom.');
      return;
    }

    setSubmitting(true);
    try {
      const lat = location.hasLocation ? location.lat : 0;
      const lon = location.hasLocation ? location.lon : 0;
      const res = await api.createEmergencyRequest({
        name,
        phone,
        hospital_id: Number(selectedHospitalId),
        symptoms,
        latitude: lat,
        longitude: lon,
      });
      setMessage(
        `Request #${res.request_id} created. Priority: ${res.priority_level.toUpperCase()}, ` +
          `ETA: ${res.estimated_arrival_time} min, Distance: ${res.distance_to_hospital.toFixed(2)} km`
      );
      setSymptoms('');
      setSelectedHospitalId('');
      await refreshRequests(phone);
    } catch (err) {
      setError(err.message || 'Failed to create request');
    } finally {
      setSubmitting(false);
    }
  };

  const hospitalsWithDistance = useMemo(() => {
    if (!location.hasLocation) return hospitals;
    return hospitals
      .map(h => ({
        ...h,
        distance: calculateDistance(location.lat, location.lon, h.latitude, h.longitude),
      }))
      .sort((a, b) => (a.distance ?? 0) - (b.distance ?? 0));
  }, [hospitals, location]);

  const selectedHospital = hospitals.find(h => h.hospital_id === Number(selectedHospitalId));

  const mapHref =
    selectedHospital && location.hasLocation
      ? `https://www.google.com/maps/dir/${location.lat},${location.lon}/${selectedHospital.latitude},${selectedHospital.longitude}`
      : undefined;

  const hasMapData = location.hasLocation && selectedHospital;

  useEffect(() => {
    if (hasMapData && mapRef.current) {
      mapRef.current.setView([location.lat, location.lon]);
    }
  }, [hasMapData, location.lat, location.lon, selectedHospitalId]);

  const autoSelectNearest = () => {
    if (!location.hasLocation || hospitalsWithDistance.length === 0) return;
    const nearest = hospitalsWithDistance[0];
    if (nearest) {
      setSelectedHospitalId(nearest.hospital_id);
    }
  };

  return (
    <div className="dashboard">
      <h2>Patient Dashboard</h2>

      <section className="card">
        <h3>New Emergency Request</h3>
        {error && <div className="error">{error}</div>}
        {message && <div className="success">{message}</div>}
        <form onSubmit={handleSubmit} className="form">
          <label>
            Name
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Your name" />
          </label>

          <label>
            Phone
            <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Your phone number" />
          </label>

          <label>
            Hospital
            <select
              value={selectedHospitalId}
              onChange={e => setSelectedHospitalId(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">Select hospital</option>
              {hospitalsWithDistance.map(h => (
                <option key={h.hospital_id} value={h.hospital_id}>
                  {h.name} (Ambulances: {h.available_ambulances}/{h.total_ambulances}
                  {h.distance ? ` • ${h.distance.toFixed(2)} km` : ''})
                </option>
              ))}
            </select>
          </label>
          {location.hasLocation && hospitalsWithDistance.length > 0 && (
            <button
              type="button"
              className="btn secondary"
              onClick={autoSelectNearest}
              style={{ alignSelf: 'flex-start' }}
            >
              Use nearest hospital
            </button>
          )}

          <label>
            Symptoms
            <select
              value={symptoms}
              onChange={e => setSymptoms(e.target.value)}
            >
              <option value="">Select symptom</option>
              <option value="heart attack">Severe chest pain / suspected heart attack</option>
              <option value="difficulty breathing">Difficulty breathing</option>
              <option value="severe bleeding">Severe bleeding</option>
              <option value="unconscious">Unconscious / unresponsive</option>
              <option value="broken bone">Broken bone / visible fracture</option>
              <option value="head injury">Head injury</option>
              <option value="burn">Serious burn</option>
              <option value="dizziness">Dizziness / feeling faint</option>
              <option value="fever">High fever</option>
              <option value="moderate pain">Moderate pain / minor cuts</option>
            </select>
          </label>

          <div className="field-inline">
            <span>
              Location: {location.hasLocation ? `${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}` : 'Not available'}
            </span>
            {mapHref && (
              <a href={mapHref} target="_blank" rel="noreferrer">
                View on Map
              </a>
            )}
          </div>

          {hasMapData && (
            <div className="map-container">
              <MapContainer
                center={[location.lat, location.lon]}
                zoom={13}
                style={{ height: 300, width: '100%' }}
                whenCreated={mapInstance => {
                  mapRef.current = mapInstance;
                }}
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution="&copy; OpenStreetMap contributors"
                />
                <Marker position={[location.lat, location.lon]} />
                <Marker position={[selectedHospital.latitude, selectedHospital.longitude]} />
                <Polyline
                  positions={[
                    [location.lat, location.lon],
                    [selectedHospital.latitude, selectedHospital.longitude],
                  ]}
                  color="#ff4d4f"
                />
              </MapContainer>
            </div>
          )}

          <button type="submit" disabled={submitting}>
            {submitting ? 'Submitting...' : 'Request Ambulance'}
          </button>
        </form>
      </section>

      <section className="card">
        <h3>My Requests</h3>
        {requests.length === 0 && <p>No requests yet.</p>}
        <div className="field-inline" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className="btn secondary"
            onClick={() => refreshRequests(phone)}
            disabled={!phone}
          >
            Refresh my requests
          </button>
        </div>
        {requests.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Hospital</th>
                <th>Priority</th>
                <th>Status</th>
                <th>ETA (min)</th>
                <th>Ambulance</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(r => (
                <tr key={r.request_id}>
                  <td>{r.request_id}</td>
                  <td>{r.hospital_name || r.hospital_id}</td>
                  <td>{r.priority_level.toUpperCase()}</td>
                  <td>{r.status}</td>
                  <td>{r.estimated_arrival_time ?? '-'}</td>
                  <td>{r.ambulance_id ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default PatientDashboard;
