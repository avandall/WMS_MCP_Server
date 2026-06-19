# Terraform configuration for WMS MCP Server infrastructure

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "wms-mcp-server-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name        = "wms-mcp-server-vpc"
    Environment = var.environment
  }
}

# Subnets
resource "aws_subnet" "public" {
  count             = var.availability_zones_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = {
    Name        = "wms-mcp-server-public-subnet-${count.index}"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  count             = var.availability_zones_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + var.availability_zones_count)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = {
    Name        = "wms-mcp-server-private-subnet-${count.index}"
    Environment = var.environment
  }
}

# Security Groups
resource "aws_security_group" "wms_mcp_server" {
  name_prefix = "wms-mcp-server"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name        = "wms-mcp-server-sg"
    Environment = var.environment
  }
}

# EC2 Instance
resource "aws_instance" "wms_mcp_server" {
  count         = var.instance_count
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.private[count.index % var.availability_zones_count].id
  
  vpc_security_group_ids = [aws_security_group.wms_mcp_server.id]
  
  user_data = <<-EOF
              #!/bin/bash
              cd /home/ubuntu/wms-mcp-server
              git pull origin main
              pip install -r requirements.txt
              systemctl restart wms-mcp-server
              EOF
  
  tags = {
    Name        = "wms-mcp-server-${count.index}"
    Environment = var.environment
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "wms_database" {
  allocated_storage    = var.db_storage
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = var.db_instance_class
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.postgres15"
  skip_final_snapshot  = true
  
  vpc_security_group_ids = [aws_security_group.wms_mcp_server.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  tags = {
    Name        = "wms-mcp-server-database"
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "wms-mcp-server-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  
  tags = {
    Name        = "wms-mcp-server-db-subnet-group"
    Environment = var.environment
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "wms-mcp-server-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "wms-mcp-server-redis"
  replication_group_description = "WMS MCP Server Redis cluster"
  node_type                     = var.redis_node_type
  number_cache_clusters         = var.redis_cluster_count
  subnet_group_name             = aws_elasticache_subnet_group.main.name
  security_group_ids            = [aws_security_group.wms_mcp_server.id]
  
  tags = {
    Name        = "wms-mcp-server-redis"
    Environment = var.environment
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "wms-mcp-server-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  
  dimensions = {
    InstanceId = aws_instance.wms_mcp_server[0].id
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_sns_topic" "alerts" {
  name = "wms-mcp-server-alerts"
}

data "aws_availability_zones" "available" {}
