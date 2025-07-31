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

