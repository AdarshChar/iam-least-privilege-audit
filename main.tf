terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "engineering" {
  source = "./modules/engineering"
}

module "finance" {
  source = "./modules/finance"
}

module "hr" {
  source = "./modules/hr"
}

module "ops" {
  source = "./modules/ops"
}

# S3 Buckets
resource "aws_s3_bucket" "engineering_data" {
  bucket = "frazycorp-engineering-data-${var.suffix}"
}

resource "aws_s3_bucket" "finance_reports" {
  bucket = "frazycorp-finance-reports-${var.suffix}"
}

resource "aws_s3_bucket" "hr_records" {
  bucket = "frazycorp-hr-records-${var.suffix}"
}

resource "aws_s3_bucket" "ops_logs" {
  bucket = "frazycorp-ops-logs-${var.suffix}"
}

# DynamoDB Tables
resource "aws_dynamodb_table" "engineering_db" {
  name         = "engineering-db"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "finance_db" {
  name         = "finance-db"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "db-password-v2"
}

resource "aws_secretsmanager_secret" "api_key" {
  name = "api-key-v2"
}

# IAM Access Analyzer
resource "aws_accessanalyzer_analyzer" "frazycorp" {
  analyzer_name = "frazycorp-analyzer"
  type          = "ACCOUNT"
}

# Password Policy
resource "aws_iam_account_password_policy" "strict" {
  minimum_password_length        = 14
  require_uppercase_characters   = true
  require_lowercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  allow_users_to_change_password = true
  max_password_age               = 90
  password_reuse_prevention      = 10
}

# S3 bucket for Config logs
resource "aws_s3_bucket" "config_logs" {
  bucket = "frazycorp-config-logs-${var.suffix}"
  force_destroy = true
}

# IAM role for Config
resource "aws_iam_role" "config_role" {
  name = "frazycorp-config-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "config_policy" {
  role       = aws_iam_role.config_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

resource "aws_s3_bucket_policy" "config_logs" {
  bucket = aws_s3_bucket.config_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSConfigBucketPermissionsCheck"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.config_logs.arn
      },
      {
        Sid    = "AWSConfigBucketDelivery"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.config_logs.arn}/AWSLogs/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

# Config Recorder
resource "aws_config_configuration_recorder" "frazycorp" {
  name     = "frazycorp-recorder"
  role_arn = aws_iam_role.config_role.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

# Config Delivery Channel
resource "aws_config_delivery_channel" "frazycorp" {
  name           = "frazycorp-delivery"
  s3_bucket_name = aws_s3_bucket.config_logs.bucket

  depends_on = [aws_config_configuration_recorder.frazycorp]
}

# Start the recorder
resource "aws_config_configuration_recorder_status" "frazycorp" {
  name       = aws_config_configuration_recorder.frazycorp.name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.frazycorp]
}

# Config Rules
resource "aws_config_config_rule" "mfa_enabled" {
  name = "iam-user-mfa-enabled"

  source {
    owner             = "AWS"
    source_identifier = "IAM_USER_MFA_ENABLED"
  }

  depends_on = [aws_config_configuration_recorder_status.frazycorp]
}

resource "aws_config_config_rule" "password_policy" {
  name = "iam-password-policy"

  source {
    owner             = "AWS"
    source_identifier = "IAM_PASSWORD_POLICY"
  }

  depends_on = [aws_config_configuration_recorder_status.frazycorp]
}

resource "aws_config_config_rule" "no_inline_policies" {
  name = "iam-no-inline-policies"

  source {
    owner             = "AWS"
    source_identifier = "IAM_NO_INLINE_POLICY_CHECK"
  }

  depends_on = [aws_config_configuration_recorder_status.frazycorp]
}

resource "aws_config_config_rule" "access_keys_rotated" {
  name = "access-keys-rotated"

  source {
    owner             = "AWS"
    source_identifier = "ACCESS_KEYS_ROTATED"
  }

  input_parameters = jsonencode({
    maxAccessKeyAge = "90"
  })

  depends_on = [aws_config_configuration_recorder_status.frazycorp]
}

resource "aws_config_config_rule" "root_mfa" {
  name = "root-account-mfa-enabled"

  source {
    owner             = "AWS"
    source_identifier = "ROOT_ACCOUNT_MFA_ENABLED"
  }

  depends_on = [aws_config_configuration_recorder_status.frazycorp]
}