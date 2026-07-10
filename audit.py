import boto3
import json
from datetime import datetime

def get_config_compliance():
    client = boto3.client('config', region_name='us-east-1')
    
    rules = [
        'iam-user-mfa-enabled',
        'iam-password-policy',
        'iam-no-inline-policies',
        'access-keys-rotated',
        'root-account-mfa-enabled'
    ]
    
    results = []
    
    for rule in rules:
        try:
            response = client.describe_compliance_by_config_rule(
                ConfigRuleNames=[rule]
            )
            
            for compliance in response['ComplianceByConfigRules']:
                status = compliance['Compliance']['ComplianceType']
                results.append({
                    'rule': rule,
                    'status': status,
                    'flagged': status != 'COMPLIANT'
                })
        except Exception as e:
            results.append({
                'rule': rule,
                'status': 'ERROR',
                'error': str(e),
                'flagged': True
            })
    
    return results

def get_analyzer_findings():
    client = boto3.client('accessanalyzer', region_name='us-east-1')
    
    try:
        analyzers = client.list_analyzers()
        
        if not analyzers['analyzers']:
            return []
        
        analyzer_arn = analyzers['analyzers'][0]['arn']
        
        findings = client.list_findings(
            analyzerArn=analyzer_arn
        )
        
        return findings.get('findings', [])
    
    except Exception as e:
        return [{'error': str(e)}]

def generate_report():
    print("Running FrazyCorp IAM Audit...\n")
    
    config_results = get_config_compliance()
    analyzer_findings = get_analyzer_findings()
    
    passing = [r for r in config_results if not r['flagged']]
    failing = [r for r in config_results if r['flagged']]
    
    report = {
        'report_generated': datetime.utcnow().isoformat(),
        'company': 'FrazyCorp',
        'config_compliance': {
            'score': f"{len(passing)} of {len(config_results)} rules passing",
            'passing_rules': passing,
            'failing_rules': failing
        },
        'access_analyzer': {
            'total_findings': len(analyzer_findings),
            'findings': analyzer_findings
        }
    }
    
    # Save report to file
    filename = f"audit-report-{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary to terminal
    print(f"Config Compliance Score: {report['config_compliance']['score']}")
    print(f"\nPassing Rules:")
    for r in passing:
        print(f"  passed {r['rule']}")
    
    print(f"\nFailing Rules:")
    for r in failing:
        print(f"  failed {r['rule']} — {r['status']}")
    
    print(f"\nAccess Analyzer Findings: {len(analyzer_findings)}")
    print(f"\nFull report saved to: {filename}")
    
    return report

if __name__ == "__main__":
    generate_report()