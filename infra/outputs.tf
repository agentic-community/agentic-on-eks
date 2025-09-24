output "cluster_name" {
  value = module.eks.cluster_id
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the cluster"
  value       = module.eks.cluster_arn
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "configure_kubectl" {
  description = "Configure kubectl: make sure you're logged in with the correct AWS profile and run the following command to update your kubeconfig"
  value       = "aws eks --region ${local.region} update-kubeconfig --name ${module.eks.cluster_name}"
}

output "langfuse_access" {
  description = "Access LangFuse dashboard via port-forward"
  value       = var.enable_langfuse ? "kubectl port-forward -n langfuse svc/langfuse-web 3000:3000" : "LangFuse not enabled"
}

output "langfuse_host" {
  description = "LangFuse internal cluster host"
  value       = var.enable_langfuse ? "http://langfuse-web.langfuse.svc.cluster.local:3000" : "LangFuse not enabled"
}