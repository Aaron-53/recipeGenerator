import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleGoogleCallback } = useAuth();

  useEffect(() => {
    const token = searchParams.get("token");

    if (token) {
      handleGoogleCallback(token).then((result) => {
        if (result.success) {
          navigate("/dashboard");
        } else {
          navigate("/login?error=google_auth_failed");
        }
      });
    } else {
      navigate("/login?error=no_token");
    }
  }, [searchParams, navigate, handleGoogleCallback]);

  return (
    <div className="loading">
      <h2>Authenticating with Google...</h2>
      <p>Please wait while we complete your login.</p>
    </div>
  );
};

export default AuthCallback;
