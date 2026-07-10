resource "aws_iam_user" "hr1" {
  name = "hr1"
}

resource "aws_iam_group" "hr" {
  name = "hr"
}

resource "aws_iam_group_membership" "hr" {
  name  = "hr-membership"
  group = aws_iam_group.hr.name
  users = [aws_iam_user.hr1.name]
}

resource "aws_iam_policy" "hr_policy" {
  name   = "hr-least-privilege"
  policy = file("${path.module}/policy.json")
}

resource "aws_iam_group_policy_attachment" "hr" {
  group      = aws_iam_group.hr.name
  policy_arn = aws_iam_policy.hr_policy.arn
}