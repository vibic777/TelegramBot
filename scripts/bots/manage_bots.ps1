param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('start', 'stop', 'restart', 'kill')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
$projectsRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

function Get-TelegramBotProjects {
    $found = @(Get-ChildItem -LiteralPath $projectsRoot -Directory | Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'start_bot.bat')) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'bot\__main__.py')) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'bot\personas.py'))
    } | Sort-Object Name)

    if ($found.Count -eq 0) {
        throw "Не нашла интегрированные проекты ботов в $projectsRoot (нужны start_bot.bat, bot\__main__.py и bot\personas.py)."
    }

    return $found
}

function Get-RunningBotProcesses {
    param([System.IO.DirectoryInfo[]]$Projects)

    try {
        $allProcesses = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    }
    catch {
        throw "Не удалось безопасно проверить процессы через Windows CIM/WMI: $($_.Exception.Message)"
    }

    $running = @()
    foreach ($project in $Projects) {
        $venvPython = [IO.Path]::GetFullPath((Join-Path $project.FullName '.venv\Scripts\python.exe'))
        $venvPythonw = [IO.Path]::GetFullPath((Join-Path $project.FullName '.venv\Scripts\pythonw.exe'))

        foreach ($process in $allProcesses) {
            if ($process.Name -notin @('python.exe', 'pythonw.exe')) { continue }
            if ([string]::IsNullOrWhiteSpace($process.ExecutablePath) -or
                [string]::IsNullOrWhiteSpace($process.CommandLine)) { continue }

            $exe = [IO.Path]::GetFullPath($process.ExecutablePath)
            $isProjectInterpreter = $exe.Equals($venvPython, [StringComparison]::OrdinalIgnoreCase) -or
                $exe.Equals($venvPythonw, [StringComparison]::OrdinalIgnoreCase)
            $runsBotModule = $process.CommandLine -match '(?i)(?:^|\s)-m\s+bot(?:\s|$)'

            if ($isProjectInterpreter -and $runsBotModule) {
                $running += [PSCustomObject]@{
                    Project = $project
                    Process = $process
                }
            }
        }
    }

    return $running
}

function Stop-TelegramBots {
    param(
        [System.IO.DirectoryInfo[]]$Projects,
        [switch]$Force
    )

    $running = @(Get-RunningBotProcesses -Projects $Projects)
    if ($running.Count -eq 0) {
        Write-Host 'Запущенных процессов Telegram-ботов не найдено.'
        return
    }

    foreach ($entry in $running) {
        $id = [int]$entry.Process.ProcessId
        $name = $entry.Project.Name
        try {
            if (-not $Force) {
                $localProcess = Get-Process -Id $id -ErrorAction SilentlyContinue
                if ($localProcess -and $localProcess.MainWindowHandle -ne 0) {
                    [void]$localProcess.CloseMainWindow()
                    [void]$localProcess.WaitForExit(5000)
                }
            }

            $stillRunning = Get-Process -Id $id -ErrorAction SilentlyContinue
            if ($stillRunning) {
                Stop-Process -Id $id -Force -ErrorAction Stop
                Write-Host "Остановлен процесс $id ($name)."
            }
            else {
                Write-Host "Процесс $id ($name) завершился штатно."
            }
        }
        catch {
            Write-Warning "Не удалось остановить процесс $id ($name): $($_.Exception.Message)"
        }
    }

    $remaining = @(Get-RunningBotProcesses -Projects $Projects)
    if ($remaining.Count -gt 0) {
        $details = $remaining | ForEach-Object { "$($_.Project.Name):$($_.Process.ProcessId)" }
        throw ("Остались процессы ботов: " + ($details -join ', '))
    }
}

function Start-TelegramBots {
    param([System.IO.DirectoryInfo[]]$Projects)

    $running = @(Get-RunningBotProcesses -Projects $Projects)
    $runningPaths = @($running | ForEach-Object { $_.Project.FullName })
    $started = 0
    $skipped = 0
    $failed = 0

    foreach ($project in $Projects) {
        if ($runningPaths -contains $project.FullName) {
            Write-Host "Уже запущен: $($project.Name)."
            $skipped++
            continue
        }

        $envFile = Join-Path $project.FullName '.env'
        if (-not (Test-Path -LiteralPath $envFile)) {
            Write-Warning "Пропускаю $($project.Name): нет .env. Скопируйте .env.example в .env и заполните настройки."
            $skipped++
            continue
        }

        $tokenLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^\s*BOT_TOKEN\s*=' } | Select-Object -First 1
        $botToken = if ($tokenLine -match '^\s*BOT_TOKEN\s*=\s*(.*?)\s*$') { $matches[1].Trim().Trim('"').Trim("'") } else { '' }
        if ([string]::IsNullOrWhiteSpace($botToken)) {
            Write-Warning "Пропускаю $($project.Name): заполните BOT_TOKEN в .env. Токены у каждого Telegram-бота должны быть свои."
            $skipped++
            continue
        }

        $startFile = Join-Path $project.FullName 'start_bot.bat'
        try {
            $arguments = '/c start "" "' + $startFile + '"'
            Start-Process -FilePath $env:ComSpec -ArgumentList $arguments -WorkingDirectory $project.FullName
            Write-Host "Запускаю $($project.Name) в отдельном окне."
            $started++
        }
        catch {
            Write-Warning "Не удалось запустить $($project.Name): $($_.Exception.Message)"
            $failed++
        }
    }

    Write-Host "Итог: новых запусков — $started; пропущено — $skipped; ошибок — $failed."
    if ($failed -gt 0 -or ($started -eq 0 -and $running.Count -eq 0)) { exit 1 }
}

try {
    $projects = @(Get-TelegramBotProjects)
    Write-Host ("Проекты: " + (($projects | ForEach-Object Name) -join ', '))

    switch ($Action) {
        'start' { Start-TelegramBots -Projects $projects }
        'stop' { Stop-TelegramBots -Projects $projects }
        'kill' {
            Write-Host 'Принудительно завершаю только процессы python -m bot из виртуальных окружений найденных проектов.'
            Stop-TelegramBots -Projects $projects -Force
        }
        'restart' {
            Stop-TelegramBots -Projects $projects
            Start-Sleep -Seconds 2
            Start-TelegramBots -Projects $projects
        }
    }
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
