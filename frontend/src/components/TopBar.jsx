import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

const tabs = [
  { path: "/", label: "Routers" },
  { path: "/history", label: "Historial" },
  { path: "/commands", label: "Comandos" },
  { path: "/settings", label: "Configuración" },
];

export default function TopBar() {
  const navigate = useNavigate();

  return (
    <div className="sticky top-0 z-50 border-b border-gray-800 bg-gray-900">
      <div className="px-4 py-3 flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gray-800 flex items-center justify-center font-bold">
            MR
          </div>
          <div className="leading-tight">
            <div className="font-semibold">Monitoreos Routers</div>
            <div className="text-xs text-gray-400 -mt-0.5">Panel</div>
          </div>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {tabs.map((t) => (
            <NavLink
              key={t.path}
              to={t.path}
              end={t.path === "/"}
              className={({ isActive }) =>
                `px-4 py-2 rounded-lg text-sm ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-gray-300 hover:bg-gray-800"
                }`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-4">
          <div className="text-sm text-gray-300">
            Backend: <span className="text-green-400">conectado</span>
          </div>
        </div>
      </div>
    </div>
  );
}
