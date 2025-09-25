variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "agents-on-eks"
}


variable "mem0_api_key" {
  description = "API key for Mem0 external memory service"
  type        = string
  sensitive   = true
  default     = ""  # Default to empty string to make it optional
}

variable "enable_langfuse" {
  description = "Enable LangFuse observability platform"
  type        = bool
  default     = false
}

variable "enable_langfuse_persistence" {
  description = "Enable persistence for LangFuse (requires EBS CSI driver)"
  type        = bool
  default     = false
}

variable "langfuse_service_type" {
  description = "Kubernetes service type for LangFuse (ClusterIP, NodePort, LoadBalancer)"
  type        = string
  default     = "ClusterIP"
}

variable "langfuse_ingress_enabled" {
  description = "Enable ingress for LangFuse"
  type        = bool
  default     = false
}

variable "langfuse_domain" {
  description = "Domain name for LangFuse (if using ingress)"
  type        = string
  default     = ""
}

variable "langfuse_public_key" {
  description = "LangFuse public API key (get from UI after deployment)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "LangFuse secret API key (get from UI after deployment)"
  type        = string
  default     = ""
  sensitive   = true
}

