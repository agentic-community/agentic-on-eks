# ---------------------------------------------------------------
# LangFuse Observability Platform - Minimal Installation
# Based on official example: https://github.com/langfuse/langfuse-k8s/tree/main/examples/minimal-installation
# ---------------------------------------------------------------

# Create namespace for LangFuse
resource "kubernetes_namespace" "langfuse" {
  count = var.enable_langfuse ? 1 : 0

  metadata {
    name = "langfuse"
  }
  depends_on = [module.eks]
}

# Generate secure random passwords and secrets
resource "random_password" "langfuse_salt" {
  count   = var.enable_langfuse ? 1 : 0
  length  = 64
  special = false  # Disable special characters for compatibility
}

resource "random_id" "langfuse_encryption_key" {
  count       = var.enable_langfuse ? 1 : 0
  byte_length = 32
}

resource "random_password" "langfuse_nextauth_secret" {
  count   = var.enable_langfuse ? 1 : 0
  length  = 64
  special = false  # Disable special characters for compatibility
}

resource "random_password" "langfuse_postgresql" {
  count   = var.enable_langfuse ? 1 : 0
  length  = 32
  special = false  # Disable special characters for compatibility
}

resource "random_password" "langfuse_clickhouse" {
  count   = var.enable_langfuse ? 1 : 0
  length  = 32
  special = false  # Disable special characters to avoid XML parsing issues
}

resource "random_password" "langfuse_redis" {
  count   = var.enable_langfuse ? 1 : 0
  length  = 32
  special = false  # Disable special characters for compatibility
}

resource "random_password" "langfuse_s3_password" {
  count   = var.enable_langfuse ? 1 : 0
  length  = 32
  special = false  # Disable special characters for compatibility
}

# Create the main secret with all credentials (following official example)
resource "kubernetes_secret" "langfuse_main" {
  count = var.enable_langfuse ? 1 : 0

  metadata {
    name      = "langfuse"
    namespace = kubernetes_namespace.langfuse[0].metadata[0].name
  }

  data = {
    salt                 = random_password.langfuse_salt[0].result
    "encryption-key"     = random_id.langfuse_encryption_key[0].hex
    "nextauth-secret"    = random_password.langfuse_nextauth_secret[0].result
    "postgresql-password" = random_password.langfuse_postgresql[0].result
    "clickhouse-password" = random_password.langfuse_clickhouse[0].result
    "redis-password"     = random_password.langfuse_redis[0].result
    "s3-user"           = "minio"
    "s3-password"       = random_password.langfuse_s3_password[0].result
  }

  type = "Opaque"
  depends_on = [kubernetes_namespace.langfuse]
}

# LangFuse Helm Release - Following official minimal example
resource "helm_release" "langfuse" {
  count = var.enable_langfuse ? 1 : 0

  name       = "langfuse"
  repository = "https://langfuse.github.io/langfuse-k8s"
  chart      = "langfuse"
  namespace  = kubernetes_namespace.langfuse[0].metadata[0].name
  version    = "1.5.4"

  wait    = false  # Don't wait - let pods come up gradually
  timeout = 900    # 15 minutes

  values = [
    yamlencode({
      langfuse = {
        # Use secrets from the Kubernetes secret
        encryptionKey = {
          secretKeyRef = {
            name = "langfuse"
            key  = "encryption-key"
          }
        }

        salt = {
          secretKeyRef = {
            name = "langfuse"
            key  = "salt"
          }
        }

        nextauth = {
          secret = {
            secretKeyRef = {
              name = "langfuse"
              key  = "nextauth-secret"
            }
          }
        }

        # Additional environment variables for minimal setup
        env = [
          {
            name  = "NEXTAUTH_URL"
            value = "http://localhost:3000"  # For port-forwarding
          },
          {
            name  = "TELEMETRY_ENABLED"
            value = "false"
          },
          {
            name  = "LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES"
            value = "false"
          }
        ]

        # Minimal resources
        resources = {
          requests = {
            cpu    = "100m"
            memory = "256Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "1Gi"
          }
        }
      }

      # PostgreSQL configuration
      postgresql = {
        auth = {
          existingSecret = "langfuse"
          secretKeys = {
            adminPasswordKey = "postgresql-password"
            userPasswordKey  = "postgresql-password"
          }
        }
        primary = {
          persistence = {
            enabled      = var.enable_langfuse_persistence
            storageClass = "gp2"
            size         = "5Gi"
          }
          resources = {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "1Gi"
            }
          }
        }
      }

      # ClickHouse configuration (required by LangFuse)
      clickhouse = {
        auth = {
          existingSecret    = "langfuse"
          existingSecretKey = "clickhouse-password"
        }
        shards           = 1
        replicasPerShard = 1
        persistence = {
          enabled      = true
          storageClass = "gp2"
          size         = "2Gi"
        }
        # Disable clustering to simplify configuration and avoid XML issues
        clustering = {
          enabled = false
        }
        # Simplified Zookeeper config
        zookeeper = {
          enabled      = true
          replicaCount = 1
          persistence = {
            enabled      = true
            storageClass = "gp2"
            size         = "1Gi"
          }
        }
        resources = {
          requests = {
            cpu    = "100m"
            memory = "512Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "2Gi"
          }
        }
        # Simplified configuration to avoid XML parsing issues
        configurationOverrides = {}
        usersConfigurationOverrides = {}
      }

      # Redis configuration (required by LangFuse)
      redis = {
        auth = {
          existingSecret             = "langfuse"
          existingSecretPasswordKey = "redis-password"
        }
        architecture = "standalone"  # Use standalone instead of master-replica
        primary = {  # Use 'primary' instead of 'master' for Redis chart
          persistence = {
            enabled      = true
            storageClass = "gp2"
            size         = "1Gi"
          }
          resources = {
            requests = {
              cpu    = "50m"
              memory = "128Mi"
            }
            limits = {
              cpu    = "250m"
              memory = "512Mi"
            }
          }
        }
        replica = {
          replicaCount = 0  # No replicas for minimal setup
        }
      }

      # S3 (MinIO) configuration (required by LangFuse)
      s3 = {
        auth = {
          existingSecret       = "langfuse"
          rootUserSecretKey    = "s3-user"
          rootPasswordSecretKey = "s3-password"
        }
        persistence = {
          enabled      = true  # Must be enabled
          storageClass = "gp2"
          size         = "2Gi"  # Minimal size
        }
        resources = {
          requests = {
            cpu    = "100m"
            memory = "256Mi"
          }
          limits = {
            cpu    = "250m"
            memory = "512Mi"
          }
        }
      }

      # Service configuration
      service = {
        type = "ClusterIP"  # For port-forwarding
        port = 3000
      }

      # Disable ingress - using port-forwarding instead
      ingress = {
        enabled = false
      }
    })
  ]

  depends_on = [
    kubernetes_namespace.langfuse,
    kubernetes_secret.langfuse_main
  ]
}

# Create Kubernetes secret for LangFuse API credentials (for agents)
resource "kubernetes_secret" "langfuse_credentials" {
  count = var.enable_langfuse ? 1 : 0

  metadata {
    name      = "langfuse-credentials"
    namespace = "default"
  }

  data = {
    # These will be the actual API keys after LangFuse is deployed
    # You'll need to get these from the LangFuse UI after first deployment
    # Placeholders are used initially - replace via terraform.tfvars after getting real keys
    LANGFUSE_PUBLIC_KEY = var.langfuse_public_key != "" ? var.langfuse_public_key : "pk-lf-placeholder-replace-me"
    LANGFUSE_SECRET_KEY = var.langfuse_secret_key != "" ? var.langfuse_secret_key : "sk-lf-placeholder-replace-me"
    LANGFUSE_HOST       = "http://langfuse-web.langfuse.svc.cluster.local:3000"
  }

  type = "Opaque"
  depends_on = [module.eks, helm_release.langfuse]
}