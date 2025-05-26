# Configuración del MCP Kubernetes Server

## Estructura del proyecto

```
kubernetes-mcp/
├── server.py                 # Servidor MCP principal
├── requirements.txt          # Dependencias Python
├── config/
│   ├── mcp_settings.json    # Configuración MCP
│   └── cluster_config.yaml  # Configuración del cluster
├── scripts/
│   ├── install.sh           # Script de instalación
│   └── health_check.sh      # Script de verificación
├── templates/
│   ├── resource_fixes/      # Plantillas para corrección de recursos
│   └── monitoring/          # Plantillas de monitoreo
└── README.md
```

## requirements.txt

```txt
mcp>=0.9.0
pyyaml>=6.0
kubernetes>=28.1.0
asyncio-subprocess>=0.1.0
```

## config/mcp_settings.json

```json
{
  "mcpVersion": "2024-11-05",
  "capabilities": {
    "tools": {}
  },
  "server": {
    "name": "kubernetes-mcp-server",
    "version": "1.0.0"
  },
  "kubernetes": {
    "defaultNamespace": "default",
    "metricsEnabled": true,
    "providers": {
      "eks": {
        "enabled": true,
        "features": ["karpenter", "load_balancer_controller", "ebs_csi"]
      },
      "gke": {
        "enabled": true,
        "features": ["gke_autopilot", "workload_identity"]
      },
      "aks": {
        "enabled": true,
        "features": ["aks_nodepool_autoscaler"]
      }
    }
  },
  "monitoring": {
    "healthCheckInterval": 300,
    "metricsRetention": "7d",
    "alerting": {
      "enabled": true,
      "thresholds": {
        "cpuUtilization": 80,
        "memoryUtilization": 85,
        "diskUtilization": 90,
        "podRestartCount": 5
      }
    }
  },
  "integrations": {
    "argocd": {
      "enabled": true,
      "namespace": "argocd"
    },
    "karpenter": {
      "enabled": true,
      "namespace": "karpenter"
    },
    "prometheus": {
      "enabled": false,
      "namespace": "monitoring"
    }
  }
}
```

## config/cluster_config.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-cluster-config
  namespace: kube-system
data:
  cluster.yaml: |
    cluster:
      name: "${CLUSTER_NAME}"
      provider: "${CLUSTER_PROVIDER}"
      region: "${AWS_REGION}"
      
    monitoring:
      enabled: true
      namespace: "monitoring"
      
    karpenter:
      enabled: true
      provisioner:
        ttlSecondsAfterEmpty: 30
        requirements:
          - key: "karpenter.sh/capacity-type"
            operator: In
            values: ["spot", "on-demand"]
          - key: "node.kubernetes.io/instance-type"
            operator: In
            values: ["m5.large", "m5.xlarge", "m5.2xlarge"]
            
    argocd:
      enabled: true
      namespace: "argocd"
      server: "https://argocd.${CLUSTER_NAME}.local"
      
    github_actions:
      runners:
        namespace: "github-runner"
        replicas: 3
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

## scripts/install.sh

```bash
#!/bin/bash
set -e

echo "🚀 Installing Kubernetes MCP Server..."

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

# Detectar provider del cluster
PROVIDER="generic"
if kubectl get nodes -o json | grep -q "eks.amazonaws.com"; then
    PROVIDER="eks"
    echo "✅ Detected EKS cluster"
elif kubectl get nodes -o json | grep -q "gke.googleapis.com"; then
    PROVIDER="gke"
    echo "✅ Detected GKE cluster"
elif kubectl get nodes -o json | grep -q "aks.azure.com"; then
    PROVIDER="aks"
    echo "✅ Detected AKS cluster"
else
    echo "ℹ️ Generic Kubernetes cluster detected"
fi

# Crear configuración del cluster
export CLUSTER_NAME=$(kubectl config current-context)
export CLUSTER_PROVIDER=$PROVIDER
export AWS_REGION=${AWS_REGION:-us-west-2}

envsubst < config/cluster_config.yaml > ~/.local/share/kubernetes-mcp/cluster_config.yaml

# Aplicar configuración al cluster
kubectl apply -f ~/.local/share/kubernetes-mcp/cluster_config.yaml

# Verificar instalación de Karpenter si es EKS
if [ "$PROVIDER" = "eks" ]; then
    echo "🔍 Checking Karpenter installation..."
    if kubectl get deployment karpenter -n karpenter >/dev/null 2>&1; then
        echo "✅ Karpenter is installed"
    else
        echo "⚠️ Karpenter not found. Consider installing it for better autoscaling."
    fi
fi

# Verificar instalación de ArgoCD
echo "🔍 Checking ArgoCD installation..."
if kubectl get namespace argocd >/dev/null 2>&1; then
    echo "✅ ArgoCD namespace found"
else
    echo "⚠️ ArgoCD not found. Install it if you want GitOps monitoring."
fi

echo "✅ Kubernetes MCP Server installation completed!"
echo "🎯 Run: python3 server.py"
```

## scripts/health_check.sh

```bash
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
```

## Plantillas de recursos

### templates/resource_fixes/network_policy.yaml

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Name }}-netpol
  namespace: {{ .Namespace }}
spec:
  podSelector:
    matchLabels:
      app: {{ .Name }}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          access: {{ .Name }}
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### templates/monitoring/service_monitor.yaml

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ .Name }}-monitor
  namespace: {{ .Namespace }}
  labels:
    app: {{ .Name }}
spec:
  selector:
    matchLabels:
      app: {{ .Name }}
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
    honorLabels: true
```

## Uso del MCP Server

### 1. Configurar Claude Desktop

Agregar al archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "python3",
      "args": ["/path/to/kubernetes-mcp/server.py"],
      "env": {
        "KUBECONFIG": "/path/to/your/kubeconfig"
      }
    }
  }
}
```

### 2. Comandos disponibles

- **cluster_health_check**: Análisis completo de salud del cluster
- **get_nodes_status**: Estado detallado de los nodos
- **get_pods_status**: Estado de pods (por namespace o todos)
- **kubectl_query**: Ejecutar comandos kubectl personalizados
- **helm_query**: Ejecutar comandos helm
- **analyze_karpenter**: Análisis de Karpenter (si está instalado)
- **get_argocd_status**: Estado de aplicaciones ArgoCD
- **generate_health_report**: Generar reportes completos (Markdown/JSON/YAML)
- **create_resource_fixes**: Generar manifiestos para corregir problemas

### 3. Ejemplos de uso

```bash
# Verificar salud del cluster
python3 server.py cluster_health_check

# Obtener estado de pods en namespace específico
python3 server.py get_pods_status --namespace=production

# Generar reporte completo
python3 server.py generate_health_report --format=markdown

# Crear fix para límites de recursos
python3 server.py create_resource_fixes --issue_type=resource_limits --target=my-app --namespace=default
```

### 4. Integración con GitHub Actions

Ejemplo de workflow para monitoreo continuo:

```yaml
name: Kubernetes Health Check
on:
  schedule:
    - cron: '0 */6 * * *'  # Cada 6 horas
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Configure kubectl
      uses: azure/k8s-set-context@v1
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG }}
    - name: Run health check
      run: |
        python3 server.py generate_health_report --format=markdown > health-report.md
    - name: Upload report
      uses: actions/upload-artifact@v3
      with:
        name: health-report
        path: health-report.md
```

## Características principales

✅ **Multi-proveedor**: Compatible con EKS, GKE, AKS y clusters genéricos
✅ **Análisis completo**: Nodos, pods, recursos, métricas
✅ **Karpenter**: Análisis específico del autoscaler
✅ **ArgoCD**: Monitoreo de aplicaciones GitOps  
✅ **Reportes**: Generación automática en múltiples formatos
✅ **Corrección automática**: Generación de manifiestos para solucionar problemas
✅ **GitHub Actions**: Integración para CI/CD
✅ **Escalable**: Fácil extensión para nuevas funcionalidades