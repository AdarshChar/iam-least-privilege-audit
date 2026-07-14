# FrazyCorp IAM Least Privilege Enforcement

## The Business Problem

Permission sprawl is one of the leading causes of cloud breaches. When companies 
manage IAM manually through the AWS console, permissions build up
over time. If a developer gets temporary admin access to unblock a 
deadline, or their permissions are never updated after moving to a different team, 
that access never gets revoked. Months later that over-permissioned 
account becomes the entry point for a breach. This project builds a 
system that enforces least privilege automatically, audits continuously, 
and blocks violations before they ever reach AWS.

---

## Architecture

![Architecture Diagram](architecture.png)

---

## Technologies Used

| Category | Technologies |
|----------|-------------|
| Infrastructure as Code | Terraform |
| Cloud Provider | AWS |
| IAM Services | IAM, IAM Access Analyzer, Secrets Manager |
| Compliance | AWS Config (5 rules) |
| CI/CD | GitHub Actions |
| Authentication | OIDC (no stored credentials) |
| Security Scanning | Checkov |
| Scripting | Python, boto3 |
| Storage | S3, DynamoDB |

---

## The Before State (Phase 2)

Before enforcement, FrazyCorp's IAM was deliberately misconfigured 
to simulate real-world permission sprawl:

| Department | Policy Applied | Why It's Wrong |
|------------|---------------|----------------|
| Engineering | AmazonS3FullAccess | Can access ALL S3 buckets including HR records |
| Finance | AdministratorAccess | Full control of entire AWS account |
| HR | AmazonS3FullAccess | Can access finance reports and engineering data |
| Operations | PowerUserAccess | Near-complete account access |

![Before State - Finance AdministratorAccess](screenshots/phase2-before-state/Finance%20Permission.png)

---

## The After State (Phase 3)

Every department now has a custom least privilege policy scoped 
to exactly the resources they need:

| Department | Users | Can Access | Actions Allowed |
|------------|-------|------------|-----------------|
| Engineering | dev1, dev2 | engineering-data bucket, engineering-db | GetObject, PutObject, DeleteObject, ListBucket, DynamoDB CRUD |
| Finance | fin1, fin2 | finance-reports bucket (read only), finance-db | GetObject, ListBucket, DynamoDB reads only |
| HR | hr1 | hr-records bucket only | GetObject, PutObject, ListBucket |
| Operations | ops1 | ops-logs bucket only | PutObject, ListBucket |

![After State - Terraform Apply](screenshots/phase3-after-state/Terraform%20apply.png)
![After State - Customer Managed Policies](screenshots/phase3-after-state/IAM%20Group%20Policies.png)
![After State - Finance Least Privilege JSON](screenshots/phase3-after-state/Finance%20Least%20Privilege.png)

---

## Continuous Compliance (Phase 4)

Five AWS Config rules run continuously to detect drift between 
Terraform runs:

| Rule | What It Checks | Current Status |
|------|---------------|----------------|
| iam-user-mfa-enabled | All IAM users have MFA | FAILING (detected) |
| iam-password-policy | Strong password policy enforced | PASSING |
| iam-no-inline-policies | No inline policies exist | PASSING |
| access-keys-rotated | No access keys older than 90 days | PASSING |
| root-account-mfa-enabled | Root account has MFA | FAILING (detected) |

The two failing rules represent real security gaps detected by the 
system. Both failures are MFA related: MFA is not enabled on IAM 
users or the root account.
In a production environment these would trigger alerts to the 
security team as this could lead to a potential breach in company resources and security.

![Config Rules](screenshots/phase4-compliance/Config%20Rules.png)
![Config Dashboard](screenshots/phase4-compliance/AWS%20Config%20Dashboard.png)
![Audit Script Output](screenshots/phase4-compliance/Audit%20script.png)

---

## CI/CD Security Gate (Phase 5)

Every pull request triggers an automated security pipeline that 
blocks merges if any IAM change violates least privilege:

### Pipeline Steps
1. **Terraform Plan**: previews exactly what would change in AWS
2. **Checkov Scan** - static analysis of all Terraform files against 
security best practices
3. **IAM Audit Script**: checks live AWS state for compliance
4. **Violations Check**: hard blocks any policy containing 
AdministratorAccess, PowerUserAccess, or wildcard permissions

### Authentication
Uses OIDC instead of stored AWS credentials. GitHub receives a 
short-lived STS token that expires when the job finishes meaning that there are 
no long-lived credentials stored anywhere.

### Proof It Works
**Bad policy blocked:**

![PR Blocked](screenshots/phase5-pipeline/Pipeline%20failing%20on%20bad%20IAM%20policy%20pull%20request.png)
![PR Comment](screenshots/phase5-pipeline/PR%20comment%20posted%20by%20workflow.png)

**Clean policy passes:**

![PR Passing](screenshots/phase5-pipeline/Pipeline%20passes%20on%20reverted%20code.png)

---

## Weekly Security Reports (Phase 6)

A Python script runs every Monday at 9am via GitHub Actions cron 
and saves a markdown report to S3 covering the full IAM state:

- All IAM users and last login dates
- MFA status per user (HIGH RISK if missing)
- Access key age (MEDIUM RISK if over 90 days)
- Policy violation scan (CRITICAL if wildcards found)
- AWS Config compliance score
- Access Analyzer findings summary

![Weekly Report Terminal](screenshots/phase6-weekly-report/Weekly%20report%20terminal%20output.png)
![Weekly Report S3](screenshots/phase6-weekly-report/weekly%20report%20S3%20bucket.png)

---

## Key Metrics

| Metric | Before | After |
|--------|--------|-------|
| Overpermissioned policies | 4 | 0 |
| AWS Config rules enforced | 0 | 5 |
| Departments with AdministratorAccess | 1 | 0 |
| Wildcard policies | 4 | 0 |
| Automated compliance checks | 0 | Continuous |
| PR pipeline catch time | N/A | Under 2 minutes |

---

## How the CI/CD Gate Works

A developer opens a pull request with an intended IAM change or modification -> 
github actions triggers automatically (continuous integration) ->
OIDC (openIDconnect) authenticates to AWS (STS) so that there are no stored keys ->
terraform plan shows proposed changes ->
checkov scans for IaC misconfigurations ->
python script audits live AWS state ->
violations check scans policy JSON files ->
does it pass ->
Yes = PR green
No = PR blocked

## What I Learned

A GitHub Actions pipeline was created as the continuous integration 
part of CI/CD. This pipeline runs automated security checks on every 
pull request, acting as a barrier that prevents unauthorized or 
misconfigured IAM changes from reaching AWS.

The pipeline uses Checkov for static analysis, scanning Terraform 
files locally without deploying anything to AWS, checking for 
misconfigurations like overly permissive IAM roles or publicly 
accessible S3 buckets. A custom Python violations script runs 
separately to scan policy.json files specifically for dangerous 
permissions like AdministratorAccess, PowerUserAccess, or wildcard 
* permissions. These two tools complement each other: Checkov 
catches broad IaC misconfigurations while the Python script catches 
specific IAM policy violations.

For AWS authentication the pipeline uses OIDC instead of stored 
access keys. The problem with access keys is they live permanently 
in GitHub secrets. If a developer account is compromised or someone 
leaks the keys, an attacker has permanent AWS access. OIDC solves 
this through a cryptographic handshake between GitHub and AWS. When 
a workflow runs, GitHub generates a JWT (JSON Web Token) containing 
cryptographic claims: the issuer, repository owner, repo name, 
branch, and audience. This JWT is sent to AWS STS (Security Token 
Service) which validates the claims against the IAM trust policy. 
If valid, STS issues temporary credentials that expire when the job 
finishes, typically between 15 minutes and 1 hour. No credentials 
are stored anywhere and even if the token was intercepted it would 
be useless after expiry.

For IAM structure, policies are attached to groups rather than 
individual users. Each department group has a custom least privilege 
policy scoped to specific resource ARNs. ARNs are unique addresses 
for every AWS resource. Instead of granting access to all S3 buckets 
with a wildcard, each group gets access to only their specific bucket 
ARN and nothing else. For example the finance group can only read 
from the finance-reports S3 bucket and query the finance-db DynamoDB 
table.

Two services run continuously in the background to monitor the live 
AWS environment independent of the pipeline. AWS Config runs 5 
compliance rules that watch internal account settings, checking 
things like whether IAM users have MFA enabled, whether access keys 
are older than 90 days, and whether the password policy meets 
requirements. It is asking "are your internal settings configured 
correctly?" IAM Access Analyzer watches the boundary between the 
account and the outside world, checking whether any S3 bucket is 
publicly accessible, whether any IAM role can be assumed by a 
different AWS account, or whether any resource is leaking outside 
the account boundary. It is asking "is anything exposed to the 
outside?" These two services catch different things: Config catches 
internal misconfigurations while Access Analyzer catches external 
exposure. The GitHub Actions pipeline catches bad code before it 
reaches AWS, Config catches bad changes made directly in the console 
that bypassed the pipeline, and Access Analyzer catches anything 
leaking outside the account entirely. Together they cover every 
attack surface. A weekly Python script using boto3 pulls findings 
from both services and generates a markdown report saved to S3 
every Monday at 9am via a GitHub Actions cron job, covering MFA 
status, access key age, policy violations, Config compliance score, 
and Access Analyzer findings.

At the enterprise level, SCPs (Service Control Policies) at the AWS 
Organizations level define hard guardrails that cannot be overridden 
by any IAM policy, not even AdministratorAccess or the root account. 
The root account itself should never be used for day to day 
operations. It uses a hardware physical token for MFA instead of a 
phone app, has a long randomly generated password stored in a company 
safe, has no access keys created, and CloudTrail alerts fire 
immediately if it ever logs in.

S3 (Simple Storage Service) is AWS cloud object storage used 
throughout this project for Config logs, weekly reports, and 
optionally Terraform remote state. DynamoDB locking prevents 
concurrent Terraform applies. When one user runs terraform apply it 
writes a lock to DynamoDB that blocks any other apply from running 
simultaneously, preventing race conditions and state corruption.


---


## Currently Implementing

- **Remote Terraform state**: moving terraform.tfstate from local 
machine to an S3 bucket with DynamoDB locking, making Terraform 
applies team-safe and creating a full audit trail of every 
infrastructure change
- **Pipeline as the only deploy path**: removing local write access 
so terraform apply can only be executed through the GitHub Actions 
pipeline, making the security gate impossible to bypass
- **AWS Organizations SCPs**: adding hard account-level guardrails 
that block IAM write actions from any identity except the approved 
pipeline role, enforcing this even against AdministratorAccess
- **IAM Identity Center**: replacing permanent IAM users with SSO 
based authentication so human users never hold long-lived credentials
- **CloudTrail + EventBridge + Lambda**: automated incident response 
that triggers on security events like root login, MFA disabled, or 
new access key created, firing alerts and automatic containment 
responses
- **GuardDuty**: ML-based threat detection monitoring for anomalous 
API calls, unusual data access patterns, and known malicious activity 
across the account
- **Permission boundaries**: hard ceilings on what any IAM role can 
do regardless of what policies are attached, preventing privilege 
escalation even if a role is misconfigured


## Project Structure
iam-least-privilege-audit/
├── main.tf                          # Root Terraform - all AWS resources
├── variables.tf                     # Region and naming variables
├── outputs.tf                       # Resource ARN outputs
├── audit.py                         # Config compliance report script
├── weekly_report.py                 # Weekly IAM security report
├── architecture.png                 # System architecture diagram
├── modules/
│   ├── engineering/
│   │   ├── main.tf                  # Engineering users, group, policy
│   │   └── policy.json              # Least privilege policy JSON
│   ├── finance/
│   │   ├── main.tf
│   │   └── policy.json
│   ├── hr/
│   │   ├── main.tf
│   │   └── policy.json
│   └── ops/
│       ├── main.tf
│       └── policy.json
├── .github/
│   └── workflows/
│       ├── iam-audit.yml            # PR security gate
│       └── weekly-report.yml        # Monday cron report
└── screenshots/                     # Before/after documentation

