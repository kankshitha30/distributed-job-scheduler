import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Queues } from './pages/Queues';
import { QueueDetails } from './pages/QueueDetails';
import { JobExplorer } from './pages/JobExplorer';
import { JobDetails } from './pages/JobDetails';
import { Workers } from './pages/Workers';
import { Metrics } from './pages/Metrics';
import { api } from './services/api';
import { OverviewMetrics, Queue } from './types';
import { usePolling } from './hooks/usePolling';

const ProtectedRoutes: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [queues, setQueues] = useState<Queue[]>([]);

  const fetchGlobalData = async () => {
    if (!isAuthenticated) return;
    try {
      const [m, q] = await Promise.all([
        api.getMetricsOverview(),
        api.getQueues(),
      ]);
      setMetrics(m);
      setQueues(q);
    } catch (e) {
      console.error('Error polling dashboard state', e);
    }
  };

  const { isPolling, setIsPolling } = usePolling(fetchGlobalData, 5000);

  if (loading) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex items-center justify-center text-slate-400 text-sm">
        Initializing Distributed Job Scheduler...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Routes>
      <Route
        element={
          <Layout
            isPolling={isPolling}
            onTogglePolling={() => setIsPolling(!isPolling)}
            onRefresh={fetchGlobalData}
            activeWorkers={metrics?.active_workers || 0}
          />
        }
      >
        <Route
          index
          element={
            <Dashboard
              metrics={metrics}
              queues={queues}
              onRefresh={fetchGlobalData}
            />
          }
        />
        <Route
          path="queues"
          element={
            <Queues
              queues={queues}
              onRefresh={fetchGlobalData}
            />
          }
        />
        <Route path="queues/:queueId" element={<QueueDetails />} />
        <Route path="jobs" element={<JobExplorer />} />
        <Route path="jobs/:jobId" element={<JobDetails />} />
        <Route path="workers" element={<Workers />} />
        <Route path="metrics" element={<Metrics />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedRoutes />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
