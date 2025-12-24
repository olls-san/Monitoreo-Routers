import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";
import { HostProvider } from "./contexts/HostContext.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <HostProvider>
        <App />
      </HostProvider>
    </BrowserRouter>
  </React.StrictMode>
);
