import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './components/LoginPage.jsx';
import SearchPage from './components/SearchPage.jsx';
import UploadPage from './components/UploadPage.jsx';

function App() {
  return (
    <Router>
      <Routes>
        {/* Redirect root / to /login */}
        <Route path="/" element={<Navigate to="/login" />} />

        {/* Actual routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/upload" element={<UploadPage />} />
      </Routes>
    </Router>
  );
}
export default App;