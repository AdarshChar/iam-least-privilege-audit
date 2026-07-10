resource "aws_iam_user" "fin1" {
  name = "fin1"
}

resource "aws_iam_user" "fin2" {
  name = "fin2"
}

resource "aws_iam_group" "finance" {
  name = "finance"
}

resource "aws_iam_group_membership" "finance" {
  name  = "finance-membership"
  group = aws_iam_group.finance.name
  users = [
    aws_iam_user.fin1.name,
    aws_iam_user.fin2.name
  ]
}

resource "aws_iam_policy" "finance_policy" {
  name   = "finance-least-privilege"
  policy = file("${path.module}/policy.json")
}

resource "aws_iam_group_policy_attachment" "finance" {
  group      = aws_iam_group.finance.name
  policy_arn = aws_iam_policy.finance_policy.arn
}