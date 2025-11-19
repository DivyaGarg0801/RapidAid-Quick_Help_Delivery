import React, { useEffect, useState } from 'react';
import './App.css';
import { api } from './api';
import PatientDashboard from './components/PatientDashboard';
import HospitalDashboard from './components/HospitalDashboard';
import SuperAdminDashboard from './components/SuperAdminDashboard';

function App() {
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState('patient');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  useEffect(() => {
    api
      .currentUser()
      .then(u => {
        setUser(u);
        if (u.role === 'patient') setView('patient');
        else if (u.role === 'hospital_admin') setView('hospital');
        else setView('admin');
      })
      .catch(() => {})
      .finally(() => setLoadingUser(false));
  }, []);

  const quickPatientAccess = () => {
    setError(null);
    setView('patient');
  };

  const handleLogin = async e => {
    e.preventDefault();
    setError(null);
    setAuthLoading(true);
    try {
      const u = await api.login(username, password);
      setUser(u);
      if (u.role === 'patient') setView('patient');
      else if (u.role === 'hospital_admin') setView('hospital');
      else setView('admin');
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    setUser(null);
    setUsername('');
    setPassword('');
  };

  const renderDashboard = () => {
    if (view === 'patient') return <PatientDashboard />;
    if (!user) return null;
    if (user.role === 'hospital_admin') return <HospitalDashboard />;
    if (user.role === 'superadmin') return <SuperAdminDashboard />;
    return null;
  };

  return (
    <div className="app-root">
      <header className="top-bar">
        <div className="brand">RapidAid</div>
        <div className="top-bar-right">
          {user ? (
            <>
              <span className="user-pill">
                {user.username} ({user.role})
              </span>
              <button className="btn" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : null}
        </div>
      </header>

      <main className="app-main">
        {!user && (
          <>
            <section className="card landing-card">
              <h1>Welcome to RapidAid</h1>
              <p>Select how you want to use the system:</p>
              <div className="role-grid">
                <div className="role-card">
                  <h3>Patient</h3>
                  <p>
                    Request an ambulance, see nearest hospitals, view distance and estimated
                    arrival time, and track your emergency request.
                  </p>
                  <p className="hint">
                    Example login: <code>johndoe</code>
                  </p>
                  <button className="btn primary" onClick={quickPatientAccess} disabled={authLoading}>
                    {authLoading ? 'Starting...' : 'Continue as Patient'}
                  </button>
                </div>
                <div className="role-card">
                  <h3>Hospital</h3>
                  <p>
                    View and manage your emergency queue using Priority, FCFS, or SJF (nearest
                    hospital) algorithms and allocate ambulances.
                  </p>
                  <p className="hint">
                    Example login: <code>hospital1_admin</code>
                  </p>
                </div>
                <div className="role-card">
                  <h3>SuperAdmin</h3>
                  <p>
                    Add hospitals with latitude/longitude, configure scheduling algorithms, and
                    monitor system-wide statistics and request flow.
                  </p>
                  <p className="hint">
                    Example login: <code>admin</code>
                  </p>
                </div>
              </div>
            </section>

            <section className="card auth-card">
              <h2>Hospital / SuperAdmin Login</h2>
              {error && <div className="error">{error}</div>}
              <form onSubmit={handleLogin} className="form">
                <label>
                  Username
                  <input
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                </label>
                <button type="submit" className="btn primary" disabled={authLoading}>
                  {authLoading ? 'Logging in...' : 'Login'}
                </button>
                <p className="hint">
                  Use the usernames above with the password you configured in MySQL (for example,
                  <code>password123</code>).
                </p>
              </form>
            </section>
          </>
        )}

        {user && (
          <>
            <nav className="tabs">
              {user.role === 'patient' && (
                <button
                  className={view === 'patient' ? 'tab active' : 'tab'}
                  onClick={() => setView('patient')}
                >
                  Patient
                </button>
              )}
              {user.role === 'hospital_admin' && (
                <button
                  className={view === 'hospital' ? 'tab active' : 'tab'}
                  onClick={() => setView('hospital')}
                >
                  Hospital
                </button>
              )}
              {user.role === 'superadmin' && (
                <button
                  className={view === 'admin' ? 'tab active' : 'tab'}
                  onClick={() => setView('admin')}
                >
                  SuperAdmin
                </button>
              )}
            </nav>
          </>
        )}

        {renderDashboard()}

        {loadingUser && <div className="hint">Checking session...</div>}
      </main>
    </div>
  );
}

export default App;
