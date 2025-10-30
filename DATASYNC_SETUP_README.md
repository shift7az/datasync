# DataSync Setup Tool - Production Ready

Automated setup for AWS DataSync cross-account S3 migrations with comprehensive safety features.

## Features

✅ **Automatic Backups** - All bucket policies backed up before changes
✅ **Safe Policy Merging** - Never replaces existing statements (Jenkins, apps preserved)
✅ **IAM Reuse** - Never modifies existing roles
✅ **Bucket Verification** - Early failure detection
✅ **Retry Logic** - Exponential backoff for AWS rate limits
✅ **Automatic Rollback** - Cleans up orphaned resources on failure
✅ **Dry-Run Mode** - Preview changes safely
✅ **No Auto-Start** - Manual approval required for data transfer
✅ **Colored Logging** - Clear visual feedback
✅ **Multi-Migration** - Process multiple bucket pairs in one run

## Requirements

```bash
pip install boto3 pyyaml
```

AWS CLI profiles configured for both source and target accounts.

## Configuration

Create `config.yaml`:

```yaml
profiles:
  source: source-account-profile    # AWS profile for source account
  target: target-account-profile    # AWS profile for target account

aws_region: us-west-2

datasync_role_name: DataSyncS3MigrationRole
iam_policy_name: DataSyncS3MigrationPolicy

migrations:
  - source_bucket: my-source-bucket
    destination_bucket: my-dest-bucket
    options:
      TaskMode: ENHANCED              # ENHANCED | BASIC
      TransferMode: CHANGED           # CHANGED | ALL
      VerifyMode: NONE                # NONE | ONLY_FILES_TRANSFERRED | POINT_IN_TIME_CONSISTENT
      OverwriteMode: ALWAYS           # ALWAYS | NEVER
      LogLevel: TRANSFER              # TRANSFER | BASIC | OFF
```

## Usage

### Dry-Run (Recommended First)

```bash
python datasync_setup_optimized.py --config config.yaml --dry-run
```

Preview all changes without modifying anything.

### Execute Setup

```bash
python datasync_setup_optimized.py --config config.yaml
```

### With Verbose Output

```bash
python datasync_setup_optimized.py --config config.yaml --dry-run --verbose
```

## What Gets Modified

### ✅ Created/Modified (Safely)
- **IAM Role** (source account) - Only if doesn't exist
- **IAM Policy** (inline) - Only if role was just created
- **Bucket Policies** (both accounts) - Merges DataSync statements, keeps all existing

### ❌ Never Modified
- **Existing IAM roles** - Reused without changes
- **Bucket ACLs** - Untouched
- **Bucket configurations** - Untouched (versioning, encryption, tags, etc.)
- **Existing policy statements** - All preserved
- **Objects** - No data transfer until manual start

## Safety Features

### Automatic Backups

Before ANY changes, creates:
```
~/Downloads/backups/mig1-YYYYMMDD-HHMMSS/
├── source-bucket-policy.json    # Complete backup
├── dest-bucket-policy.json      # Complete backup
└── restore.sh                   # One-click restore script
```

### Restore from Backup

```bash
cd ~/Downloads/backups/<timestamp>
./restore.sh
```

### Policy Merging Logic

The script **never** replaces bucket policies. It:
1. Retrieves existing policy
2. Filters out old DataSync statements (by Sid)
3. Keeps ALL other statements
4. Adds new DataSync statements
5. Applies merged policy

**Example:**
```
Existing: Jenkins permissions + App permissions
Result:   Jenkins permissions + App permissions + DataSync permissions
```

## Example Run

```bash
$ python datasync_setup_optimized.py --config migration-config.yaml

============================================================
DataSync Setup
============================================================
✓ Source: 123456789012 | Target: 987654321098

ℹ️  Processing 1 migration(s)

ℹ️  Setting up IAM role...
✓ IAM role exists - reusing without modification
ℹ️  Role: arn:aws:iam::123456789012:role/DataSyncS3MigrationRole

============================================================
Migration 1/1: my-source-bucket → my-dest-bucket
------------------------------------------------------------

ℹ️  Verifying bucket access...
✓ Bucket access verified

✓ Backed up source bucket policy
✓ Backed up dest bucket policy
✓ Created restore: /Users/username/Downloads/backups/mig1-20251030-134521/restore.sh

ℹ️  Updating bucket policies...
✓ Updated policy for my-source-bucket
✓ Updated policy for my-dest-bucket

ℹ️  Creating DataSync task...
✓ Source location: arn:aws:datasync:us-west-2:123456789012:location/loc-xxx
✓ Dest location: arn:aws:datasync:us-west-2:123456789012:location/loc-yyy
✓ Task: arn:aws:datasync:us-west-2:123456789012:task/task-zzz

✓ Migration 1 setup complete

============================================================
✅ 1 migration(s) configured
============================================================

Migration 1: my-source-bucket → my-dest-bucket
  Task: arn:aws:datasync:us-west-2:123456789012:task/task-zzz
  Backup: /Users/username/Downloads/backups/mig1-20251030-134521

▶️  Start migration:
   aws datasync start-task-execution --task-arn <TASK_ARN> \
     --region us-west-2 --profile source-account-profile

⚠️  Migrations NOT auto-started - review and start manually
```

## Starting Migrations

The script outputs the exact command to start each migration:

```bash
aws datasync start-task-execution \
  --task-arn arn:aws:datasync:us-west-2:ACCOUNT:task/task-ID \
  --region us-west-2 \
  --profile source-profile
```

## Monitoring

```bash
# Check task status
aws datasync describe-task-execution \
  --task-execution-arn <EXECUTION_ARN> \
  --region us-west-2 \
  --profile source-profile

# Or view in AWS Console
https://us-west-2.console.aws.amazon.com/datasync/home
```

## Troubleshooting

### "Invalid principal" Error
**Cause:** IAM role not yet propagated
**Solution:** Script waits 15s, but if error persists, wait 1-2 minutes and re-run

### "Access Denied" to Bucket
**Cause:** Bucket doesn't exist or profile lacks permissions
**Solution:** Verify buckets exist and profiles have correct permissions

### "Task creation failed, rolling back..."
**Cause:** DataSync API error during task creation
**Solution:** Check logs, verify all prerequisites, retry after fixing issue

## Advanced

### Multiple Migrations

```yaml
migrations:
  - source_bucket: bucket-1
    destination_bucket: dest-1
  - source_bucket: bucket-2  
    destination_bucket: dest-2
  - source_bucket: bucket-3
    destination_bucket: dest-3
```

All processed sequentially with single IAM role.

### Custom Backup Directory

```yaml
backup_dir: /path/to/custom/backups
```

Default: `~/Downloads/backups/`

## Security

- IAM role created in source account only
- Confused deputy protection (aws:SourceAccount, aws:SourceArn)
- Cross-account condition on destination permissions
- Least privilege S3 permissions
- No credentials in code (uses AWS CLI profiles)

## Support

**Common Issues:**
1. Check AWS CLI profiles configured correctly
2. Verify buckets exist in correct region
3. Ensure IAM permissions in both accounts
4. Review backup/restore capability
5. Test with dry-run first

**Logs:** Use `--verbose` for detailed output

**Backups:** Always stored in timestamped directories

**Restore:** Run `restore.sh` from backup directory if needed
