
param(
    [ValidateSet('dashboard', 'setup', 'check', 'phase4_check', 'train', 'trainbigram', 'generate', 'generatebigram', 'compare', 'runs', 'reindex', 'test', 'datareport', 'clean', 'clean_dataset', 'chat', 'chat_web', 'models', 'memory', 'context', 'logs', 'ops')]
    [string]$Action = 'dashboard',
    [ValidateSet('all', 'unit', 'integration')]
    [string]$Suite = 'all',
    [switch]$AllRuns
)


$root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$logRoot = Join-Path $tempRoot 'logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$script:DashboardState = 'Idle'
$script:LastActionLabel = 'None'
$script:LastResultLabel = 'Ready'
$script:LastResultColor = 'Green'
$script:LastLogPath = ''
$script:CurrentDashboardSection = 'Overview'
$script:DashboardWebHost = '127.0.0.1'
$script:DashboardWebPort = 8765
$script:DashboardWebPath = '/overview'

function Get-StatusLabel {
    param([bool]$Ready)

    if ($Ready) { return 'Ready' }
    return 'Missing'
}

function Write-StatusLine {
    param(
        [string]$Label,
        [bool]$Ready
    )

    $status = Get-StatusLabel -Ready $Ready
    $color = if ($Ready) { 'Green' } else { 'Yellow' }
    Write-Host ("  {0,-22} " -f $Label) -NoNewline
    Write-Host $status -ForegroundColor $color
}

function Write-TwoColumnLine {
    param(
        [string]$LeftLabel,
        [string]$LeftValue,
        [string]$RightLabel = '',
        [string]$RightValue = ''
    )

    $leftText = "  {0,-10} {1,-24}" -f ($LeftLabel + ' :'), $LeftValue
    if ($RightLabel) {
        $rightText = "{0,-10} {1}" -f ($RightLabel + ' :'), $RightValue
        Write-Host ($leftText + $rightText)
        return
    }
    Write-Host $leftText
}

function Write-TwoColumnStatus {
    param(
        [string]$LeftLabel,
        [bool]$LeftReady,
        [string]$RightLabel,
        [bool]$RightReady
    )

    $leftStatus = Get-StatusLabel -Ready $LeftReady
    $rightStatus = Get-StatusLabel -Ready $RightReady
    $leftColor = if ($LeftReady) { 'Green' } else { 'Yellow' }
    $rightColor = if ($RightReady) { 'Green' } else { 'Yellow' }

    Write-Host ("  {0,-22} " -f $LeftLabel) -NoNewline
    Write-Host ("{0,-10}" -f $leftStatus) -NoNewline -ForegroundColor $leftColor
    Write-Host ("  {0,-22} " -f $RightLabel) -NoNewline
    Write-Host $rightStatus -ForegroundColor $rightColor
}

function Write-SectionTitle {
    param([string]$Title)

    Write-Host ''
    Write-Host $Title -ForegroundColor Yellow
}

function Write-FrameLine {
    param(
        [string]$Text = '',
        [int]$Width = 68
    )

    $trimmed = if ($Text.Length -gt $Width) { $Text.Substring(0, $Width) } else { $Text }
    Write-Host ('| ' + $trimmed.PadRight($Width) + ' |') -ForegroundColor DarkGray
}

function Write-MenuRow {
    param(
        [string]$LeftText,
        [string]$RightText = ''
    )

    $combined = "{0,-33}{1,-33}" -f $LeftText, $RightText
    Write-FrameLine -Text $combined
}

function Write-MenuGroup {
    param([string]$Title)

    Write-FrameLine -Text ''
    Write-FrameLine -Text ("[{0}]" -f $Title)
}

function Write-MenuEntry {
    param(
        [string]$Number,
        [string]$Label
    )

    return ("{0,-2} {1}" -f ($Number + '.'), $Label)
}

function Get-ActionSection {
    param([string]$SelectedAction)

    switch ($SelectedAction) {
        'setup' { return 'Workspace' }
        'check' { return 'Workspace' }
        'phase4_check' { return 'Workspace' }
        'chat' { return 'Workspace' }
        'chat_web' { return 'Workspace' }
        'train' { return 'Training' }
        'trainbigram' { return 'Training' }
        'generate' { return 'Training' }
        'generatebigram' { return 'Training' }
        'compare' { return 'Training' }
        'runs' { return 'Training' }
        'reindex' { return 'Training' }
        'datareport' { return 'Training' }
        'clean_dataset' { return 'Training' }
        'models' { return 'Knowledge' }
        'memory' { return 'Knowledge' }
        'context' { return 'Knowledge' }
        'logs' { return 'System' }
        'ops' { return 'System' }
        'evaluate' { return 'System' }
        'quantize' { return 'System' }
        'export_onnx' { return 'System' }
        'export_weights' { return 'System' }
        'infer_simple' { return 'System' }
        'test' { return 'Quality' }
        'clean' { return 'Quality' }
        default { return 'Overview' }
    }
}

function Get-ProjectPython {
    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        return 'python'
    }
    return $venvPython
}

function Test-TcpPortOpen {
    param(
        [string]$Host,
        [int]$Port,
        [int]$TimeoutMs = 150
    )

    $client = $null
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $async = $client.BeginConnect($Host, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs)) {
            return $false
        }
        $client.EndConnect($async) | Out-Null
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($client) {
            $client.Close()
        }
    }
}

function Get-WebDashboardStatus {
    $url = "http://{0}:{1}{2}" -f $script:DashboardWebHost, $script:DashboardWebPort, $script:DashboardWebPath
    $running = Test-TcpPortOpen -Host $script:DashboardWebHost -Port $script:DashboardWebPort
    if ($running) {
        return [pscustomobject]@{
            Label = 'Running'
            Color = 'Green'
            Url = $url
        }
    }

    return [pscustomobject]@{
        Label = 'Offline'
        Color = 'DarkGray'
        Url = $url
    }
}

function Set-DashboardStatus {
    param(
        [string]$State,
        [string]$LastAction,
        [string]$LastResult,
        [string]$Color = 'Green',
        [string]$LogPath = '',
        [string]$Section = 'Overview'
    )

    $script:DashboardState = $State
    $script:LastActionLabel = $LastAction
    $script:LastResultLabel = $LastResult
    $script:LastResultColor = $Color
    $script:CurrentDashboardSection = $Section
    if ($LogPath -ne '') {
        $script:LastLogPath = $LogPath
    }
}

function Show-StatusBar {
    $webStatus = Get-WebDashboardStatus

    Write-Host ''
    Write-Host ('=' * 72) -ForegroundColor DarkCyan
    Write-Host 'Status ' -NoNewline -ForegroundColor Yellow
    Write-Host ("{0,-10}" -f $script:DashboardState) -NoNewline -ForegroundColor Cyan
    Write-Host '  Section ' -NoNewline -ForegroundColor Yellow
    Write-Host ("{0,-14}" -f $script:CurrentDashboardSection) -NoNewline -ForegroundColor White
    Write-Host '  Last Action ' -NoNewline -ForegroundColor Yellow
    Write-Host ("{0,-18}" -f $script:LastActionLabel) -NoNewline -ForegroundColor White
    Write-Host '  Result ' -NoNewline -ForegroundColor Yellow
    Write-Host $script:LastResultLabel -ForegroundColor $script:LastResultColor
    Write-Host ''
    Write-Host 'Web ' -NoNewline -ForegroundColor Yellow
    Write-Host ("{0,-10}" -f $webStatus.Label) -NoNewline -ForegroundColor $webStatus.Color
    Write-Host '  URL ' -NoNewline -ForegroundColor Yellow
    Write-Host $webStatus.Url -ForegroundColor DarkGray
    if ($script:LastLogPath) {
        Write-Host ("Log " ) -NoNewline -ForegroundColor Yellow
        Write-Host $script:LastLogPath -ForegroundColor DarkGray
    }
}

function Show-Dashboard {
    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    $dataset = Join-Path $root 'data\input.txt'
    $bestModel = Join-Path $root 'models\char_model_best.pt'
    $runIndex = Join-Path $root 'runs\index.json'
    $allRunIndex = Join-Path $root 'runs\all_index.json'

    Write-Host ('=' * 72) -ForegroundColor Cyan
    Write-Host 'AI LAN' -ForegroundColor Cyan
    Write-Host 'Windows-first CPU AI workspace' -ForegroundColor DarkCyan
    Write-Host ('=' * 72) -ForegroundColor Cyan

    Write-Host ''
    Write-TwoColumnLine -LeftLabel 'Phase' -LeftValue 'Phase 2.0 - Transformer' -RightLabel 'Entry' -RightValue 'main.ps1'
    Write-TwoColumnLine -LeftLabel 'Stage' -LeftValue 'foundation and maturity' -RightLabel 'Temp' -RightValue $tempRoot

    Write-SectionTitle 'Workspace'
    Write-TwoColumnStatus -LeftLabel 'Python environment' -LeftReady (Test-Path $venvPython) -RightLabel 'Dataset' -RightReady (Test-Path $dataset)
    Write-TwoColumnStatus -LeftLabel 'Best model' -LeftReady (Test-Path $bestModel) -RightLabel 'Project runs' -RightReady (Test-Path $runIndex)
    Write-TwoColumnStatus -LeftLabel 'All runs' -LeftReady (Test-Path $allRunIndex) -RightLabel 'Temp folder' -RightReady (Test-Path $tempRoot)

    Write-SectionTitle 'System Capability'
    Write-TwoColumnLine -LeftLabel 'Web Search' -LeftValue 'No (Stage 1 pending)' -RightLabel 'PC Control' -RightValue 'No (Stage 3 pending)'
    Write-TwoColumnLine -LeftLabel 'Current Brain' -LeftValue 'StackedTransformer-v2' -RightLabel 'Exp Profile' -RightValue (if ($env:AI_LAN_EXP_PROFILE) { $env:AI_LAN_EXP_PROFILE } else { 'default' })

    Write-SectionTitle 'Debug & Observability'
    Write-TwoColumnLine -LeftLabel 'Basic Debug' -LeftValue (if ($env:AI_LAN_DEBUG -eq '1') { 'ON' } else { 'OFF' }) -RightLabel 'Trace Mode' -RightValue (if ($env:AI_LAN_TRACE -eq '1') { 'ON' } else { 'OFF' })
    Write-TwoColumnLine -LeftLabel 'Profiling' -LeftValue (if ($env:AI_LAN_PROFILE -eq '1') { 'ON' } else { 'OFF' }) -RightLabel 'Trace STDOUT' -RightValue (if ($env:AI_LAN_TRACE_STDOUT -eq '1') { 'ON' } else { 'OFF' })
    Show-StatusBar
}

function Show-Menu {
    Write-SectionTitle 'Actions'
    Write-Host ('+' + ('-' * 70) + '+') -ForegroundColor DarkGray
    Write-MenuGroup -Title 'Workspace'
    Write-MenuRow -LeftText (Write-MenuEntry -Number '1' -Label 'Setup environment') -RightText (Write-MenuEntry -Number '3' -Label 'CLI chat interface')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '2' -Label 'Health check') -RightText (Write-MenuEntry -Number '4' -Label 'Web chat interface')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '30' -Label 'Phase 4 tool check')
    Write-MenuGroup -Title 'Training'
    Write-MenuRow -LeftText (Write-MenuEntry -Number '5' -Label 'Train model') -RightText (Write-MenuEntry -Number '7' -Label 'Show project runs')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '6' -Label 'Compare checkpoints') -RightText (Write-MenuEntry -Number '8' -Label 'Show all runs')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '9' -Label 'Rebuild run indexes') -RightText (Write-MenuEntry -Number '10' -Label 'Train bigram baseline')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '11' -Label 'Generate text') -RightText (Write-MenuEntry -Number '12' -Label 'Generate with bigram')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '13' -Label 'Dataset report') -RightText (Write-MenuEntry -Number '14' -Label 'Clean and deduplicate dataset')
    Write-MenuGroup -Title 'Knowledge'
    Write-MenuRow -LeftText (Write-MenuEntry -Number '15' -Label 'Model registry') -RightText (Write-MenuEntry -Number '16' -Label 'Memory view')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '17' -Label 'Context view')
    Write-MenuGroup -Title 'System'
    Write-MenuRow -LeftText (Write-MenuEntry -Number '18' -Label 'Logs view') -RightText (Write-MenuEntry -Number '19' -Label 'System control')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '20' -Label 'Evaluate model metrics') -RightText (Write-MenuEntry -Number '21' -Label 'Quantize (.pt) model')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '22' -Label 'Export to ONNX') -RightText (Write-MenuEntry -Number '23' -Label 'Export clean weights')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '24' -Label 'Standalone inference')
    Write-MenuGroup -Title 'Quality'
    Write-MenuRow -LeftText (Write-MenuEntry -Number '25' -Label 'Run unit tests') -RightText (Write-MenuEntry -Number '26' -Label 'Run integration tests')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '27' -Label 'Run all tests') -RightText (Write-MenuEntry -Number '28' -Label 'Refresh dashboard')
    Write-MenuRow -LeftText (Write-MenuEntry -Number '29' -Label 'Clean cache and temp data')

    Write-MenuGroup -Title 'System Config'
    Write-MenuRow -LeftText (Write-MenuEntry -Number 'D' -Label 'Toggle Basic Debug') -RightText (Write-MenuEntry -Number 'T' -Label 'Toggle Trace Mode')
    Write-MenuRow -LeftText (Write-MenuEntry -Number 'P' -Label 'Toggle Profiling') -RightText (Write-MenuEntry -Number 'S' -Label 'Toggle Trace STDOUT')
    Write-FrameLine -Text ''
    Write-Host ('+' + ('-' * 70) + '+') -ForegroundColor DarkGray

    Write-SectionTitle 'Footer'
    Write-Host '  Enter an action number to run it.'
    Write-Host '  Press Q to close the dashboard.'
    Write-Host ''
}

function Invoke-ProjectScript {
    param(
        [string]$ScriptPath,
        [string[]]$ScriptArgs = @(),
        [string]$LogPath = ''
    )

    $extension = [System.IO.Path]::GetExtension($ScriptPath).ToLowerInvariant()
    if ($extension -eq '.py') {
        $python = Get-ProjectPython
        if ($LogPath) {
            & $python $ScriptPath @ScriptArgs *> $LogPath
            return $LASTEXITCODE
        }

        & $python $ScriptPath @ScriptArgs
        return $LASTEXITCODE
    }

    if ($LogPath) {
        & powershell -ExecutionPolicy Bypass -File $ScriptPath @ScriptArgs *> $LogPath
        return $LASTEXITCODE
    }

    & powershell -ExecutionPolicy Bypass -File $ScriptPath @ScriptArgs
    return $LASTEXITCODE
}

function Get-ActionDisplayName {
    param(
        [string]$SelectedAction,
        [string]$SelectedSuite = 'all',
        [bool]$SelectedAllRuns = $false
    )

    switch ($SelectedAction) {
        'setup' { return 'Setup environment' }
        'check' { return 'Health check' }
        'phase4_check' { return 'Phase 4 tool check' }
        'train' { return 'Train model' }
        'trainbigram' { return 'Train bigram baseline' }
        'generate' { return 'Generate text' }
        'generatebigram' { return 'Generate with bigram' }
        'compare' { return 'Compare checkpoints' }
        'datareport' { return 'Dataset report' }
        'runs' {
            if ($SelectedAllRuns) { return 'Show all runs' }
            return 'Show project runs'
        }
        'reindex' { return 'Rebuild run indexes' }
        'clean' { return 'Clean cache and temp data' }
        'clean_dataset' { return 'Clean and deduplicate dataset' }
        'models' { return 'Model registry' }
        'memory' { return 'Memory view' }
        'context' { return 'Context view' }
        'logs' { return 'Logs view' }
        'ops' { return 'System control' }
        'export_onnx' { return 'Export to ONNX' }
        'quantize' { return 'Quantize (.pt) model' }
        'export_weights' { return 'Export clean weights' }
        'evaluate' { return 'Evaluate model metrics' }
        'infer_simple' { return 'Standalone inference' }
        'chat' { return 'CLI chat interface' }
        'chat_web' { return 'Web chat interface' }
        'test' {
            switch ($SelectedSuite) {
                'unit' { return 'Run unit tests' }
                'integration' { return 'Run integration tests' }
                default { return 'Run all tests' }
            }
        }
        default { return $SelectedAction }
    }
}

function Invoke-Action {
    param(
        [string]$SelectedAction,
        [string]$SelectedSuite = 'all',
        [bool]$SelectedAllRuns = $false,
        [string]$LogPath = '',
        [string]$Query = ''
    )

    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        $venvPython = 'python'
    }

    $dashboardViews = Join-Path $root 'scripts\dashboard_views.py'

    switch ($SelectedAction) {
        'setup' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\setup.ps1') -LogPath $LogPath) }
        'check' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\check.ps1') -LogPath $LogPath) }
        'phase4_check' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\validate_installation.py') -ScriptArgs @('--phase4') -LogPath $LogPath) }
        'train' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\train.ps1') -LogPath $LogPath) }
        'trainbigram' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\train_bigram.ps1') -LogPath $LogPath) }
        'generate' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\generate.ps1') -LogPath $LogPath) }
        'generatebigram' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\generate_bigram.ps1') -LogPath $LogPath) }
        'compare' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\compare.ps1') -LogPath $LogPath) }
        'datareport' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\data_report.ps1') -LogPath $LogPath) }
        'runs' {
            $runArgs = @()
            if ($SelectedAllRuns) { $runArgs += '-AllRuns' }
            return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\runs.ps1') -ScriptArgs $runArgs -LogPath $LogPath)
        }
        'reindex' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\reindex_runs.ps1') -LogPath $LogPath) }
        'clean' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\clean.ps1') -LogPath $LogPath) }
        'clean_dataset' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\clean_dataset.ps1') -LogPath $LogPath) }
        'export_onnx' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\export_onnx.ps1') -LogPath $LogPath) }
        'quantize' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\quantize.ps1') -LogPath $LogPath) }
        'export_weights' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\export_weights.ps1') -LogPath $LogPath) }
        'evaluate' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\evaluate.ps1') -LogPath $LogPath) }
        'infer_simple' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\infer_simple.ps1') -LogPath $LogPath) }
        'chat' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\launch.py') -ScriptArgs @('--mode', 'cli') -LogPath $LogPath) }
        'chat_web' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\launch.py') -ScriptArgs @('--mode', 'web') -LogPath $LogPath) }
        'models' { return (Invoke-ProjectScript -ScriptPath $dashboardViews -ScriptArgs @('models') -LogPath $LogPath) }
        'memory' {
            $memoryArgs = @('memory')
            if ($Query.Trim()) {
                $memoryArgs += @('--query', $Query.Trim())
            }
            return (Invoke-ProjectScript -ScriptPath $dashboardViews -ScriptArgs $memoryArgs -LogPath $LogPath)
        }
        'context' {
            $contextQuery = if ($Query.Trim()) { $Query.Trim() } else { 'system status' }
            return (Invoke-ProjectScript -ScriptPath $dashboardViews -ScriptArgs @('context', '--query', $contextQuery) -LogPath $LogPath)
        }
        'logs' { return (Invoke-ProjectScript -ScriptPath $dashboardViews -ScriptArgs @('logs') -LogPath $LogPath) }
        'ops' { return (Invoke-ProjectScript -ScriptPath $dashboardViews -ScriptArgs @('ops') -LogPath $LogPath) }
        'test' { return (Invoke-ProjectScript -ScriptPath (Join-Path $root 'scripts\test.ps1') -ScriptArgs @($SelectedSuite) -LogPath $LogPath) }
        default { throw "Unsupported action: $SelectedAction" }
    }
}

function Show-WorkArea {
    param(
        [string]$Title,
        [string]$LogPath,
        [int]$TailCount = 12
    )

    Write-SectionTitle 'Work Area'
    Write-Host ('+' + ('-' * 70) + '+') -ForegroundColor DarkGray
    Write-FrameLine -Text ("Action: {0}" -f $Title)
    Write-FrameLine -Text ("Log:    {0}" -f $LogPath)
    Write-Host ('+' + ('-' * 70) + '+') -ForegroundColor DarkGray

    if (Test-Path $LogPath) {
        $lines = Get-Content $LogPath -Tail $TailCount
        foreach ($line in $lines) {
            Write-FrameLine -Text $line
        }
    }
    else {
        Write-FrameLine -Text 'No log output captured.'
    }

    Write-Host ('+' + ('-' * 70) + '+') -ForegroundColor DarkGray
}

function Invoke-ManagedAction {
    param(
        [string]$SelectedAction,
        [string]$SelectedSuite = 'all',
        [bool]$SelectedAllRuns = $false
    )

    $label = Get-ActionDisplayName -SelectedAction $SelectedAction -SelectedSuite $SelectedSuite -SelectedAllRuns $SelectedAllRuns
    $section = Get-ActionSection -SelectedAction $SelectedAction
    $query = ''
    if ($SelectedAction -eq 'memory') {
        $query = (Read-Host 'Memory query (blank for recent)').Trim()
    }
    elseif ($SelectedAction -eq 'context') {
        $query = (Read-Host 'Context query (blank for system status)').Trim()
    }
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $safeLabel = ($label -replace '[^A-Za-z0-9]+', '_').Trim('_').ToLower()
    $logPath = Join-Path $logRoot ("{0}_{1}.log" -f $timestamp, $safeLabel)
    $tailCount = switch ($SelectedAction) {
        'models' { 24 }
        'memory' { 40 }
        'context' { 48 }
        'logs' { 32 }
        'ops' { 28 }
        default { 12 }
    }
    Set-DashboardStatus -State 'Running' -LastAction $label -LastResult 'In progress' -Color 'Yellow' -LogPath $logPath -Section $section
    Clear-Host
    Show-Dashboard
    Write-Host ''
    Show-WorkArea -Title $label -LogPath $logPath -TailCount $tailCount

    $code = Invoke-Action -SelectedAction $SelectedAction -SelectedSuite $SelectedSuite -SelectedAllRuns $SelectedAllRuns -LogPath $logPath -Query $query

    if ($code -eq 0) {
        Set-DashboardStatus -State 'Idle' -LastAction $label -LastResult 'Success' -Color 'Green' -LogPath $logPath -Section $section
    }
    else {
        Set-DashboardStatus -State 'Idle' -LastAction $label -LastResult ("Exit {0}" -f $code) -Color 'Yellow' -LogPath $logPath -Section $section
    }

    Clear-Host
    Show-Dashboard
    Show-WorkArea -Title $label -LogPath $logPath -TailCount $tailCount
    return $code
}

function Start-InteractiveDashboard {
    while ($true) {
        Clear-Host
        Show-Dashboard
        Show-Menu
        $choice = Read-Host 'Choice'

        switch ($choice.Trim().ToLower()) {
            '1' { $code = Invoke-ManagedAction -SelectedAction 'setup' }
            '2' { $code = Invoke-ManagedAction -SelectedAction 'check' }
            '3' { $code = Invoke-ManagedAction -SelectedAction 'chat' }
            '4' { $code = Invoke-ManagedAction -SelectedAction 'chat_web' }
            '5' { $code = Invoke-ManagedAction -SelectedAction 'train' }
            '6' { $code = Invoke-ManagedAction -SelectedAction 'compare' }
            '7' { $code = Invoke-ManagedAction -SelectedAction 'runs' }
            '8' { $code = Invoke-ManagedAction -SelectedAction 'runs' -SelectedAllRuns $true }
            '9' { $code = Invoke-ManagedAction -SelectedAction 'reindex' }
            '10' { $code = Invoke-ManagedAction -SelectedAction 'trainbigram' }
            '11' { $code = Invoke-ManagedAction -SelectedAction 'generate' }
            '12' { $code = Invoke-ManagedAction -SelectedAction 'generatebigram' }
            '13' { $code = Invoke-ManagedAction -SelectedAction 'datareport' }
            '14' { $code = Invoke-ManagedAction -SelectedAction 'clean_dataset' }
            '15' { $code = Invoke-ManagedAction -SelectedAction 'models' }
            '16' { $code = Invoke-ManagedAction -SelectedAction 'memory' }
            '17' { $code = Invoke-ManagedAction -SelectedAction 'context' }
            '18' { $code = Invoke-ManagedAction -SelectedAction 'logs' }
            '19' { $code = Invoke-ManagedAction -SelectedAction 'ops' }
            '20' { $code = Invoke-ManagedAction -SelectedAction 'evaluate' }
            '21' { $code = Invoke-ManagedAction -SelectedAction 'quantize' }
            '22' { $code = Invoke-ManagedAction -SelectedAction 'export_onnx' }
            '23' { $code = Invoke-ManagedAction -SelectedAction 'export_weights' }
            '24' { $code = Invoke-ManagedAction -SelectedAction 'infer_simple' }
            '25' { $code = Invoke-ManagedAction -SelectedAction 'test' -SelectedSuite 'unit' }
            '26' { $code = Invoke-ManagedAction -SelectedAction 'test' -SelectedSuite 'integration' }
            '27' { $code = Invoke-ManagedAction -SelectedAction 'test' -SelectedSuite 'all' }
            '28' { continue }
            '29' { $code = Invoke-ManagedAction -SelectedAction 'clean' }
            '30' { $code = Invoke-ManagedAction -SelectedAction 'phase4_check' }
            'd' { $env:AI_LAN_DEBUG = if ($env:AI_LAN_DEBUG -eq '1') { '0' } else { '1' }; continue }
            't' { $env:AI_LAN_TRACE = if ($env:AI_LAN_TRACE -eq '1') { '0' } else { '1' }; continue }
            'p' { $env:AI_LAN_PROFILE = if ($env:AI_LAN_PROFILE -eq '1') { '0' } else { '1' }; continue }
            's' { $env:AI_LAN_TRACE_STDOUT = if ($env:AI_LAN_TRACE_STDOUT -eq '1') { '0' } else { '1' }; continue }
            'q' {
                Clear-Host
                Write-Host 'AI Lan closed.' -ForegroundColor Green
                exit 0
            }
            default {
                Write-Host ''
                Write-Host '[WARN] Invalid selection. Please choose a valid menu option.' -ForegroundColor Yellow
                Start-Sleep -Seconds 2
                continue
            }
        }

        Write-Host ''
        if ($code -eq 0) {
            Write-Host '[INFO] Action completed. Press Enter to return to the dashboard.' -ForegroundColor Green
        }
        else {
            Write-Host "[WARN] Action finished with exit code $code. Press Enter to return to the dashboard." -ForegroundColor Yellow
        }
        [void](Read-Host)
    }
}

switch ($Action) {
    'dashboard' { Start-InteractiveDashboard; exit 0 }
    'setup' { exit (Invoke-Action -SelectedAction 'setup') }
    'check' { exit (Invoke-Action -SelectedAction 'check') }
    'train' { exit (Invoke-Action -SelectedAction 'train') }
    'trainbigram' { exit (Invoke-Action -SelectedAction 'trainbigram') }
    'generate' { exit (Invoke-Action -SelectedAction 'generate') }
    'generatebigram' { exit (Invoke-Action -SelectedAction 'generatebigram') }
    'compare' { exit (Invoke-Action -SelectedAction 'compare') }
    'datareport' { exit (Invoke-Action -SelectedAction 'datareport') }
    'runs' { exit (Invoke-Action -SelectedAction 'runs' -SelectedAllRuns $AllRuns) }
    'reindex' { exit (Invoke-Action -SelectedAction 'reindex') }
    'clean' { exit (Invoke-Action -SelectedAction 'clean') }
    'chat' { exit (Invoke-Action -SelectedAction 'chat') }
    'chat_web' { exit (Invoke-Action -SelectedAction 'chat_web') }
    'models' { exit (Invoke-Action -SelectedAction 'models') }
    'memory' { exit (Invoke-Action -SelectedAction 'memory') }
    'context' { exit (Invoke-Action -SelectedAction 'context') }
    'logs' { exit (Invoke-Action -SelectedAction 'logs') }
    'ops' { exit (Invoke-Action -SelectedAction 'ops') }
    'test' { exit (Invoke-Action -SelectedAction 'test' -SelectedSuite $Suite) }
}
