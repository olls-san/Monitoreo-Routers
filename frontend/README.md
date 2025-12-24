# MoniTe Web Frontend

This directory contains a basic React application built with Vite and
Tailwind CSS that replicates the desktop‑like experience of the
original PySide6 application. The interface is dark themed and
optimised for quick operations on routers.

## Getting started

1. Install dependencies (requires Node.js and npm):

   ```sh
   cd frontend
   npm install
   ```

2. Start the development server:

   ```sh
   npm run dev
   ```

   The app will be served at http://localhost:5173 and will proxy API
   requests to the backend running at http://localhost:8000 (configured
   in `vite.config.js`).

3. Build for production:

   ```sh
   npm run build
   ```

## Features implemented

- **Tab navigation**: The UI uses a horizontal tab bar similar to a
  desktop application. Only the *Routers* tab has been implemented in
  this MVP; other tabs are placeholders.
- **Router management**: You can list existing routers, add new
  routers via a modal dialog and select a router to perform actions.
- **Dynamic actions**: Once a router is selected you can trigger
  supported actions (consultar saldo, recargar saldo, ver logs USSD).
  Results are displayed in a monospaced console panel with raw and
  parsed output.
- **Dark theme**: Colours are defined in `tailwind.config.js` to match
  the provided specification.

## Extending the UI

This frontend is a starting point. To support additional router
types, actions, automation configuration and history views you can
add further tabs and components following the same patterns used in
`src/App.jsx`. For example, a *Historial* tab could fetch and display
action runs from the `/runs` endpoint with filters and pagination.
