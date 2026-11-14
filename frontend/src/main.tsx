import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import { AuthProvider } from "./context/AuthContext.tsx";
import { OnboardingProvider } from "./context/OnboardingContext.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <OnboardingProvider>
          <App />
        </OnboardingProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
