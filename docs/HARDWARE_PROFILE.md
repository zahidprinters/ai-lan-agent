# Hardware Profile (Detected 2026-04-04)

This profile is captured from the current development machine to keep training and tooling aligned with real hardware limits.

## System Summary

- Manufacturer/Model: LENOVO 20L6S63U0G
- OS: Windows 11 Pro (Build 26200, 64-bit)
- CPU: Intel Core i5-8350U (4 cores / 8 threads)
- RAM: 16 GB DDR4 @ 2400 MT/s
- GPU: Intel UHD Graphics 620 (integrated)
- Discrete GPU: None detected
- Main SSD: Samsung MZVLB256HAHQ (256 GB NVMe)

## Chipset-Like Devices (Key)

- Intel Host Bridge/DRAM Registers (5914)
- Mobile Intel Processor Family I/O LPC Controller (9D4E)
- Multiple Intel PCI Express Root Ports (9D10/9D16/9D18/9D1A)
- Synaptics SMBus Driver

## Project Guidance For This Machine

- Keep runtime target as CPU-first; do not assume CUDA.
- Use small to medium profiles by default (`debug`, `baseline`, `transformer_small`).
- Prefer lower-risk batch/block values when training on battery or while multitasking.
- Keep all temporary artifacts under `temp/`.

## Recommended Environment Defaults

Use these for stable runs on this machine:

```powershell
$env:AI_LAN_DEVICE="cpu"
$env:AI_LAN_USE_AMP="0"
$env:AI_LAN_EXP_PROFILE="transformer_small"
$env:AI_LAN_BATCH_SIZE="8"
$env:AI_LAN_BLOCK_SIZE="16"
```

## Refresh Hardware Snapshot

Regenerate the raw hardware snapshot JSON at any time:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/hardware_profile.ps1
```

Default output path:

- `temp/hardware/hardware_profile.json`
