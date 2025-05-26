#!/bin/bash

echo "🏥 Kubernetes Cluster Health Check"
echo "=================================="

# Verificar conectividad
echo "🔗 Checking cluster connectivity..."
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Cluster connection: OK"
else
    echo "❌ Cluster connection: FAILED"
    exit 1
fi

# Verificar nodos
echo ""
echo "🖥️ Node Status:"
kubectl get nodes --no-headers | while read line; do
    name=$(echo $line | awk '{print $1}')
    status=$(echo $line | awk '{print $2}')
    if [ "$status" = "Ready" ]; then
        echo "✅ $name: $status"
    else
        echo "❌ $name: $status"
    fi
done

# Verificar pods críticos
echo ""
echo "🚨 Critical Pods Status:"
critical_namespaces=("kube-system" "karpenter" "argocd")

for ns in "${critical_namespaces[@]}"; do
    if kubectl get namespace $ns >/dev/null 2>&1; then
        echo "📦 Namespace: $ns"
        failed_pods=$(kubectl get pods -n $ns --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
        if [ $failed_pods -eq 0 ]; then
            echo "  ✅ All pods running"
        else
            echo "  ❌ $failed_pods pods not running"
            kubectl get pods -n $ns --field-selector=status.phase!=Running --no-headers 2>/dev/null | while read pod_line; do
                pod_name=$(echo $pod_line | awk '{print $1}')
                pod_status=$(echo $pod_line | awk '{print $3}')
                echo "    ⚠️ $pod_name: $pod_status"
            done
        fi
    fi
done

# Verificar recursos
echo ""
echo "📊 Resource Usage:"
if kubectl top nodes >/dev/null 2>&1; then
    kubectl top nodes
else
    echo "⚠️ Metrics server not available"
fi

# Verificar eventos recientes
echo ""
echo "📅 Recent Events (last 10):"
kubectl get events --all-namespaces --sort-by='.lastTimestamp' --field-selector type=Warning | tail -10

echo ""
echo "🎯 Health check completed!"