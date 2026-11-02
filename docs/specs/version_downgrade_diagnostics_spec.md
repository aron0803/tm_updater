# Spec: Version Downgrade Timeout Diagnostics & Prevention

## 1. Background & Root Causes

During version downgrade / specified version installation, users report occasional timeouts (120s delay followed by failure).
Analysis reveals two major factors:
1. **Missing `--no-index`**: When installing via `--find-links={source_path} {pkg}=={ver}`, pip without `--no-index` still attempts to query the external PyPI package index. On isolated lab/factory test computers or firewalled environments, network connect requests hang until socket timeout (repeated retries consume over 100-120 seconds), causing `subprocess.TimeoutExpired`.
2. **Monolithic Try-Catch & Lack of Phased Logs**: Both `pip uninstall` and `pip install` were wrapped in a single `try...except subprocess.TimeoutExpired` without logging timestamps, per-stage elapsed times, or stdout/stderr. When a timeout occurred, operators could not determine whether uninstall or install timed out, nor what pip was doing.

## 2. Technical Specifications

### 2.1 Pip Execution Parameters (`src/updater/core.py`)
- **Stage 1: Uninstall**
  - Command: `[python_exe, "-m", "pip", "uninstall", "-y", "--no-input", package_name]`
  - Timeout: 120s
- **Stage 2: Install**
  - Command: `[python_exe, "-m", "pip", "install", "--no-index", f"--find-links={source_path}", "--no-input", f"{package_name}=={target_version}"]`
  - When `--no-index` is specified, pip operates 100% offline using wheels provided in `source_path`.
  - `--no-input` guarantees pip never waits for interactive input.

### 2.2 Structured Phased Logging
- **Stage 1 (Uninstall)**:
  - Start: `[1/2] 解除安裝舊版本 ({installed_ver})...`
  - Success: `[1/2] 解除安裝完成 (耗時 X.Xs)`
  - Failure: `[1/2 解除安裝失敗] {stderr}`
  - Timeout: `[1/2 解除安裝逾時] pip uninstall 超過 120 秒未回應（可能原因：相關程式仍在使用該套件檔案造成鎖檔）`
- **Stage 2 (Install)**:
  - Pre-inspection: Check if matching `.whl` exists in `source_path` and log: `[2/2] 找到 wheel: {filename}`
  - Start: `[2/2] 安裝指定版本 v{target_version}...`
  - Success: `[2/2] 安裝完成 (耗時 X.Xs)`
  - Failure: `[2/2 安裝失敗] {stderr}`
  - Timeout: `[2/2 安裝逾時] pip install 超過 120 秒未回應`

