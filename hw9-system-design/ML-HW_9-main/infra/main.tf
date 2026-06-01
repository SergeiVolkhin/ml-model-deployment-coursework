###############################################################################
# Terraform-описание локального стенда ML-системы прогноза складских запасов.
#
# Состав: docker-network + контейнеры Postgres (метадата Airflow и MLflow),
# MinIO (S3-совместимое хранилище для чеков и артефактов моделей),
# MLflow tracking + Model Registry, Airflow (webserver и scheduler в одном
# контейнере для простоты dev-стенда).
#
# Бэкенд: локальный terraform.tfstate. Для prod заменить блоком ниже на
# S3 + DynamoDB lock - см. закомментированный пример.
###############################################################################

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }

  # Для prod-конфигурации использовать удалённый backend с блокировкой:
  # backend "s3" {
  #   bucket         = "mlops-tfstate"
  #   key            = "inventory/terraform.tfstate"
  #   region         = "eu-central-1"
  #   dynamodb_table = "mlops-tfstate-lock"
  #   encrypt        = true
  # }
}

provider "docker" {}

###############################################################################
# Переменные.
###############################################################################
variable "project" {
  type        = string
  description = "Префикс имён ресурсов"
  default     = "inventory-ml"
}

variable "postgres_image" {
  type        = string
  description = "Образ Postgres"
  default     = "postgres:15-alpine"
}

variable "minio_image" {
  type        = string
  description = "Образ MinIO"
  default     = "minio/minio:RELEASE.2024-10-13T13-34-11Z"
}

variable "mlflow_image" {
  type        = string
  description = "Образ MLflow tracking сервера"
  default     = "ghcr.io/mlflow/mlflow:v2.18.0"
}

variable "airflow_image" {
  type        = string
  description = "Образ Apache Airflow"
  default     = "apache/airflow:2.10.3-python3.11"
}

variable "postgres_port" {
  type        = number
  description = "Порт Postgres на хосте"
  default     = 5432
}

variable "minio_api_port" {
  type        = number
  description = "Порт S3 API MinIO на хосте"
  default     = 9000
}

variable "minio_console_port" {
  type        = number
  description = "Порт web-консоли MinIO на хосте"
  default     = 9001
}

variable "mlflow_port" {
  type        = number
  description = "Порт MLflow на хосте"
  default     = 5000
}

variable "airflow_port" {
  type        = number
  description = "Порт Airflow webserver на хосте"
  default     = 8080
}

# Секреты ниже: defaults оставлены для запускаемости dev-стенда.
# В prod переопределять через TF_VAR_postgres_password / TF_VAR_minio_root_password
# или *.tfvars-файл вне git (имя в .gitignore). Никогда не коммитить prod-значения.
variable "postgres_password" {
  type        = string
  description = "Пароль суперпользователя Postgres. Dev-only default; в prod задавать через TF_VAR_postgres_password или *.tfvars вне git."
  sensitive   = true
  default     = "airflow"
}

variable "minio_root_user" {
  type        = string
  description = "Логин root MinIO"
  default     = "minio"
}

variable "minio_root_password" {
  type        = string
  description = "Пароль root MinIO. Dev-only default; в prod задавать через TF_VAR_minio_root_password или *.tfvars вне git."
  sensitive   = true
  default     = "minio12345"
}

###############################################################################
# Сеть и общие тома.
###############################################################################
resource "docker_network" "ml_stack" {
  name = "${var.project}-net"
}

resource "docker_volume" "postgres_data" {
  name = "${var.project}-pg-data"
}

resource "docker_volume" "minio_data" {
  name = "${var.project}-minio-data"
}

resource "docker_volume" "mlflow_artifacts" {
  name = "${var.project}-mlflow-artifacts"
}

###############################################################################
# Postgres (метадата Airflow + MLflow backend store).
###############################################################################
resource "docker_image" "postgres" {
  name = var.postgres_image
}

resource "docker_container" "postgres" {
  name     = "${var.project}-postgres"
  image    = docker_image.postgres.image_id
  restart  = "unless-stopped"
  hostname = "postgres"

  networks_advanced {
    name = docker_network.ml_stack.name
  }

  env = [
    "POSTGRES_USER=airflow",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=airflow",
  ]

  ports {
    internal = 5432
    external = var.postgres_port
  }

  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U airflow"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

###############################################################################
# MinIO (S3-совместимое хранилище для чеков и артефактов моделей).
###############################################################################
resource "docker_image" "minio" {
  name = var.minio_image
}

resource "docker_container" "minio" {
  name     = "${var.project}-minio"
  image    = docker_image.minio.image_id
  restart  = "unless-stopped"
  hostname = "minio"
  command  = ["server", "/data", "--console-address", ":9001"]

  networks_advanced {
    name = docker_network.ml_stack.name
  }

  env = [
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}",
  ]

  ports {
    internal = 9000
    external = var.minio_api_port
  }

  ports {
    internal = 9001
    external = var.minio_console_port
  }

  volumes {
    volume_name    = docker_volume.minio_data.name
    container_path = "/data"
  }

  healthcheck {
    test     = ["CMD-SHELL", "curl -fsS http://localhost:9000/minio/health/live || exit 1"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

###############################################################################
# MLflow tracking server.
###############################################################################
resource "docker_image" "mlflow" {
  name = var.mlflow_image
}

resource "docker_container" "mlflow" {
  name     = "${var.project}-mlflow"
  image    = docker_image.mlflow.image_id
  restart  = "unless-stopped"
  hostname = "mlflow"

  networks_advanced {
    name = docker_network.ml_stack.name
  }

  env = [
    "MLFLOW_S3_ENDPOINT_URL=http://minio:9000",
    "AWS_ACCESS_KEY_ID=${var.minio_root_user}",
    "AWS_SECRET_ACCESS_KEY=${var.minio_root_password}",
  ]

  command = [
    "mlflow", "server",
    "--host", "0.0.0.0",
    "--port", "5000",
    "--backend-store-uri", "postgresql://airflow:${var.postgres_password}@postgres:5432/airflow",
    "--default-artifact-root", "s3://mlflow-artifacts",
  ]

  ports {
    internal = 5000
    external = var.mlflow_port
  }

  volumes {
    volume_name    = docker_volume.mlflow_artifacts.name
    container_path = "/mlflow/artifacts"
  }

  depends_on = [
    docker_container.postgres,
    docker_container.minio,
  ]
}

###############################################################################
# Airflow webserver + scheduler в одном контейнере (dev-режим, standalone).
###############################################################################
resource "docker_image" "airflow" {
  name = var.airflow_image
}

resource "docker_container" "airflow" {
  name     = "${var.project}-airflow"
  image    = docker_image.airflow.image_id
  restart  = "unless-stopped"
  hostname = "airflow"
  command  = ["airflow", "standalone"]

  networks_advanced {
    name = docker_network.ml_stack.name
  }

  env = [
    "AIRFLOW__CORE__EXECUTOR=LocalExecutor",
    "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:${var.postgres_password}@postgres:5432/airflow",
    "AIRFLOW__CORE__LOAD_EXAMPLES=False",
    "AIRFLOW__WEBSERVER__EXPOSE_CONFIG=True",
    "MLFLOW_TRACKING_URI=http://mlflow:5000",
    "AWS_ACCESS_KEY_ID=${var.minio_root_user}",
    "AWS_SECRET_ACCESS_KEY=${var.minio_root_password}",
    "AWS_ENDPOINT_URL=http://minio:9000",
  ]

  ports {
    internal = 8080
    external = var.airflow_port
  }

  volumes {
    host_path      = abspath("${path.module}/../dags")
    container_path = "/opt/airflow/dags"
    read_only      = true
  }

  depends_on = [
    docker_container.postgres,
    docker_container.mlflow,
  ]
}

###############################################################################
# Outputs.
###############################################################################
output "airflow_url" {
  value       = "http://localhost:${var.airflow_port}"
  description = "Airflow webserver"
}

output "mlflow_url" {
  value       = "http://localhost:${var.mlflow_port}"
  description = "MLflow tracking UI"
}

output "minio_console_url" {
  value       = "http://localhost:${var.minio_console_port}"
  description = "MinIO web console"
}

output "minio_s3_endpoint" {
  value       = "http://localhost:${var.minio_api_port}"
  description = "MinIO S3-совместимый endpoint"
}
