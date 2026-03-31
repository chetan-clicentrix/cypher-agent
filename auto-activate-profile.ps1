# PowerShell script to activate venv automatically when entering Cypher directory
# Add this to your PowerShell profile

# Auto-activate venv when entering D:\Cipher
function prompt {
    $currentPath = Get-Location
    if ($currentPath.Path -eq "D:\Cipher") {
        if (Test-Path "venv\Scripts\Activate.ps1") {
            if ($env:VIRTUAL_ENV -eq $null) {
                Write-Host "[Cypher] Activating virtual environment..." -ForegroundColor Cyan
                & "venv\Scripts\Activate.ps1"
            }
        }
    }
    
    # Standard prompt
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}
