# Build ZenTray Windows installer inside WinBoat / Windows guest.
# Invoked via freerdp RemoteApp against shared folder \\host.lan\Data\...
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Log = "\\host.lan\Data\workspace\private\my_todo\dist\releases\win_build.log"
$Project = "\\host.lan\Data\workspace\private\my_todo"
$Releases = Join-Path $Project "dist\releases"
$MarkerOk = Join-Path $Releases "win_build.ok"
$MarkerFail = Join-Path $Releases "win_build.fail"

function Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Host $line
}

try {
    New-Item -ItemType Directory -Force -Path $Releases | Out-Null
    if (Test-Path $MarkerOk) { Remove-Item $MarkerOk -Force }
    if (Test-Path $MarkerFail) { Remove-Item $MarkerFail -Force }
    "" | Set-Content -Path $Log -Encoding UTF8
    Log "=== ZenTray Windows build start ==="
    Log "Project: $Project"
    Set-Location $Project

    # --- Ensure Python 3.12 ---
    $py = $null
    foreach ($c in @("python", "py")) {
        try {
            $v = & $c --version 2>&1 | Out-String
            if ($v -match "Python 3\.(1[0-9]|[2-9]\d)") {
                $py = $c
                Log "Found $c : $v"
                break
            }
        } catch {}
    }

    if (-not $py) {
        Log "Installing Python 3.12 (silent)..."
        $installer = Join-Path $env:TEMP "python-3.12.8-amd64.exe"
        $url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        Invoke-WebRequest -Uri $url -OutFile $installer
        $args = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1 SimpleInstall=1"
        $p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
        Log "Python installer exit: $($p.ExitCode)"
        # refresh PATH for this process
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
        $py = "python"
        & $py --version
        if ($LASTEXITCODE -ne 0) { throw "Python still not available after install" }
    }

    Log "Creating venv..."
    $venvPy = Join-Path $Project "venv_win\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        & $py -m venv (Join-Path $Project "venv_win")
    }
    Log "Upgrading pip / installing deps..."
    & $venvPy -m pip install -U pip wheel
    & $venvPy -m pip install -e ".[dev]" pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

    # web/dist should already be committed; rebuild if node available
    $webDist = Join-Path $Project "web\dist\index.html"
    if (-not (Test-Path $webDist)) {
        Log "web/dist missing; trying npm build..."
        $node = Get-Command npm -ErrorAction SilentlyContinue
        if ($node) {
            Push-Location (Join-Path $Project "web")
            npm ci
            npm run build
            Pop-Location
        } else {
            throw "web/dist missing and npm not installed"
        }
    } else {
        Log "Using existing web/dist"
    }

    Log "PyInstaller zentray.spec..."
    & $venvPy -m PyInstaller zentray.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "zentray.spec failed" }
    $appExe = Join-Path $Project "dist\ZenTray.exe"
    if (-not (Test-Path $appExe)) { throw "missing dist\ZenTray.exe" }
    Log ("Main app size: {0:N1} MB" -f ((Get-Item $appExe).Length / 1MB))

    Log "PyInstaller installer.spec..."
    & $venvPy -m PyInstaller installer.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "installer.spec failed" }

    $ver = & $venvPy -c "from zentray.config import VERSION; print(VERSION)"
    $ver = $ver.Trim()
    $src = Join-Path $Project "dist\ZenTrayInstaller.exe"
    if (-not (Test-Path $src)) { throw "missing dist\ZenTrayInstaller.exe" }
    $out = Join-Path $Releases "ZenTrayInstaller-$ver-x64.exe"
    Copy-Item -Force $src $out
    Log "Artifact: $out ($([math]::Round((Get-Item $out).Length/1MB,1)) MB)"
    Set-Content -Path $MarkerOk -Value $out -Encoding UTF8
    Log "=== BUILD OK ==="
    exit 0
}
catch {
    $err = $_.Exception.Message
    try { Log "ERROR: $err" } catch {}
    try { Set-Content -Path $MarkerFail -Value $err -Encoding UTF8 } catch {}
    exit 1
}
