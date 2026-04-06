import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App"; // Este archivo importa App.tsx correctamente
import "./styles.css"; // Verifica que este archivo también sea accesible

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);