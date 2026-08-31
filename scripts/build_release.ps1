[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [ValidateSet('Baseline', 'Conservative', 'Extended', 'Deduplicated')]
    [string]$OptimizationProfile = 'Deduplicated',

    [string]$BuildPython = 'python',
    [string]$BuildEnvironment = '.venv-build',
    [string]$DistPath = 'dist',
    [long]$BaselineBytes = 86995084,
    [long]$MaximumBytes = 62000000,
    [switch]$RecreateEnvironment,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$resolvedProject = (Resolve-Path $projectRoot).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
$environmentPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $BuildEnvironment))
$expectedPrefix = $resolvedProject + [IO.Path]::DirectorySeparatorChar
if (-not $environmentPath.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "BuildEnvironment must resolve inside the project: $environmentPath"
}

if ($RecreateEnvironment -and (Test-Path -LiteralPath $environmentPath)) {
    Remove-Item -LiteralPath $environmentPath -Recurse -Force
}
if (-not (Test-Path -LiteralPath $environmentPath)) {
    & $BuildPython -m venv $environmentPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create the release build environment.'
    }
}

$buildEnvironmentPython = Join-Path $environmentPath 'Scripts\python.exe'
if (-not $SkipDependencyInstall) {
    & $buildEnvironmentPython -m pip install --disable-pip-version-check -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to install release build dependencies.'
    }
}

$excludedModules = switch ($OptimizationProfile) {
    'Baseline' { @() }
    'Conservative' { @('mypy', 'lxml', 'PIL') }
    'Extended' { @('mypy', 'lxml', 'PIL', 'setuptools', 'pygments', 'rich', 'markdown_it', 'click') }
    'Deduplicated' { @('mypy', 'lxml', 'PIL', 'setuptools', 'pygments', 'rich', 'markdown_it', 'click') }
}

$iconPath = (Resolve-Path (Join-Path $projectRoot 'icon.ico')).Path
$packArguments = @(
    '-c', 'from flet.cli import main; main()',
    'pack', 'main.py',
    '-n', 'MetaDescriptionGenerator',
    '-i', $iconPath,
    '--product-name', 'Meta Description Generator',
    '--file-description', 'Gemini APIを利用したMeta title・description生成ツール',
    '--product-version', $Version,
    '--file-version', "$Version.0",
    '--distpath', $DistPath,
    '-y',
    '--pyinstaller-build-args=--clean'
)
foreach ($module in $excludedModules) {
    $packArguments += "--pyinstaller-build-args=--exclude-module=$module"
}

if ($OptimizationProfile -eq 'Deduplicated') {
    $specPath = Join-Path $projectRoot 'packaging\windows_release.spec'
    $pyinstallerArguments = @(
        '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--distpath', $DistPath,
        '--workpath', 'build\release',
        $specPath,
        '--',
        '--version', $Version,
        '--name', 'MetaDescriptionGenerator',
        '--icon', $iconPath
    )
    & $buildEnvironmentPython @pyinstallerArguments
} else {
    & $buildEnvironmentPython @packArguments
}
if ($LASTEXITCODE -ne 0) {
    throw 'Windows release packaging failed.'
}

$executablePath = Join-Path ([IO.Path]::GetFullPath((Join-Path $projectRoot $DistPath))) 'MetaDescriptionGenerator.exe'
$analysisArguments = @(
    'scripts/analyze_package.py',
    $executablePath,
    '--baseline', $BaselineBytes,
    '--maximum', $MaximumBytes
)
foreach ($module in $excludedModules) {
    $analysisArguments += @('--forbid', $module)
}
if ($OptimizationProfile -eq 'Deduplicated') {
    $analysisArguments += @(
        '--maximum-duplicate-bytes', '1000000',
        '--forbid-root-duplicate', 'libmpv-2.dll',
        '--forbid-root-duplicate', 'flutter_windows.dll',
        '--forbid-root-duplicate', 'libGLESv2.dll',
        '--forbid-root-duplicate', 'libEGL.dll',
        '--forbid-root-duplicate', 'rive_common_plugin.dll',
        '--forbid-root-duplicate', 'ucrtbased.dll',
        '--forbid-root-duplicate-suffix', '_plugin.dll',
        '--require-entry', 'flet_desktop\app\flet\flet.exe',
        '--require-entry', 'flet_desktop\app\flet\libmpv-2.dll',
        '--require-entry', 'flet_desktop\app\flet\flutter_windows.dll',
        '--require-entry', 'flet_desktop\app\flet\libGLESv2.dll',
        '--require-entry', 'flet_desktop\app\flet\libEGL.dll',
        '--require-entry', 'flet_desktop\app\flet\rive_common_plugin.dll'
    )
}
& $buildEnvironmentPython @analysisArguments
if ($LASTEXITCODE -ne 0) {
    throw 'Release package validation failed.'
}

$versionInfo = (Get-Item -LiteralPath $executablePath).VersionInfo
if ($versionInfo.ProductVersion -ne $Version) {
    throw "Unexpected ProductVersion: $($versionInfo.ProductVersion)"
}
if ($versionInfo.FileVersion -ne "$Version.0") {
    throw "Unexpected FileVersion: $($versionInfo.FileVersion)"
}

$hash = Get-FileHash -LiteralPath $executablePath -Algorithm SHA256
Write-Host "Optimization profile: $OptimizationProfile"
Write-Host "ProductVersion: $($versionInfo.ProductVersion)"
Write-Host "FileVersion: $($versionInfo.FileVersion)"
Write-Host "SHA256: $($hash.Hash)"
