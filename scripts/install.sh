#!/bin/bash
set -e

echo "🚀 Installing Kubernetes MCP Server (EKS only)..."

# Verificar prerequisites
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Exiting." >&2; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "❌ helm is required but not installed. Exiting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 is required but not installed. Exiting." >&2; exit 1; }

# Crear directorio de trabajo
mkdir -p ~/.local/share/kubernetes-mcp
cd ~/.local/share/kubernetes-mcp

# Instalar dependencias Python
echo "📦 Installing Python dependencies..."
pip3 install --user -r requirements.txt

# Verificar conexión al cluster
echo "🔗 Verifying cluster connection..."
kubectl cluster-info || { echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig." >&2; exit 1; }

# Detectar EKS
if kubectl get nodes -o json | grep -q "eks.amazonaws.com"; then
    PROVIDER="eks"
    echo "✅ Detected EKS cluster"
else
    echo "❌ This tool is intended for EKS clusters only. Exiting."
    exit 1
fi

# Crear configuración del cluster
export CLUSTER_NAME=$(kubectl config current-context)
export CLUSTER_PROVIDER=$PROVIDER
export AWS_REGION=${AWS_REGION:-us-west-2}

envsubst < config/cluster_config.yaml > ~/.local/share/kubernetes-mcp/cluster_config.yaml

# Aplicar configuración al cluster
kubectl apply -f ~/.local/share/kubernetes-mcp/cluster_config.yaml

# Verificar instalación de Karpenter
echo "🔍 Checking Karpenter installation..."
if kubectl get deployment karpenter -n karpenter >/dev/null 2>&1; then
    echo "✅ Karpenter is installed"
else
    echo "⚠️ Karpenter not found. Consider installing it for better autoscaling."
fi

echo "✅ Kubernetes MCP Server installation completed!"
echo "🎯 Run: python3 server.py"