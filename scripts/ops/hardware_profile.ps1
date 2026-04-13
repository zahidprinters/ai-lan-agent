param(
    [string]$OutputJson = "temp/hardware/hardware_profile.json"
)

$ErrorActionPreference = "SilentlyContinue"

$cpu = Get-CimInstance Win32_Processor |
    Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, L2CacheSize, L3CacheSize

$computerSystem = Get-CimInstance Win32_ComputerSystem |
    Select-Object Manufacturer, Model, TotalPhysicalMemory, SystemType

$os = Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, BuildNumber, OSArchitecture, CSName, LastBootUpTime

$gpu = Get-CimInstance Win32_VideoController |
    Select-Object Name, AdapterRAM, DriverVersion, VideoProcessor, Status

$memory = Get-CimInstance Win32_PhysicalMemory |
    Select-Object BankLabel, Capacity, Speed, ConfiguredClockSpeed, Manufacturer, PartNumber

$baseBoard = Get-CimInstance Win32_BaseBoard |
    Select-Object Manufacturer, Product, Version, SerialNumber

$bios = Get-CimInstance Win32_BIOS |
    Select-Object Manufacturer, SMBIOSBIOSVersion, ReleaseDate

$disks = Get-CimInstance Win32_DiskDrive |
    Select-Object Model, Size, MediaType, InterfaceType

$chipset = Get-PnpDevice -Class System |
    Where-Object { $_.FriendlyName -match 'chipset|host bridge|SMBus|LPC Controller|PCI Express Root' } |
    Select-Object FriendlyName, Manufacturer, Status

$profile = [pscustomobject]@{
    CollectedAt = (Get-Date).ToString("s")
    ComputerSystem = $computerSystem
    CPU = $cpu
    OperatingSystem = $os
    GPU = $gpu
    MemoryModules = $memory
    BaseBoard = $baseBoard
    BIOS = $bios
    Disks = $disks
    ChipsetLikeDevices = $chipset
}

$resolvedOutput = Resolve-Path . | ForEach-Object { Join-Path $_.Path $OutputJson }
$outDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$profile | ConvertTo-Json -Depth 6 | Set-Content -Path $resolvedOutput -Encoding UTF8

Write-Host "Hardware profile written: $resolvedOutput"
