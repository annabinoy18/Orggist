// components/LoginPage.js
import React from "react";
import "./LoginPage.css";

const LoginPage = () => {
  const backendGoogleLoginUrl = "http://localhost:8080/oauth2/authorization/google";

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Welcome back!</h1>
        <p>Sign in to your account to continue</p>

        <a href={backendGoogleLoginUrl} className="google-btn">
          <img src="https://developers.google.com/identity/images/g-logo.png" alt="Google icon" />
          Continue with Google
        </a>

        <div className="divider"><span>OR</span></div>

        <form>
          <label>Email</label>
          <input type="email" placeholder="demo@bootlab.io" required />

          <label>Password</label>
          <input type="password" placeholder="********" required />

          <div className="options">
            <label>
              <input type="checkbox" /> Remember me
            </label>
            <a href="#">Forgot password?</a>
          </div>

          <button type="submit" className="sign-in-btn">Sign in</button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
