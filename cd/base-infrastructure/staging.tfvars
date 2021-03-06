environment_prefix = "staging"

private_cidrs = ["10.0.0.0/26", "10.0.0.64/26"]

public_cidrs = ["10.0.0.128/26", "10.0.0.192/26"]

# keys below are currently the same as the default values to be changed later

deploy_role = "arn:aws:iam::437518843863:role/notification-deploy-role"

admin_principal = "arn:aws:iam::437518843863:role/federated-admin"

vpc_cidr = "10.0.0.0/24"

region = "us-east-2"