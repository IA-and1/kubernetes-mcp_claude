#!/bin/bash

# Kubernetes MCP Server Setup Script
set -e

echo "🚀 Setting up Kubernetes MCP Server..."

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    echo "   Visit: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    echo "⚠️  helm is not installed. Some features will be limited."
    echo "   To install helm, visit: https://helm.sh/docs/intro/install/"
else
    echo "✅ helm found"
fi

# Check kubectl access
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot access Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

echo "✅ kubectl access confirmed"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo "❌ Python 3.8+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python $python_version found"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv k8s-mcp-env
source k8s-mcp-env/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up configuration
echo "⚙️  Setting up configuration..."

# Create config directory
mkdir -p ~/.config/mcp
cp mcp_config.json ~/.config/mcp/

# Make server executable
chmod +x kubernetes_mcp_server.py

# Detect cluster provider
echo "🔍 Detecting cluster provider..."
if kubectl cluster-info dump --output json 2>/dev/null | grep -q "eks.amazonaws.com"; then
    echo "✅ Detected EKS cluster"
    CLUSTER_PROVIDER="eks"
elif kubectl cluster-info dump --output json 2>/dev/null | grep -q "gke.googleapis.com"; then
    echo "✅ Detected GKE cluster"
    CLUSTER_PROVIDER="gke"
elif kubectl cluster-info dump --output json 2>/dev/null | grep -q "aks.azure.com"; then
    echo "✅ Detected AKS cluster"
    CLUSTER_PROVIDER="aks"
else
    echo "✅ Generic Kubernetes cluster detected"
    CLUSTER_PROVIDER="generic"
fi

# Check for metrics server
echo "📊 Checking for metrics server..."
if kubectl get deployment metrics-server -n kube-system &> /dev/null; then
    echo "✅ Metrics server found"
else
    echo "⚠️  Metrics server not found. Resource metrics will be limited."
    echo "   To install metrics server:"
    echo "   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
fi

# Check for Karpenter
echo "🎯 Checking for Karpenter..."
if kubectl get deployment karpenter -n karpenter &> /dev/null; then
    echo "✅ Karpenter found"
else
    echo "ℹ️  Karpenter not found (optional)"
fi

# Check for ArgoCD
echo "🔄 Checking for ArgoCD..."
if kubectl get namespace argocd &> /dev/null; then
    echo "✅ ArgoCD namespace found"
else
    echo "ℹ️  ArgoCD not found (optional)"
fi

# Create sample health check
echo "🏥 Testing server functionality..."
python3 -c "
import asyncio
import sys
sys.path.append('.')
from kubernetes_mcp_server import KubernetesClient

async def test():
    client = KubernetesClient()
    try:
        health = await client.analyze_cluster_health()
        print(f'✅ Health check successful - Status: {health.overall_status}')
        print(f'   Nodes: {health.node_count} ({health.healthy_nodes} healthy)')
        print(f'   Pods: {health.total_pods} ({health.running_pods} running)')
    except Exception as e:
        print(f'❌ Health check failed: {e}')
        return False
    return True

if not asyncio.run(test()):
    exit(1)
"

echo ""
echo "🎉 Kubernetes MCP Server setup complete!"
echo ""
echo "📋 Setup Summary:"
echo "   • Cluster Provider: $CLUSTER_PROVIDER"
echo "   • kubectl: ✅"
echo "   • helm: $(command -v helm &> /dev/null && echo '✅' || echo '❌')"
echo "   • Metrics Server: $(kubectl get deployment metrics-server -n kube-system &> /dev/null && echo '✅' || echo '❌')"
echo "   • Karpenter: $(kubectl get deployment karpenter -n karpenter &> /dev/null && echo '✅' || echo '❌')"
echo "   • ArgoCD: $(kubectl get namespace argocd &> /dev/null && echo '✅' || echo '❌')"
echo ""
echo "🚀 To start the server:"
echo "   source k8s-mcp-env/bin/activate"
echo "   python kubernetes_mcp_server.py"
echo ""
echo "📖 Available tools:"
echo "   • cluster_health_check - Comprehensive health analysis"
echo "   • get_nodes_status - Node information and metrics"
echo "   • get_pods_status - Pod information and metrics"
echo "   • kubectl_query - Execute kubectl commands"
echo "   • helm_query - Execute helm commands"
echo "   • analyze_karpenter - Karpenter analysis"
echo "   • get_argocd_status - ArgoCD status"
echo "   • generate_health_report - Generate detailed reports"
echo "   • create_resource_fixes - Generate resource fix manifests"
echo ""
echo "💡 Pro tip: Use 'generate_health_report' for comprehensive cluster analysis!"