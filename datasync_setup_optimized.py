#!/usr/bin/env python3
"""
DataSync Migration Setup - Production Ready
Cross-account S3 migrations using AWS DataSync with automatic backups & rollback.

Safety: Backups, policy merging (never replace), IAM reuse, dry-run mode, no auto-start
Usage: ./datasync_setup_optimized.py --config config.yaml [--dry-run] [--verbose]
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import boto3
import yaml
from botocore.exceptions import ClientError

# Logging with custom SUCCESS level and colors
logging.addLevelName(25, "SUCCESS")
logging.Logger.success = lambda self, msg, *args: (
    self._log(25, msg, args) if self.isEnabledFor(25) else None
)

COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[34m",
    "SUCCESS": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
}
SYMBOLS = {"DEBUG": "🔍", "INFO": "ℹ️", "SUCCESS": "✓", "WARNING": "⚠️", "ERROR": "✗"}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        level = "SUCCESS" if record.levelno == 25 else record.levelname
        record.levelname = f"{COLORS.get(level, '')}{SYMBOLS[level]}\033[0m"
        return super().format(record)


def get_logger(verbose: bool) -> logging.Logger:
    logger = logging.getLogger("datasync")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter("%(levelname)s %(message)s"))
    logger.handlers = [handler]
    return logger


# ============================================
# CONFIGURATION LOADING
# ============================================
def load_config(path: Path) -> Dict:
    """Load and validate YAML config. Requires: profiles, aws_region, role/policy names, migrations."""
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    req = [
        "profiles.source",
        "profiles.target",
        "aws_region",
        "datasync_role_name",
        "iam_policy_name",
        "migrations",
    ]
    missing = [
        f
        for f in req
        if not any(
            f.split(".")[0] in cfg
            and (len(f.split(".")) == 1 or f.split(".")[1] in cfg.get(f.split(".")[0], {}))
            for _ in [1]
        )
    ]
    if missing:
        raise ValueError(f"Missing config fields: {missing}")
    return cfg


# ============================================
# BACKUP MANAGEMENT
# ============================================
def backup_policies(
    s3_src,
    s3_tgt,
    src_bucket: str,
    dst_bucket: str,
    backup_dir: Path,
    src_prof: str,
    tgt_prof: str,
    log,
    dry_run: bool,
) -> None:
    """Backup bucket policies to timestamped dir. Creates restore.sh for one-click rollback."""
    if dry_run:
        return log.info("[DRY RUN] Would backup policies")
    backup_dir.mkdir(parents=True, exist_ok=True)

    for s3, bucket, typ in [(s3_src, src_bucket, "source"), (s3_tgt, dst_bucket, "dest")]:
        try:
            pol = s3.get_bucket_policy(Bucket=bucket)
            (backup_dir / f"{typ}-bucket-policy.json").write_text(
                json.dumps(json.loads(pol["Policy"]), indent=2)
            )
            log.success(f"Backed up {typ} bucket policy")
        except ClientError as err:
            if err.response["Error"]["Code"] == "NoSuchBucketPolicy":
                log.info(f"No {typ} bucket policy to backup")

    # Create cross-platform Python restore script
    (backup_dir / "restore.py").write_text(
        f'''#!/usr/bin/env python3
"""
Cross-platform restore script for bucket policies.
Works on Windows, macOS, and Linux.
"""
import json
import sys
from pathlib import Path

import boto3

def restore_policies():
    """Restore bucket policies from backup files."""
    backup_dir = Path(__file__).parent
    
    # Source bucket policy
    source_policy_file = backup_dir / "source-bucket-policy.json"
    if source_policy_file.exists():
        print(f"Restoring source bucket policy for {src_bucket}...")
        with open(source_policy_file, encoding="utf-8") as f:
            policy = f.read()
        
        session = boto3.Session(profile_name="{src_prof}")
        s3 = session.client("s3")
        s3.put_bucket_policy(Bucket="{src_bucket}", Policy=policy)
        print(f"✓ Restored source bucket policy for {src_bucket}")
    else:
        print(f"No source bucket policy backup found")
    
    # Destination bucket policy
    dest_policy_file = backup_dir / "dest-bucket-policy.json"
    if dest_policy_file.exists():
        print(f"Restoring destination bucket policy for {dst_bucket}...")
        with open(dest_policy_file, encoding="utf-8") as f:
            policy = f.read()
        
        session = boto3.Session(profile_name="{tgt_prof}")
        s3 = session.client("s3")
        s3.put_bucket_policy(Bucket="{dst_bucket}", Policy=policy)
        print(f"✓ Restored destination bucket policy for {dst_bucket}")
    else:
        print(f"No destination bucket policy backup found")
    
    print("\\n✓ Restore complete!")

if __name__ == "__main__":
    try:
        restore_policies()
        sys.exit(0)
    except Exception as e:
        print(f"\\n❌ Restore failed: {{e}}")
        sys.exit(1)
'''
    )
    if sys.platform != "win32":
        (backup_dir / "restore.py").chmod(0o755)
    log.success(f"Created restore: {backup_dir}/restore.py")


# ============================================
# IAM ROLE AND POLICY MANAGEMENT
# ============================================
def setup_iam(
    iam,
    role_name: str,
    policy_name: str,
    acct_id: str,
    region: str,
    src_buckets: List[str],
    dst_buckets: List[str],
    dst_acct: str,
    log,
    dry_run: bool,
) -> Tuple[str, bool]:
    """Create/retrieve IAM role in source account. NEVER modifies existing roles (reuses as-is).
    Includes confused deputy protection, source read perms, dest write perms with cross-account condition.
    """
    role_arn = f"arn:aws:iam::{acct_id}:role/{role_name}"

    try:
        iam.get_role(RoleName=role_name)
        log.success("IAM role exists - reusing without modification")
        return role_arn, False
    except ClientError as err:
        if err.response["Error"]["Code"] != "NoSuchEntity":
            raise

    if dry_run:
        log.info(f"[DRY RUN] Would create IAM role: {role_name}")
        return role_arn, True

    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "datasync.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {"aws:SourceAccount": acct_id},
                            "ArnLike": {"aws:SourceArn": f"arn:aws:datasync:{region}:{acct_id}:*"},
                        },
                    }
                ],
            }
        ),
        Description="DataSync S3 migration role",
    )
    log.success(f"Created role {role_name}")
    log.info("Waiting 15s for IAM propagation...")
    time.sleep(15)

    # Attach policy
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "SourceBucketAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetBucketLocation",
                            "s3:ListBucket",
                            "s3:ListBucketMultipartUploads",
                        ],
                        "Resource": [f"arn:aws:s3:::{b}" for b in src_buckets],
                    },
                    {
                        "Sid": "SourceObjectAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:GetObjectTagging",
                            "s3:GetObjectVersion",
                            "s3:GetObjectVersionTagging",
                            "s3:ListMultipartUploadParts",
                        ],
                        "Resource": [f"arn:aws:s3:::{b}/*" for b in src_buckets],
                    },
                    {
                        "Sid": "DestBucketAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetBucketLocation",
                            "s3:ListBucket",
                            "s3:ListBucketMultipartUploads",
                        ],
                        "Resource": [f"arn:aws:s3:::{b}" for b in dst_buckets],
                        "Condition": {"StringEquals": {"aws:ResourceAccount": dst_acct}},
                    },
                    {
                        "Sid": "DestObjectAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:AbortMultipartUpload",
                            "s3:DeleteObject",
                            "s3:GetObject",
                            "s3:GetObjectTagging",
                            "s3:PutObject",
                            "s3:PutObjectTagging",
                        ],
                        "Resource": [f"arn:aws:s3:::{b}/*" for b in dst_buckets],
                        "Condition": {"StringEquals": {"aws:ResourceAccount": dst_acct}},
                    },
                ],
            }
        ),
    )
    log.success(f"Attached policy {policy_name}")
    return role_arn, True


# ============================================
# BUCKET POLICY MANAGEMENT
# ============================================
def update_policy(s3, bucket: str, role_arn: str, log, dry_run: bool) -> None:
    """Safely merge DataSync perms into bucket policy. NEVER replaces - filters old DataSync statements,
    keeps all other statements (Jenkins, apps, etc.), adds new DataSync statements."""
    if dry_run:
        return log.info(f"[DRY RUN] Would update policy for {bucket}")

    ds_stmts = [
        {
            "Sid": "DataSyncAllowBucketAccess",
            "Effect": "Allow",
            "Principal": {"AWS": role_arn},
            "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:ListBucketMultipartUploads"],
            "Resource": f"arn:aws:s3:::{bucket}",
        },
        {
            "Sid": "DataSyncAllowObjectAccess",
            "Effect": "Allow",
            "Principal": {"AWS": role_arn},
            "Action": [
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:PutObject",
                "s3:PutObjectTagging",
                "s3:GetObjectTagging",
            ],
            "Resource": f"arn:aws:s3:::{bucket}/*",
        },
    ]

    # Get existing bucket policy, or create empty policy if none exists
    try:
        pol = json.loads(s3.get_bucket_policy(Bucket=bucket)["Policy"])
    except ClientError as err:
        # If no policy exists, start with empty policy structure
        if err.response["Error"]["Code"] == "NoSuchBucketPolicy":
            pol = {"Version": "2012-10-17", "Statement": []}
        else:
            raise

    # CRITICAL SAFETY STEP: Merge policies instead of replacing
    # Filter out old DataSync statements (by Sid) to avoid duplicates
    # Keep ALL other statements (Jenkins, apps, etc.) untouched
    ds_sids = {"DataSyncAllowBucketAccess", "DataSyncAllowObjectAccess"}
    pol["Statement"] = [
        s for s in pol.get("Statement", []) if s.get("Sid") not in ds_sids
    ] + ds_stmts

    # Apply the merged policy back to the bucket
    s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(pol))
    log.success(f"Updated policy for {bucket}")


# ============================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# ============================================
def retry_with_backoff(func, max_retries: int = 3, backoff: float = 2.0, log=None):
    """Execute with exponential backoff for AWS rate limits. Retries: 2s, 4s, 8s."""
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as err:
            code = err.response["Error"]["Code"]
            # Retry only on rate limiting errors
            if code in ["Throttling", "RequestLimitExceeded", "TooManyRequestsException"]:
                if attempt < max_retries - 1:
                    wait = backoff**attempt
                    if log:
                        log.warning(f"Rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
            raise  # Re-raise non-retriable errors


# ============================================
# BUCKET ACCESS VERIFICATION
# ============================================
def verify_bucket_access(s3, bucket: str, log) -> bool:
    """Verify bucket exists and is accessible. Early failure with clear errors."""
    try:
        s3.head_bucket(Bucket=bucket)
        return True
    except ClientError as err:
        code = err.response["Error"]["Code"]
        if code == "404":
            log.error(f"Bucket '{bucket}' does not exist")
        elif code == "403":
            log.error(f"Access denied to bucket '{bucket}'")
        else:
            log.error(f"Cannot access bucket '{bucket}': {err}")
        return False


# ============================================
# DATASYNC TASK CREATION WITH ROLLBACK
# ============================================
def create_datasync(ds, src: str, dst: str, role_arn: str, opts: Dict, log, dry_run: bool) -> str:
    """Create DataSync source location, dest location, and task. Auto-rollback on failure to prevent orphans."""
    if dry_run:
        log.info(f"[DRY RUN] Would create task: {src} → {dst}")
        return f"arn:aws:datasync:region:account:task/task-DRYRUN"

    # Track created resources for rollback if needed
    created_resources = []

    try:
        # Create source location with retry logic
        src_loc = retry_with_backoff(
            lambda: ds.create_location_s3(
                S3BucketArn=f"arn:aws:s3:::{src}",
                S3Config={"BucketAccessRoleArn": role_arn},
                Subdirectory="/",
                S3StorageClass="STANDARD",
            )["LocationArn"],
            log=log,
        )
        created_resources.append(("location", src_loc))
        log.success(f"Source location: {src_loc}")

        # Create destination location with retry logic
        dst_loc = retry_with_backoff(
            lambda: ds.create_location_s3(
                S3BucketArn=f"arn:aws:s3:::{dst}",
                S3Config={"BucketAccessRoleArn": role_arn},
                Subdirectory="/",
                S3StorageClass="STANDARD",
            )["LocationArn"],
            log=log,
        )
        created_resources.append(("location", dst_loc))
        log.success(f"Dest location: {dst_loc}")

        # Build task options with sensible defaults
        task_opts = {
            "TransferMode": opts.get("TransferMode", "CHANGED"),
            "VerifyMode": opts.get("VerifyMode", "NONE"),
            "OverwriteMode": opts.get("OverwriteMode", "ALWAYS"),
            "LogLevel": opts.get("LogLevel", "TRANSFER"),
            "PreserveDeletedFiles": opts.get("PreserveDeletedFiles", "PRESERVE"),
            "PreserveDevices": opts.get("PreserveDevices", "NONE"),
        }

        task_params = {
            "SourceLocationArn": src_loc,
            "DestinationLocationArn": dst_loc,
            "Name": f"Migration-{src}-to-{dst}",
            "Options": task_opts,
        }

        # Add TaskMode if specified (ENHANCED recommended)
        if "TaskMode" in opts:
            task_params["TaskMode"] = opts["TaskMode"]

        # Create task with retry logic
        task_arn = retry_with_backoff(lambda: ds.create_task(**task_params)["TaskArn"], log=log)
        log.success(f"Task: {task_arn}")
        return task_arn

    except Exception:
        # AUTOMATIC ROLLBACK: Clean up any resources created before failure
        if created_resources:
            log.warning(
                f"Task creation failed, rolling back {len(created_resources)} resource(s)..."
            )
            for res_type, res_arn in reversed(created_resources):
                try:
                    if res_type == "location":
                        ds.delete_location(LocationArn=res_arn)
                        log.info(f"Deleted location: {res_arn}")
                except Exception as cleanup_err:
                    log.error(f"Rollback failed for {res_arn}: {cleanup_err}")
        raise  # Re-raise original error after cleanup


# ============================================
# MAIN ORCHESTRATION
# ============================================
def main():
    """Main orchestration: load config, setup IAM, verify buckets, backup policies, create tasks.
    Stops before starting data transfer for manual review."""
    parser = argparse.ArgumentParser(description="DataSync Setup Tool (Optimized)")
    parser.add_argument("-c", "--config", required=True, type=Path, help="Config YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Initialize logger with appropriate level (DEBUG if verbose, otherwise INFO)
    log = get_logger(args.verbose)

    try:
        cfg = load_config(args.config)
        log.info(f"{'=' * 60}\nDataSync Setup {'(DRY RUN)' if args.dry_run else ''}\n{'=' * 60}")

        src_sess = boto3.Session(
            profile_name=cfg["profiles"]["source"], region_name=cfg["aws_region"]
        )
        tgt_sess = boto3.Session(
            profile_name=cfg["profiles"]["target"], region_name=cfg["aws_region"]
        )

        iam, s3_src, s3_tgt, ds = (src_sess.client(c) for c in ["iam", "s3", "s3", "datasync"])
        s3_tgt = tgt_sess.client("s3")

        src_acct = src_sess.client("sts").get_caller_identity()["Account"]
        tgt_acct = tgt_sess.client("sts").get_caller_identity()["Account"]
        log.success(f"Source: {src_acct} | Target: {tgt_acct}\n")

        migrations = cfg["migrations"]
        log.info(f"Processing {len(migrations)} migration(s)\n")

        src_buckets = [m["source_bucket"] for m in migrations]
        dst_buckets = [m["destination_bucket"] for m in migrations]

        log.info("Setting up IAM role...")
        role_arn, _ = setup_iam(
            iam,
            cfg["datasync_role_name"],
            cfg["iam_policy_name"],
            src_acct,
            cfg["aws_region"],
            src_buckets,
            dst_buckets,
            tgt_acct,
            log,
            args.dry_run,
        )
        log.info(f"Role: {role_arn}\n")

        results = []
        for idx, mig in enumerate(migrations, 1):
            log.info(
                f"{'=' * 60}\nMigration {idx}/{len(migrations)}: {mig['source_bucket']} → {mig['destination_bucket']}\n{'-' * 60}"
            )

            try:
                # Verify bucket access before changes
                if not args.dry_run:
                    log.info("Verifying bucket access...")
                    if not verify_bucket_access(s3_src, mig["source_bucket"], log):
                        raise ValueError(f"Cannot access source bucket: {mig['source_bucket']}")
                    if not verify_bucket_access(s3_tgt, mig["destination_bucket"], log):
                        raise ValueError(
                            f"Cannot access destination bucket: {mig['destination_bucket']}"
                        )
                    log.success("Bucket access verified\n")

                # Backup policies to timestamped dir
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                bak_dir = (
                    Path(cfg.get("backup_dir", Path.home() / "Downloads" / "backups"))
                    / f"mig{idx}-{ts}"
                )
                backup_policies(
                    s3_src,
                    s3_tgt,
                    mig["source_bucket"],
                    mig["destination_bucket"],
                    bak_dir,
                    cfg["profiles"]["source"],
                    cfg["profiles"]["target"],
                    log,
                    args.dry_run,
                )

                # Update bucket policies (safe merge - preserves existing)
                log.info(f"\nUpdating bucket policies...")
                update_policy(s3_src, mig["source_bucket"], role_arn, log, args.dry_run)
                update_policy(s3_tgt, mig["destination_bucket"], role_arn, log, args.dry_run)

                # Create DataSync task (NOT started)
                log.info(f"\nCreating DataSync task...")
                task_arn = create_datasync(
                    ds,
                    mig["source_bucket"],
                    mig["destination_bucket"],
                    role_arn,
                    mig.get("options", {}),
                    log,
                    args.dry_run,
                )

                results.append((mig, task_arn, bak_dir))
                log.success(f"\n✅ Migration {idx} setup complete\n")

            except Exception as e:
                log.error(f"Migration {idx} failed: {e}")
                break

        print(
            f"\n{'=' * 60}\n{'✅ DRY RUN COMPLETE' if args.dry_run else f'✅ {len(results)} migration(s) configured'}\n{'=' * 60}\n"
        )

        if not args.dry_run and results:
            for idx, (mig, task, bak) in enumerate(results, 1):
                print(f"Migration {idx}: {mig['source_bucket']} → {mig['destination_bucket']}")
                print(f"  Task: {task}")
                print(f"  Backup: {bak}\n")

            print(
                f"▶️  Start migration:\n   aws datasync start-task-execution --task-arn {results[0][1]} \\"
            )
            print(f"     --region {cfg['aws_region']} --profile {cfg['profiles']['source']}\n")
            log.warning("⚠️  Migrations NOT auto-started - review and start manually\n")

        sys.exit(0)

    except KeyboardInterrupt:
        log.warning("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as err:
        log.error(f"\n❌ Failed: {err}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
