resource "aws_iam_user" "ops1" {
  name = "ops1"
}

resource "aws_iam_group" "operations" {
  name = "operations"
}

resource "aws_iam_group_membership" "ops" {
  name  = "ops-membership"
  group = aws_iam_group.operations.name
  users = [aws_iam_user.ops1.name]
}

resource "aws_iam_policy" "ops_policy" {
  name   = "ops-least-privilege"
  policy = file("${path.module}/policy.json")
}

resource "aws_iam_group_policy_attachment" "ops" {
  group      = aws_iam_group.operations.name
  policy_arn = aws_iam_policy.ops_policy.arn
}