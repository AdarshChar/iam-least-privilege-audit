import boto3
import json
from datetime import datetime, timezone, timedelta

# Configuration
REPORT_BUCKET = "frazycorp-weekly-reports-2024frazy"
REGION = "us-east-1"

# Initialize clients
iam = boto3.client('iam', region_name=REGION)
config_client = boto3.client('config', region_name=REGION)
analyzer = boto3.client('accessanalyzer', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

def get_all_users():
    users = []
    paginator = iam.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']

            # Get last login
            last_login = user.get('PasswordLastUsed', None)
            if last_login:
                days_since_login = (datetime.now(timezone.utc) - last_login).days
                last_login_str = last_login.strftime('%Y-%m-%d')
            else:
                days_since_login = 999
                last_login_str = "Never logged in"

            # Check MFA
            mfa_devices = iam.list_mfa_devices(UserName=username)
            has_mfa = len(mfa_devices['MFADevices']) > 0

            # Check access keys
            keys = iam.list_access_keys(UserName=username)
            old_keys = []
            for key in keys['AccessKeyMetadata']:
                key_age = (datetime.now(timezone.utc) - key['CreateDate']).days
                if key_age > 90:
                    old_keys.append({
                        'key_id': key['AccessKeyId'],
                        'age_days': key_age
                    })

            users.append({
                'username': username,
                'last_login': last_login_str,
                'days_since_login': days_since_login,
                'has_mfa': has_mfa,
                'old_keys': old_keys,
                'risk_flags': []
            })

    return users

def get_all_groups():
    groups = []
    paginator = iam.get_paginator('list_groups')
    for page in paginator.paginate():
        for group in page['Groups']:
            group_name = group['GroupName']

            attached = iam.list_attached_group_policies(GroupName=group_name)
            policies = [p['PolicyName'] for p in attached['AttachedPolicies']]

            members = iam.get_group(GroupName=group_name)
            member_names = [u['UserName'] for u in members['Users']]

            groups.append({
                'name': group_name,
                'policies': policies,
                'members': member_names
            })

    return groups

def check_policy_violations():
    violations = []
    paginator = iam.get_paginator('list_policies')
    for page in paginator.paginate(Scope='Local'):
        for policy in page['Policies']:
            policy_version = iam.get_policy_version(
                PolicyArn=policy['Arn'],
                VersionId=policy['DefaultVersionId']
            )

            document = policy_version['PolicyVersion']['Document']
            policy_str = json.dumps(document)

            if '"*"' in policy_str:
                violations.append({
                    'policy': policy['PolicyName'],
                    'severity': 'CRITICAL',
                    'reason': 'Contains wildcard * permission'
                })

            for dangerous in ['AdministratorAccess', 'PowerUserAccess']:
                if dangerous in policy_str:
                    violations.append({
                        'policy': policy['PolicyName'],
                        'severity': 'CRITICAL',
                        'reason': f'References {dangerous}'
                    })

    return violations

def get_config_compliance():
    rules = [
        'iam-user-mfa-enabled',
        'iam-password-policy',
        'iam-no-inline-policies',
        'access-keys-rotated',
        'root-account-mfa-enabled'
    ]

    passing = []
    failing = []

    for rule in rules:
        try:
            response = config_client.describe_compliance_by_config_rule(
                ConfigRuleNames=[rule]
            )
            for compliance in response['ComplianceByConfigRules']:
                status = compliance['Compliance']['ComplianceType']
                if status == 'COMPLIANT':
                    passing.append(rule)
                else:
                    failing.append(rule)
        except Exception as e:
            failing.append(f"{rule} (ERROR: {str(e)})")

    return passing, failing

def get_analyzer_findings():
    try:
        analyzers = analyzer.list_analyzers()
        if not analyzers['analyzers']:
            return []
        analyzer_arn = analyzers['analyzers'][0]['arn']
        findings = analyzer.list_findings(analyzerArn=analyzer_arn)
        return findings.get('findings', [])
    except Exception as e:
        return []

def flag_risks(users):
    for user in users:
        if not user['has_mfa']:
            user['risk_flags'].append('HIGH RISK: No MFA enabled')
        if user['old_keys']:
            user['risk_flags'].append('MEDIUM RISK: Access key older than 90 days')
        if user['days_since_login'] > 90:
            user['risk_flags'].append(
                f"MEDIUM RISK: No login in {user['days_since_login']} days"
            )
    return users

def generate_markdown_report(users, groups, violations, passing, failing, findings):
    now = datetime.now(timezone.utc)

    report = f"""# FrazyCorp Weekly IAM Security Report
Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total IAM Users | {len(users)} |
| Users Without MFA | {len([u for u in users if not u['has_mfa']])} |
| Config Rules Passing | {len(passing)} of {len(passing) + len(failing)} |
| Policy Violations | {len(violations)} |
| Access Analyzer Findings | {len(findings)} |

---

## Config Compliance Score: {len(passing)}/{len(passing) + len(failing)} Rules Passing

### Passing Rules
"""
    for rule in passing:
        report += f"- PASS {rule}\n"

    report += "\n### Failing Rules\n"
    for rule in failing:
        report += f"- FAIL {rule}\n"

    report += "\n---\n\n## IAM Users\n\n"
    report += "| User | Last Login | MFA | Risk Flags |\n"
    report += "|------|------------|-----|------------|\n"

    for user in users:
        mfa_status = "YES" if user['has_mfa'] else "NO"
        flags = ", ".join(user['risk_flags']) if user['risk_flags'] else "None"
        report += f"| {user['username']} | {user['last_login']} | {mfa_status} | {flags} |\n"

    report += "\n---\n\n## IAM Groups and Policies\n\n"
    for group in groups:
        report += f"### {group['name']}\n"
        report += f"**Members:** {', '.join(group['members'])}\n\n"
        report += "**Attached Policies:**\n"
        for policy in group['policies']:
            report += f"- {policy}\n"
        report += "\n"

    report += "---\n\n## Policy Violations\n\n"
    if violations:
        for v in violations:
            report += f"- {v['severity']} - {v['policy']}: {v['reason']}\n"
    else:
        report += "No policy violations found\n"

    report += "\n---\n\n## Access Analyzer Findings\n\n"
    if findings:
        report += f"{len(findings)} findings require review\n"
    else:
        report += "No external access findings\n"

    report += "\n---\n*Report automatically generated by FrazyCorp IAM Audit System*"

    return report

def save_report_to_s3(report_content):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f"iam-report-{timestamp}.md"

    s3.put_object(
        Bucket=REPORT_BUCKET,
        Key=f"reports/{filename}",
        Body=report_content.encode('utf-8'),
        ContentType='text/markdown'
    )

    print(f"Report saved to s3://{REPORT_BUCKET}/reports/{filename}")
    return filename

def main():
    print("Generating FrazyCorp Weekly IAM Report...\n")

    print("Fetching IAM users...")
    users = get_all_users()
    users = flag_risks(users)

    print("Fetching IAM groups...")
    groups = get_all_groups()

    print("Checking policy violations...")
    violations = check_policy_violations()

    print("Fetching Config compliance...")
    passing, failing = get_config_compliance()

    print("Fetching Access Analyzer findings...")
    findings = get_analyzer_findings()

    print("Generating report...")
    report = generate_markdown_report(
        users, groups, violations, passing, failing, findings
    )

    print("\n" + "="*50)
    print(report)
    print("="*50 + "\n")

    save_report_to_s3(report)

    print("Done!")

if __name__ == "__main__":
    main()