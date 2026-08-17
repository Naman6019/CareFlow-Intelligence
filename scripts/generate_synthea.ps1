param (
    [int]$Population = 100,
    [string]$State = "Massachusetts",
    [string]$City = "",
    [string]$OutputDir = "$PSScriptRoot\..\data\raw\synthea_output"
)

$ErrorActionPreference = "Stop"

$ToolsDir = "$PSScriptRoot\tools"
$JarPath = "$ToolsDir\synthea-with-dependencies.jar"
$DownloadUrl = "https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar"

# Ensure directories exist
if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
}
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}

# Download Synthea standalone JAR if not already present
if (-not (Test-Path $JarPath)) {
    Write-Host "[Synthea] Downloading standalone synthea-with-dependencies.jar..." -ForegroundColor Cyan
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $JarPath
    Write-Host "[Synthea] Download complete!" -ForegroundColor Green
} else {
    Write-Host "[Synthea] Found existing synthea-with-dependencies.jar in $ToolsDir" -ForegroundColor Cyan
}

$AbsOutputDir = (Resolve-Path $OutputDir).Path
$AbsToolsDir = (Resolve-Path $ToolsDir).Path

# Convert Windows paths for Docker volume mapping
$DockerOutputDir = $AbsOutputDir -replace '\\', '/'
$DockerToolsDir = $AbsToolsDir -replace '\\', '/'

Write-Host "[Synthea] Generating $Population synthetic patient records for $State via Docker (eclipse-temurin:17-jre)..." -ForegroundColor Yellow

$DockerArgs = @(
    "run", "--rm",
    "-v", "${DockerOutputDir}:/output",
    "-v", "${DockerToolsDir}:/app",
    "-w", "/output",
    "eclipse-temurin:17-jre-alpine",
    "java", "-jar", "/app/synthea-with-dependencies.jar",
    "-p", "$Population",
    "--exporter.csv.export=true",
    "--exporter.fhir.export=true",
    "--exporter.baseDirectory=/output",
    "$State"
)

if ($City -ne "") {
    $DockerArgs += "$City"
}

& docker @DockerArgs

Write-Host "[Synthea] Generation complete! Files saved to: $AbsOutputDir" -ForegroundColor Green
