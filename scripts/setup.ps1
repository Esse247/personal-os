param(
    [string]$BootstrapPython = $env:PERSONAL_OS_BOOTSTRAP_PYTHON
)

$ErrorActionPreference = 'Stop'

if (-not $BootstrapPython) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { $BootstrapPython = $command.Source }
}

if (-not $BootstrapPython) {
    throw 'Python 3.12+ was not found. Set PERSONAL_OS_BOOTSTRAP_PYTHON to a trusted Python executable.'
}

& $BootstrapPython -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e 'backend[dev]'
& npm.cmd install
if ($LASTEXITCODE -ne 0) { throw 'npm install failed' }
& .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'database migration failed' }
& .\.venv\Scripts\python.exe -m personal_os.cli fixtures-load
if ($LASTEXITCODE -ne 0) { throw 'fixture loading failed' }
npm.cmd run setup:check
if ($LASTEXITCODE -ne 0) { throw 'setup verification failed' }

Write-Output 'Setup complete. All runtime data is synthetic and all providers are mocked.'
