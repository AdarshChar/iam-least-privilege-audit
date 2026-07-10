output "engineering_bucket" {
  value = aws_s3_bucket.engineering_data.arn
}

output "finance_bucket" {
  value = aws_s3_bucket.finance_reports.arn
}

output "hr_bucket" {
  value = aws_s3_bucket.hr_records.arn
}

output "ops_bucket" {
  value = aws_s3_bucket.ops_logs.arn
}