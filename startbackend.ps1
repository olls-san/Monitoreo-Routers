$ErrorActionPreference = "Stop"

# Ir a la carpeta del script (raíz del proyecto)
Set-Location $PSScriptRoot

# Crear venv si no existe
if (!(Test-Path ".\.venv\Scripts\Activate.ps1")) {
    python -m venv .venv
}

# Activar venv
. .\.venv\Scripts\Activate.ps1

# Instalar deps (opcional: puedes comentarlo si no quieres hacerlo siempre)
pip install -r requirements.txt

# Variables de entorno (DB)
$env:MONITE_DATABASE_URL = "sqlite+aiosqlite:///./monite.db"

# Levantar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000

cd D:\Coding\routerManager\monite_web\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload