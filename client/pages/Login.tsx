import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mail, Lock, Eye, EyeOff, AlertCircle } from "lucide-react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  auth,
  signInWithGoogle,
  signInWithGithub,
  saveUserData,
  updateLastLogin,
} from "@/services/firebase";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"login" | "signup">("login");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    if (!email || !password) {
      setError("Please fill in all fields");
      setIsLoading(false);
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      setIsLoading(false);
      return;
    }

    // Check if admin email
    const isAdminEmail = email.toLowerCase() === "admin@legally.com";

    try {
      if (isAdminEmail) {
        // Admin login - call admin backend API
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${apiBaseUrl}/api/v1/admin/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (data.success && data.token) {
          localStorage.setItem("adminToken", data.token);
          localStorage.setItem("adminEmail", email);
          localStorage.setItem("isAuthenticated", "true");
          navigate("/admin/dashboard");
          return;
        } else {
          setError(data.message || "Invalid admin credentials");
          setIsLoading(false);
          return;
        }
      }

      // Normal user login
      if (mode === "signup") {
        const userCredential = await createUserWithEmailAndPassword(
          auth,
          email,
          password
        );
        const user = userCredential.user;
        
        // Save user data to Firebase Realtime Database
        await saveUserData({
          uid: user.uid,
          email: user.email || email,
          displayName: user.displayName || undefined,
          photoURL: user.photoURL || undefined,
        });
        
        localStorage.setItem("isAuthenticated", "true");
        localStorage.setItem("userEmail", user.email || email);
        localStorage.setItem("userId", user.uid);
      } else {
        const userCredential = await signInWithEmailAndPassword(
          auth,
          email,
          password
        );
        const user = userCredential.user;
        
        // Update last login timestamp
        await updateLastLogin(user.uid);
        
        localStorage.setItem("isAuthenticated", "true");
        localStorage.setItem("userEmail", user.email || email);
        localStorage.setItem("userId", user.uid);
      }

      navigate("/");
    } catch (err) {
      let errorMessage = "Authentication failed. Please try again.";

      if (err instanceof Error) {
        if (err.message.includes("auth/user-not-found")) {
          errorMessage = "No account found with this email address.";
        } else if (err.message.includes("auth/wrong-password")) {
          errorMessage = "Incorrect password. Please try again.";
        } else if (err.message.includes("auth/invalid-credential")) {
          errorMessage = "Invalid email or password. Please check your credentials and try again.";
        } else if (err.message.includes("auth/email-already-in-use")) {
          errorMessage = "An account with this email already exists.";
        } else if (err.message.includes("auth/weak-password")) {
          errorMessage = "Password is too weak. Use at least 6 characters.";
        } else if (err.message.includes("auth/invalid-email")) {
          errorMessage = "Please enter a valid email address.";
        } else if (err.message.includes("auth/too-many-requests")) {
          errorMessage = "Too many failed attempts. Please try again later or reset your password.";
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError("");
    setIsLoading(true);

    try {
      const user = await signInWithGoogle();
      
      // Save/update user data to Firebase Realtime Database
      await saveUserData({
        uid: user.uid,
        email: user.email || "",
        displayName: user.displayName || undefined,
        photoURL: user.photoURL || undefined,
      });
      
      localStorage.setItem("isAuthenticated", "true");
      localStorage.setItem("userEmail", user.email || "");
      localStorage.setItem("userId", user.uid);
      navigate("/");
    } catch (err) {
      let errorMessage = "Google sign-in failed. Please try again.";

      if (err instanceof Error) {
        if (err.message.includes("popup-closed-by-user")) {
          errorMessage = "Sign-in was cancelled.";
        } else if (err.message.includes("popup-blocked")) {
          errorMessage = "Please allow popups to sign in with Google.";
        } else if (err.message.includes("auth/invalid-credential")) {
          errorMessage = "Google sign-in failed. Make sure Google authentication is enabled in Firebase Console.";
        } else if (err.message.includes("auth/account-exists-with-different-credential")) {
          errorMessage = "An account already exists with this email using a different sign-in method.";
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
      setIsLoading(false);
    }
  };

  const handleGithubSignIn = async () => {
    setError("");
    setIsLoading(true);

    try {
      const user = await signInWithGithub();
      
      // Save/update user data to Firebase Realtime Database
      await saveUserData({
        uid: user.uid,
        email: user.email || "",
        displayName: user.displayName || undefined,
        photoURL: user.photoURL || undefined,
      });
      
      localStorage.setItem("isAuthenticated", "true");
      localStorage.setItem("userEmail", user.email || "");
      localStorage.setItem("userId", user.uid);
      navigate("/");
    } catch (err) {
      let errorMessage = "GitHub sign-in failed. Please try again.";

      if (err instanceof Error) {
        if (err.message.includes("popup-closed-by-user")) {
          errorMessage = "Sign-in was cancelled.";
        } else if (err.message.includes("popup-blocked")) {
          errorMessage = "Please allow popups to sign in with GitHub.";
        } else if (err.message.includes("auth/invalid-credential")) {
          errorMessage = "GitHub sign-in failed. Make sure GitHub authentication is enabled in Firebase Console.";
        } else if (err.message.includes("auth/account-exists-with-different-credential")) {
          errorMessage = "An account already exists with this email using a different sign-in method.";
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4 py-12 overflow-hidden">
      {/* Background animated elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-white/5 to-transparent rounded-full blur-3xl animate-pulse-scale"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-white/5 to-transparent rounded-full blur-3xl animate-pulse-scale" style={{ animationDelay: "1s" }}></div>
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo/Header */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-2 animate-dancing-glow">
            Legally
          </h1>
          <div className="h-1 w-32 mx-auto bg-gradient-to-r from-transparent via-white to-transparent mb-6 animate-shimmer"></div>
          <p className="text-white/60 text-sm animate-glow-text">
            AI-Powered Legal Intelligence Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="relative bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur-xl hover:border-white/20 transition-all duration-500 animate-slide-up">
          {/* Glow effect on hover */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-white/5 rounded-2xl opacity-0 hover:opacity-100 transition-opacity duration-500"></div>

          <div className="relative z-10">
            {/* Mode Toggle */}
            <div className="flex gap-4 mb-8">
              <button
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all duration-300 ${
                  mode === "login"
                    ? "bg-white text-black shadow-lg shadow-white/30 scale-105"
                    : "bg-white/5 text-white hover:bg-white/10"
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => {
                  setMode("signup");
                  setError("");
                }}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all duration-300 ${
                  mode === "signup"
                    ? "bg-white text-black shadow-lg shadow-white/30 scale-105"
                    : "bg-white/5 text-white hover:bg-white/10"
                }`}
              >
                Sign Up
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex gap-3 items-start animate-bounce-in">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email Input */}
              <div className="group relative">
                <label className="block text-xs font-semibold text-white/70 mb-2 group-focus-within:text-white transition-colors">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40 group-focus-within:text-white/60 transition-colors" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full bg-white/5 border border-white/10 rounded-lg pl-12 pr-4 py-3 text-white placeholder-white/30 focus:outline-none focus:border-white/30 focus:ring-2 focus:ring-white/20 focus:bg-white/10 transition-all duration-300 group-focus-within:shadow-lg group-focus-within:shadow-white/10"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="group relative">
                <label className="block text-xs font-semibold text-white/70 mb-2 group-focus-within:text-white transition-colors">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40 group-focus-within:text-white/60 transition-colors" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-white/5 border border-white/10 rounded-lg pl-12 pr-12 py-3 text-white placeholder-white/30 focus:outline-none focus:border-white/30 focus:ring-2 focus:ring-white/20 focus:bg-white/10 transition-all duration-300 group-focus-within:shadow-lg group-focus-within:shadow-white/10"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors group-focus-within:text-white/60"
                  >
                    {showPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Remember Me / Forgot Password */}
              {mode === "login" && (
                <div className="flex items-center justify-between text-xs">
                  <label className="flex items-center gap-2 text-white/60 hover:text-white/80 cursor-pointer transition-colors group">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-white/20 bg-white/5 accent-white"
                    />
                    <span>Remember me</span>
                  </label>
                  <button
                    type="button"
                    className="text-white/60 hover:text-white transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full bg-white text-black font-semibold py-3 rounded-lg hover:bg-white/90 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95 shadow-lg shadow-white/20 hover:shadow-white/40 overflow-hidden"
              >
                <span className="absolute inset-0 bg-black/20 transform scale-0 group-active:scale-100 transition-transform duration-500 origin-center rounded-lg"></span>
                <span className="relative z-10">
                  {isLoading
                    ? "Processing..."
                    : mode === "login"
                      ? "Sign In"
                      : "Create Account"}
                </span>
              </button>
            </form>

            {/* Divider */}
            <div className="my-8 flex items-center gap-4">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent to-white/10"></div>
              <span className="text-white/40 text-xs">OR</span>
              <div className="flex-1 h-px bg-gradient-to-l from-transparent to-white/10"></div>
            </div>

            {/* OAuth Buttons */}
            <div className="space-y-3">
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={isLoading}
                className="group w-full flex items-center justify-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white hover:bg-white/10 hover:border-white/20 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span className="text-sm font-medium">
                  {isLoading ? "Signing in..." : "Google"}
                </span>
              </button>

              <button
                type="button"
                onClick={handleGithubSignIn}
                disabled={isLoading}
                className="group w-full flex items-center justify-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white hover:bg-white/10 hover:border-white/20 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v 3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                <span className="text-sm font-medium">
                  {isLoading ? "Signing in..." : "GitHub"}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Footer Text */}
        <p className="text-center text-white/50 text-xs mt-8 animate-fade-in" style={{ animationDelay: "0.3s" }}>
          {mode === "login"
            ? "Don't have an account? "
            : "Already have an account? "}
          <button
            onClick={() => setMode(mode === "login" ? "signup" : "login")}
            className="text-white hover:underline transition-all duration-200"
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>

        {/* Legal Disclaimer */}
        <p className="text-center text-white/40 text-xs mt-6 leading-relaxed">
          By continuing, you agree to our{" "}
          <button className="text-white/60 hover:text-white transition-colors underline">
            Terms of Service
          </button>{" "}
          and{" "}
          <button className="text-white/60 hover:text-white transition-colors underline">
            Privacy Policy
          </button>
        </p>
      </div>
    </div>
  );
}
