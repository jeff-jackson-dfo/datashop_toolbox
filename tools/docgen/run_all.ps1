<#
.SYNOPSIS
    Regenerate doc/reference.md from the current source tree.

.DESCRIPTION
    Windows PowerShell equivalent of run_all.sh. Runs extract.py over every
    module in datashop_toolbox, odf_oracle, and datashop_toolbox/gui, then
    runs build_doc.py to assemble the grouped Markdown sections into a
    single reference.md.

.PARAMETER SrcPath
    Path to the repo's src/ folder. Expects the standard layout:
        <SrcPath>\datashop_toolbox\*.py
        <SrcPath>\datashop_toolbox\gui\*.py
        <SrcPath>\odf_oracle\*.py

.EXAMPLE
    .\run_all.ps1 -SrcPath C:\DFO-MPO\DEV\datashop_toolbox\src

.NOTES
    Requires Python 3.9+ on PATH (uses ast.unparse). Writes reference.md
    in the current directory.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$SrcPath
)

$ErrorActionPreference = "Stop"

# Force Python's stdio to UTF-8 regardless of the Windows console code page,
# so non-ASCII characters in any docstring round-trip correctly.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Resolve the folder this script lives in, so extract.py / build_doc.py /
# preamble.md are found regardless of the caller's current directory.
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

# Prefer the Windows "py" launcher if present, otherwise fall back to "python".
$PythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" }
             elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" }
             else { throw "No Python interpreter found on PATH (tried 'py' and 'python')." }

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

$DtSrc     = Join-Path $SrcPath "datashop_toolbox"
$GuiSrc    = Join-Path $DtSrc   "gui"
$OracleSrc = Join-Path $SrcPath "odf_oracle"

foreach ($p in @($DtSrc, $GuiSrc, $OracleSrc)) {
    if (-not (Test-Path $p)) {
        throw "Expected folder not found: $p"
    }
}

$Work = Join-Path ([System.IO.Path]::GetTempPath()) ("docgen_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path (Join-Path $Work "dt")     | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Work "oracle") | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Work "gui")    | Out-Null

try {
    function Invoke-ExtractDir {
        param(
            [string]$SourceDir,
            [string]$OutDir
        )
        Get-ChildItem -Path $SourceDir -Filter "*.py" -File | ForEach-Object {
            $name = $_.BaseName
            # Skip Qt-Designer-generated files; their docstrings are
            # regenerated automatically and aren't hand-maintained.
            if ($name -like "ui_*") { return }
            $outFile = Join-Path $OutDir "$name.json"
            # Capture stdout as an array of lines and rejoin with LF, rather
            # than piping to Out-File, which would add a UTF-8 BOM in
            # Windows PowerShell 5.1 and break json.load() on the far end.
            $jsonLines = & $PythonCmd (Join-Path $Here "extract.py") $_.FullName
            if ($LASTEXITCODE -ne 0) {
                throw "extract.py failed on $($_.FullName)"
            }
            Write-Utf8NoBom -Path $outFile -Content (($jsonLines -join "`n") + "`n")
        }
    }

    Write-Host "Extracting datashop_toolbox ..."
    Invoke-ExtractDir -SourceDir $DtSrc -OutDir (Join-Path $Work "dt")

    Write-Host "Extracting odf_oracle ..."
    Invoke-ExtractDir -SourceDir $OracleSrc -OutDir (Join-Path $Work "oracle")

    Write-Host "Extracting datashop_toolbox.gui ..."
    Invoke-ExtractDir -SourceDir $GuiSrc -OutDir (Join-Path $Work "gui")

    Write-Host "Assembling reference.md ..."
    Copy-Item (Join-Path $Here "preamble.md") (Join-Path $Work "preamble.md")

    Push-Location $Work
    try {
        & $PythonCmd (Join-Path $Here "build_doc.py")
        if ($LASTEXITCODE -ne 0) {
            throw "build_doc.py failed"
        }
    }
    finally {
        Pop-Location
    }

    $parts = @(
        (Join-Path $Work "preamble.md"),
        (Join-Path $Work "section_datashop_toolbox.md"),
        (Join-Path $Work "section_odf_oracle.md"),
        (Join-Path $Work "section_gui.md")
    )

    $combined = ($parts | ForEach-Object { Get-Content -Raw -Encoding utf8 $_ }) -join "`n"
    $combined = [System.Text.RegularExpressions.Regex]::Replace($combined, "(\r?\n){3,}", "`n`n")
    $combined = $combined.TrimEnd() + "`n"

    $outPath = Join-Path (Get-Location) "reference.md"
    Write-Utf8NoBom -Path $outPath -Content $combined

    Write-Host "Done: $outPath"
}
finally {
    Remove-Item -Path $Work -Recurse -Force -ErrorAction SilentlyContinue
}
