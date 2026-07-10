resource "aws_iam_user" "dev1" {
  name = "dev1"
}

resource "aws_iam_user" "dev2" {
  name = "dev2"
}

resource "aws_iam_group" "engineering" {
  name = "engineering"
}

resource "aws_iam_group_membership" "engineering" {
  name  = "engineering-membership"
  group = aws_iam_group.engineering.name
  users = [
    aws_iam_user.dev1.name,
    aws_iam_user.dev2.name
  ]
}

resource "aws_iam_policy" "engineering_policy" {
  name   = "engineering-least-privilege"
  policy = file("${path.module}/policy.json")
}

resource "aws_iam_group_policy_attachment" "engineering" {
  group      = aws_iam_group.engineering.name
  policy_arn = aws_iam_policy.engineering_policy.arn
}