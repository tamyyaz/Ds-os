<#
.SYNOPSIS
  Creates (or removes) a Hyper-V virtual machine for trying Darksham OS on Windows.

.DESCRIPTION
  Darksham OS is a bootc image on ghcr.io, so the easy way to try it is:
    1. install stock Bazzite (KDE, the AMD/Intel ISO) in the VM from an ISO you download,
    2. inside the VM run:  sudo bootc switch ghcr.io/tamyyaz/ds-os:latest   (needs the package to be Public)
    3. reboot and run tools/vm/vm-check.sh to see what works.
  This script does the VM part: checks the PC, creates a Generation 2 VM that Linux can boot
  (Secure Boot with the Microsoft UEFI CA template), attaches the ISO and opens the VM window.
  It never downloads anything and never touches existing VMs.

  Needs Windows Pro/Enterprise with Hyper-V and an administrator prompt (it asks Windows to elevate).
  Limits: Hyper-V gives Linux no 3D graphics, so the desktop runs with software rendering.
  Good for: boot, theme, splash, login, the Darksham Launcher in a window. NOT good for: gamescope
  / Gaming Mode, GPU drivers, game performance. Test those on a real PC.

.EXAMPLE
  .\New-DarkshamVM.ps1 -IsoPath D:\ISOs\bazzite-stable-amd64.iso
  .\New-DarkshamVM.ps1 -IsoPath D:\ISOs\bazzite.iso -MemoryGB 10 -DiskGB 80 -VmPath E:\VMs
  .\New-DarkshamVM.ps1 -EjectIso        # after the install finished: boot from the disk
  .\New-DarkshamVM.ps1 -Remove          # delete the VM and its disk
  .\New-DarkshamVM.ps1 -DryRun -IsoPath x.iso    # only print what would happen
#>
[CmdletBinding()]
param(
    [string]$IsoPath,
    [string]$Name = "Darksham-OS-Test",
    [int]$MemoryGB = 8,
    [int]$CpuCount = 4,
    [int]$DiskGB = 64,
    [string]$VmPath,
    [string]$Switch = "Default Switch",
    [switch]$EjectIso,
    [switch]$Remove,
    [switch]$EnableHyperV,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }
function Fail($msg) { Say "ERROR: $msg" Red; exit 1 }
function Step($n, $msg) { Say ("[{0}] {1}" -f $n, $msg) Cyan }

# ---------------------------------------------------------------- elevation
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and -not $DryRun) {
    Say "Hyper-V needs an administrator prompt. Windows will ask for permission (UAC)..." Yellow
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-File", "`"$PSCommandPath`"")
    foreach ($k in $PSBoundParameters.Keys) {
        $v = $PSBoundParameters[$k]
        if ($v -is [System.Management.Automation.SwitchParameter]) { if ($v.IsPresent) { $argList += "-$k" } }
        else { $argList += "-$k"; $argList += "`"$v`"" }
    }
    Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs
    exit 0
}

# ---------------------------------------------------------------- checks
Step 1 "Checking this PC"
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
Say ("  Windows: {0}  |  RAM: {1} GB  |  virtualization on: {2}" -f $os.Caption, $ramGB, $cs.HypervisorPresent)
if ($os.Caption -match "Home") { Fail "Windows Home has no Hyper-V. Use VirtualBox or QEMU instead (see tools/vm/README.md)." }
if ($MemoryGB * 1GB -gt ($cs.TotalPhysicalMemory * 0.6)) { Fail "$MemoryGB GB is more than 60% of your RAM ($ramGB GB). Use -MemoryGB with a smaller number." }

if (-not (Get-Command New-VM -ErrorAction SilentlyContinue)) {
    if ($EnableHyperV) {
        if ($DryRun) { Say "  (dry run) would enable the Hyper-V feature and ask for a restart" Yellow; exit 0 }
        Say "  Enabling Hyper-V (a restart is needed afterwards)..." Yellow
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart | Out-Null
        Say "Done. Restart Windows, then run this script again." Green
        exit 0
    }
    Fail "The Hyper-V PowerShell module is missing. Run this script once with -EnableHyperV, restart Windows, then run it again."
}

# ---------------------------------------------------------------- remove
$existing = $null
if (-not $DryRun) { $existing = Get-VM -Name $Name -ErrorAction SilentlyContinue }
if ($Remove) {
    if ($DryRun) { Say "(dry run) would delete the VM '$Name' and its disk after you type YES." Yellow; exit 0 }
    if (-not $existing) { Say "No VM named $Name." Yellow; exit 0 }
    $disks = @($existing.HardDrives | ForEach-Object { $_.Path })
    Say "This deletes the VM '$Name' and its disk(s):" Yellow
    $disks | ForEach-Object { Say "  $_" Yellow }
    if ($DryRun) { Say "(dry run) nothing deleted." Yellow; exit 0 }
    if ((Read-Host "Type YES to continue") -ne "YES") { Say "Cancelled."; exit 0 }
    if ($existing.State -ne "Off") { Stop-VM -Name $Name -TurnOff -Force }
    Remove-VM -Name $Name -Force
    $disks | ForEach-Object { if (Test-Path $_) { Remove-Item $_ -Force } }
    Say "Removed." Green
    exit 0
}

# ---------------------------------------------------------------- eject
if ($EjectIso) {
    if (-not $existing) { Fail "No VM named $Name." }
    if ($DryRun) { Say "(dry run) would eject the ISO and boot from the disk." Yellow; exit 0 }
    if ($existing.State -ne "Off") { Say "Shut the VM down first (inside the VM, or Stop-VM -Name $Name)." Yellow; exit 1 }
    Get-VMDvdDrive -VMName $Name | Set-VMDvdDrive -Path $null
    $hd = Get-VMHardDiskDrive -VMName $Name | Select-Object -First 1
    Set-VMFirmware -VMName $Name -FirstBootDevice $hd
    Say "ISO ejected. Starting the VM from its disk..." Green
    Start-VM -Name $Name; vmconnect.exe localhost $Name
    exit 0
}

# ---------------------------------------------------------------- create
if ($existing) { Fail "A VM named '$Name' already exists. Use -Remove first, or pass -Name with another name." }
if (-not $IsoPath) { Fail "Pass the Bazzite ISO: -IsoPath C:\path\to\bazzite.iso (download it from https://bazzite.gg, the AMD/Intel KDE image)." }
if (-not (Test-Path -LiteralPath $IsoPath)) { Fail "ISO not found: $IsoPath" }
$IsoPath = (Resolve-Path -LiteralPath $IsoPath).Path
if ((Get-Item $IsoPath).Length -lt 1GB) { Fail "That file is smaller than 1 GB, it does not look like a Bazzite ISO: $IsoPath" }

# (a dry run never talks to Hyper-V, so it also works without an administrator prompt)
if (-not $DryRun) {
    $sw = Get-VMSwitch -Name $Switch -ErrorAction SilentlyContinue
    if (-not $sw) { Say ("  Switch '{0}' not found. Available: {1}" -f $Switch, ((Get-VMSwitch).Name -join ", ")) Yellow; Fail "Pass -Switch with one of those names." }
}

# put the VM on the fixed drive with the most free space (the disk can grow to -DiskGB)
if (-not $VmPath) {
    $best = Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq "Fixed" } | Sort-Object SizeRemaining -Descending | Select-Object -First 1
    $VmPath = "{0}:\VMs" -f $best.DriveLetter
}
$driveLetter = (Split-Path $VmPath -Qualifier).TrimEnd(":")
$freeGB = [math]::Round((Get-Volume -DriveLetter $driveLetter).SizeRemaining / 1GB, 1)
Say ("  VM folder: {0}  ({1} GB free)" -f $VmPath, $freeGB)
if ($freeGB -lt 45) { Fail "Less than 45 GB free on $driveLetter`: . The install plus the Darksham image need about 35 GB. Pass -VmPath on a bigger drive." }
if ($freeGB -lt $DiskGB) { Say "  Note: the disk is dynamic and can grow to $DiskGB GB, but only $freeGB GB is free." Yellow }

Step 2 "Plan"
Say ("  VM '{0}': {1} CPUs, {2} GB RAM, {3} GB dynamic disk, Secure Boot (Linux-friendly), switch '{4}'" -f $Name, $CpuCount, $MemoryGB, $DiskGB, $Switch)
Say ("  ISO: {0}" -f $IsoPath)
if ($DryRun) { Say "(dry run) nothing created." Yellow; exit 0 }

Step 3 "Creating the VM"
New-Item -ItemType Directory -Force -Path $VmPath | Out-Null
$vhd = Join-Path $VmPath "$Name.vhdx"
New-VHD -Path $vhd -SizeBytes ($DiskGB * 1GB) -Dynamic | Out-Null
New-VM -Name $Name -Generation 2 -MemoryStartupBytes ($MemoryGB * 1GB) -VHDPath $vhd -Path $VmPath -SwitchName $Switch | Out-Null
Set-VM -Name $Name -ProcessorCount $CpuCount -CheckpointType Disabled -AutomaticStopAction ShutDown
Set-VMMemory -VMName $Name -DynamicMemoryEnabled $false
Set-VMFirmware -VMName $Name -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
Set-VMVideo -VMName $Name -HorizontalResolution 1920 -VerticalResolution 1080 -ResolutionType Single
Add-VMDvdDrive -VMName $Name -Path $IsoPath
$dvd = Get-VMDvdDrive -VMName $Name
Set-VMFirmware -VMName $Name -FirstBootDevice $dvd
Enable-VMIntegrationService -VMName $Name -Name "Guest Service Interface" -ErrorAction SilentlyContinue

Step 4 "Starting"
Start-VM -Name $Name
vmconnect.exe localhost $Name

Say ""
Say "VM '$Name' is running. What to do next:" Green
Say "  1. In the VM window install Bazzite (KDE). Pick the disk, make a user, restart when asked."
Say "  2. When it asks to restart, shut the VM down instead and run:  .\New-DarkshamVM.ps1 -EjectIso"
Say "  3. Log in, open a terminal, and switch to Darksham OS (needs the GHCR package to be Public):"
Say "       sudo bootc switch ghcr.io/tamyyaz/ds-os:latest && systemctl reboot"
Say "  4. After the reboot, in a terminal:"
Say "       curl -fsSL https://raw.githubusercontent.com/tamyyaz/Ds-os/main/tools/vm/vm-check.sh | bash"
Say "     and send me the report (it is saved as ~/darksham-vm-report.txt)."
Say ""
Say "Remove everything later with:  .\New-DarkshamVM.ps1 -Remove" DarkGray
