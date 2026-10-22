# Install uv and windows-mcp when they are missing, then print the executable path.
$ErrorActionPreference = 'Stop'

$localBin = Join-Path $env:USERPROFILE '.local\bin'
$localUv = Join-Path $localBin 'uv.exe'
$preferredMcp = Join-Path $localBin 'windows-mcp.exe'

function Find-Uv {
  $command = Get-Command uv -ErrorAction SilentlyContinue
  if ($null -ne $command) { return $command.Source }
  if (Test-Path -LiteralPath $localUv) { return $localUv }
  return $null
}

function Find-WindowsMcp {
  if (Test-Path -LiteralPath $preferredMcp) { return $preferredMcp }
  $found = @(where.exe windows-mcp 2>$null | ForEach-Object { $_.Trim() } | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
  if ($found.Count -gt 0) { return $found[0] }
  return $null
}

$uv = Find-Uv
if ($null -eq $uv) {
  Write-Host '安装 uv'
  irm https://astral.sh/uv/install.ps1 | iex
  $env:PATH = "$localBin;$env:PATH"
  $uv = Find-Uv
  if ($null -eq $uv) { throw 'uv 安装后仍未找到 uv.exe' }
} else {
  Write-Host "uv 已安装: $uv"
}

$mcp = Find-WindowsMcp
if ($null -eq $mcp) {
  Write-Host '安装 windows-mcp'
  & $uv tool install windows-mcp
  if ($LASTEXITCODE -ne 0) { throw "uv tool install windows-mcp 退出码 $LASTEXITCODE" }
  $mcp = Find-WindowsMcp
  if ($null -eq $mcp) { throw 'windows-mcp 安装后仍未找到 windows-mcp.exe' }
} else {
  Write-Host "windows-mcp 已安装: $mcp"
}

Write-Output $mcp
