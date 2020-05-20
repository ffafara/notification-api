resource "aws_security_group" "ecs_task_outbound_access" {
  name        = "ecs-task-outbound-access-security-group"
  description = "allow outbound access"
  vpc_id      = data.aws_vpc.notification.id
  tags        = var.default_tags

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "notification_db_access" {
  name_prefix = "notification-db-access-"
  description = "For access to the Notification Database"
  vpc_id      = data.aws_vpc.notification.id
}