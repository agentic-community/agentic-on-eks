module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.0"
  cluster_name    = var.cluster_name
  cluster_version = "1.31"

  cluster_addons = {
    coredns                = {}
    eks-pod-identity-agent = {}
    kube-proxy             = {}
    vpc-cni                = {}
  }

  # Access entries for cluster access control
  # Note: The cluster creator access entry is automatically created by EKS
  # when authentication_mode is set to API_AND_CONFIG_MAP
  access_entries = {}

  # Enable public access to the Kubernetes API server
  cluster_endpoint_public_access = true
  
  # Configure cluster access for kubectl
  cluster_endpoint_private_access = true
  
  # Ensure the security group allows access to the Kubernetes API
  create_cluster_security_group = true
  create_node_security_group = true

  subnet_ids         = module.vpc.private_subnets
  vpc_id             = module.vpc.vpc_id
  enable_irsa        = true
  

  eks_managed_node_groups = {
    default_nodes = {
      instance_types = ["m5.xlarge"]
      desired_size   = 3
      min_size       = 1
      max_size       = 5
      ami_type       = "BOTTLEROCKET_x86_64"
      
      # Attach additional IAM policies to the node group
      iam_role_additional_policies = {
        AmazonBedrockFullAccess = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        AmazonSSMReadOnlyAccess = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
        BedrockCustomPolicy     = aws_iam_policy.bedrock_policy.arn
      }
    }
    
    gpu_nodes = {
      instance_types = ["g5.8xlarge"]
      desired_size   = 0
      min_size       = 0
      max_size       = 5
      ami_type       = "AL2_x86_64_GPU"
      capacity_type  = "ON_DEMAND"
      
      # Add labels to identify GPU nodes
      labels = {
        "node.kubernetes.io/instance-type" = "g5.8xlarge"
        "nvidia.com/gpu"                   = "true"
      }
      
      # Add taints to ensure only GPU workloads are scheduled on these nodes
      taints = {
        gpu = {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
    }
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}

resource "aws_iam_policy" "alb_controller_policy" {
  name   = "${var.cluster_name}-AWSLoadBalancerControllerIAMPolicy"
  policy = file("${path.module}/iam_policy_alb_controller.json")
}

resource "aws_iam_role" "alb_controller_role" {
  name               = "${var.cluster_name}-aws-lbc-sa-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Federated = module.eks.oidc_provider_arn
      },
      Action = "sts:AssumeRoleWithWebIdentity",
      Condition = {
        StringEquals = {
          "${module.eks.oidc_provider}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "alb_controller_attachment" {
  policy_arn = aws_iam_policy.alb_controller_policy.arn
  role       = aws_iam_role.alb_controller_role.name
}

resource "kubernetes_service_account" "alb_controller_sa" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.alb_controller_role.arn
    }
  }
  depends_on = [module.eks]
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.7.1"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "false"
  }

  set {
    name  = "serviceAccount.name"
    value = kubernetes_service_account.alb_controller_sa.metadata[0].name
  }

  set {
    name  = "region"
    value = var.region
  }

  set {
    name  = "vpcId"
    value = module.vpc.vpc_id
  }

  depends_on = [kubernetes_service_account.alb_controller_sa]
}
# Create IAM policy for Bedrock access
resource "aws_iam_policy" "bedrock_policy" {
  name        = "${var.cluster_name}-EKSNodeBedrockPolicy"
  description = "IAM policy for EKS nodes to access AWS Bedrock"
  policy      = file("${path.module}/iam_policy_bedrock.json")
}

# Create Kubernetes secret for Mem0 API key
resource "kubernetes_secret" "mem0_api_key" {
  metadata {
    name      = "mem0-api-key"
    namespace = "default"
  }

  data = {
    API_KEY = var.mem0_api_key
  }

  type = "Opaque"
  depends_on = [module.eks]
}