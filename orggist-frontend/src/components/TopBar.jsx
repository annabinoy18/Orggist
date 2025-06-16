import React from 'react';
import './TopBar.css';
import { Link } from 'react-router-dom';

const TopBar = ({ user }) => {
  return (
    <header className="top-bar">
      <div className="brand">
        <Link to="/" className="nav-link brand-link">FMS HUB</Link>
      </div>

      <nav className="nav-links">
        <Link to="/login" className="nav-link">Login</Link>
        <Link to="/search" className="nav-link">Search</Link>
      </nav>

      {user && (
        <div className="user-info">
          <img src={user.picture} alt="avatar" />
          <span>{user.name}</span>
        </div>
      )}
    </header>
  );
};

export default TopBar;
