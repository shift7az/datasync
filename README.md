# AWS DataSync Setup Tool

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Code Quality](https://img.shields.io/badge/pylint-8.27/10-brightgreen)
![AWS](https://img.shields.io/badge/AWS-DataSync-orange)
[![Validate](https://github.com/shift7az/datasync/actions/workflows/validate.yml/badge.svg)](https://github.com/shift7az/datasync/actions/workflows/validate.yml)

**Production-ready automation for AWS DataSync cross-account S3 migrations**

Safely migrate S3 buckets between AWS accounts with automatic backups, policy merging, and rollback capabilities.

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](CONTRIBUTING.md)

</div>

---

## 📋 Table of Contents

- [Why Use This Tool?](#-why-use-this-tool)
- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [How It Works](#-how-it-works)
- [Safety Features](#-safety-features)
- [Troubleshooting](#-troubleshooting)
- [Advanced Usage](#-advanced-usage)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Why Use This Tool?

Setting up AWS DataSync for cross-account migrations is complex and error-prone. This tool automates the entire process while maintaining safety through:

- ✅ **Zero Risk** - Automatic backups before any changes
- ✅ **Policy Safety** - Never overwrites existing bucket policies
- ✅ **IAM Safety** - Reuses existing roles, never modifies them
- ✅ **Dry-Run First** - Preview all changes before execution
- ✅ **Auto-Rollback** - Cleans up orphaned resources on failure
- ✅ **Production Ready** - Battle-tested with comprehensive error handling

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Automatic Backups** | All bucket policies backed up with one-click restore |
| 🛡️ **Safe Policy Merging** | Preserves existing statements (Jenkins, apps, etc.) |
| 🔑 **IAM Reuse** | Never modifies existing roles - reuses as-is |
| ✅ **Bucket Verification** | Early failure detection with clear error messages |
| 🔁 **Retry Logic** | Exponential backoff for AWS rate limits |
| ↩️ **Automatic Rollback** | Cleans up orphaned resources on failure |
| 🔍 **Dry-Run Mode** | Preview all changes without modifications |
| 🚫 **No Auto-Start** | Manual approval required for data transfer |
| 🎨 **Colored Logging** | Clear visual feedback with emojis |
| 📦 **Multi-Migration** | Process multiple bucket pairs in one run |

---

## 📦 Prerequisites

- **Python 3.8+** (Windows, macOS, or Linux)
- **AWS CLI** configured with profiles for both accounts
- **IAM Permissions:**
  - Source account: IAM role creation, S3 bucket policy management
  - Target account: S3 bucket policy management
- **AWS DataSync** - Available in your region

### Cross-Platform Support

✅ **Fully compatible** with Windows, macOS, and Linux  
✅ Pure Python implementation - no platform-specific dependencies  
✅ Cross-platform file paths using `pathlib`  
✅ Universal restore script in Python (no bash required)

---

## 🚀 Installation

### Option 1: Using pip (Recommended)

```bash
pip install -r requirements.txt
```

### Option 2: Using virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Requirements

- `boto3>=1.28.0`
- `pyyaml>=6.0`

---

## ⚡ Quick Start

### 1. Create Configuration File

Create `config.yaml`:

```yaml
profiles:
  source: my-source-profile
  target: my-target-profile

aws_region: us-west-2

datasync_role_name: DataSyncS3MigrationRole
iam_policy_name: DataSyncS3MigrationPolicy

migrations:
  - source_bucket: my-source-bucket
    destination_bucket: my-dest-bucket
    options:
      TaskMode: ENHANCED
      TransferMode: CHANGED
      VerifyMode: NONE
```

### 2. Preview Changes (Dry-Run)

```bash
python datasync_setup_optimized.py --config config.yaml --dry-run
```

### 3. Execute Setup

```bash
python datasync_setup_optimized.py --config config.yaml
```

### 4. Start Migration

```bash
aws datasync start-task-execution \
  --task-arn <TASK_ARN_FROM_OUTPUT> \
  --region us-west-2 \
  --profile my-source-profile
```

---

## ⚙️ Configuration

### Basic Configuration

```yaml
profiles:
  source: source-account-profile    # AWS CLI profile for source
  target: target-account-profile    # AWS CLI profile for target

aws_region: us-west-2               # Region for both buckets

datasync_role_name: DataSyncS3MigrationRole
iam_policy_name: DataSyncS3MigrationPolicy

migrations:
  - source_bucket: my-source-bucket
    destination_bucket: my-dest-bucket
```

### Task Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `TaskMode` | ENHANCED, BASIC | ENHANCED | ENHANCED is faster with no quotas |
| `TransferMode` | CHANGED, ALL | CHANGED | CHANGED only syncs new/modified files |
| `VerifyMode` | NONE, ONLY_FILES_TRANSFERRED, POINT_IN_TIME_CONSISTENT | NONE | File verification level |
| `OverwriteMode` | ALWAYS, NEVER | ALWAYS | Overwrite existing files |
| `LogLevel` | TRANSFER, BASIC, OFF | TRANSFER | Logging verbosity |

See [datasync-config.example.yaml](datasync-config.example.yaml) for complete options.

---

## 📖 Usage

### Command-Line Options

```bash
python datasync_setup_optimized.py [OPTIONS]

Options:
  -c, --config PATH    Configuration YAML file (required)
  --dry-run           Preview changes without modifying anything
  -v, --verbose       Enable verbose output for debugging
  -h, --help          Show help message
```

### Examples

**Dry-run with verbose output:**
```bash
python datasync_setup_optimized.py --config config.yaml --dry-run --verbose
```

**Production setup:**
```bash
python datasync_setup_optimized.py --config config.yaml
```

---

## 🔧 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    DataSync Setup Flow                       │
└─────────────────────────────────────────────────────────────┘

1️⃣  Load & Validate Configuration
    ├─ Parse YAML configuration
    ├─ Validate required fields
    └─ Connect to AWS accounts

2️⃣  Setup IAM (Source Account)
    ├─ Check if role exists (reuse if found)
    ├─ Create role with confused deputy protection
    └─ Attach policy with least privilege permissions

3️⃣  For Each Migration:
    ├─ Verify bucket access
    ├─ Backup existing bucket policies
    ├─ Merge DataSync permissions (safe)
    ├─ Create DataSync locations
    ├─ Create DataSync task
    └─ Generate restore scripts

4️⃣  Output Results
    ├─ Display task ARNs
    ├─ Show backup locations
    └─ Provide start command
```

### What Gets Created

| Resource | Location | Notes |
|----------|----------|-------|
| IAM Role | Source Account | Only if doesn't exist |
| IAM Policy | Source Account | Inline policy |
| Bucket Policies | Both Accounts | Merged, not replaced |
| DataSync Locations | Source Account | S3 source & destination |
| DataSync Task | Source Account | Not started automatically |
| Backup Files | Local Filesystem | With restore scripts |

---

## 🛡️ Safety Features

### Automatic Backups

Before any changes, creates timestamped backups:

```
~/Downloads/backups/mig1-20251030-134521/
├── source-bucket-policy.json    # Complete backup
├── dest-bucket-policy.json      # Complete backup
└── restore.py                   # Cross-platform restore script
```

### Policy Merging (Never Replaces)

```diff
📋 Existing Policy:
+ Jenkins CI/CD permissions
+ Application access permissions
+ Monitoring service permissions

➕ After Script:
+ Jenkins CI/CD permissions (preserved)
+ Application access permissions (preserved)
+ Monitoring service permissions (preserved)
+ DataSync permissions (added)
```

### Restore from Backup

**Windows:**
```cmd
cd %USERPROFILE%\Downloads\backups\<timestamp>
python restore.py
```

**macOS/Linux:**
```bash
cd ~/Downloads/backups/<timestamp>
python restore.py
```

### Automatic Rollback

If task creation fails, automatically cleans up:
- ✅ Deletes created DataSync locations
- ✅ Logs all cleanup actions
- ✅ Reports errors clearly

---

## 🔍 Troubleshooting

<details>
<summary><b>"Invalid principal" Error</b></summary>

**Cause:** IAM role not yet propagated across AWS

**Solution:** Script waits 15s automatically. If error persists, wait 1-2 minutes and re-run.
</details>

<details>
<summary><b>"Access Denied" to Bucket</b></summary>

**Cause:** 
- Bucket doesn't exist
- AWS profile lacks permissions
- Wrong region

**Solution:**
1. Verify bucket exists: `aws s3 ls s3://bucket-name`
2. Check profile permissions
3. Confirm region matches
</details>

<details>
<summary><b>"Task creation failed, rolling back..."</b></summary>

**Cause:** DataSync API error (rate limits, quotas, permissions)

**Solution:**
1. Check error message in output
2. Verify all prerequisites
3. Run with `--verbose` for details
4. Retry after fixing issue
</details>

### Getting Help

- 📖 Check [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- 🐛 [Report bugs](https://github.com/shift7az/datasync/issues/new?template=bug_report.md)
- 💡 [Request features](https://github.com/shift7az/datasync/issues/new?template=feature_request.md)

---

## 🎓 Advanced Usage

### Multiple Migrations

Process multiple bucket pairs in one run:

```yaml
migrations:
  - source_bucket: bucket-1
    destination_bucket: dest-1
  - source_bucket: bucket-2
    destination_bucket: dest-2
  - source_bucket: bucket-3
    destination_bucket: dest-3
```

All processed sequentially with a single IAM role.

### Custom Backup Directory

```yaml
backup_dir: /path/to/custom/backups
```

Default: `~/Downloads/backups/`

### Monitoring Migrations

```bash
# Check task status
aws datasync describe-task-execution \
  --task-execution-arn <EXECUTION_ARN> \
  --region us-west-2 \
  --profile source-profile

# View in AWS Console
https://console.aws.amazon.com/datasync/home
```

---

## 🔒 Security

- ✅ IAM role created in source account only
- ✅ Confused deputy protection (`aws:SourceAccount`, `aws:SourceArn`)
- ✅ Cross-account condition on destination permissions
- ✅ Least privilege S3 permissions
- ✅ No credentials in code (uses AWS CLI profiles)
- ✅ Automatic policy backups for rollback

---

## 🤝 Contributing

We welcome contributions! Please see:

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community guidelines
- [CHANGELOG.md](CHANGELOG.md) - Version history

### Development Setup

```bash
git clone https://github.com/shift7az/datasync.git
cd datasync
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pylint black
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🌟 Acknowledgments

Built with ❤️ for the AWS community

- Inspired by real-world S3 migration challenges
- Designed with safety and automation in mind
- Production-tested on multiple large-scale migrations

---

<div align="center">

**[⬆ back to top](#aws-datasync-setup-tool)**

Made with ☕ and Python | [Report Bug](https://github.com/shift7az/datasync/issues) | [Request Feature](https://github.com/shift7az/datasync/issues)

</div>
