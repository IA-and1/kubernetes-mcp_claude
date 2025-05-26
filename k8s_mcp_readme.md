# Kubernetes MCP Server 🚀

Un servidor MCP (Model Context Protocol) completo para monitoreo, análisis y gestión de clusters Kubernetes. Diseñado específicamente para EKS pero compatible con cualquier proveedor de Kubernetes.

## ✨ Características Principales

- 🏥 **Análisis Integral de Salud**: Monitoreo completo de nodos, pods y recursos
- 📊 **Métricas en Tiempo Real**: CPU, memoria, y estado de componentes
- 🎯 **Soporte Multi-Proveedor**: EKS, GKE, AKS y Kubernetes genérico
- 🚀 **Análisis de Karpenter**: Monitoreo de autoescalado y provisioning
- 🔄 **Integración ArgoCD**: Estado de aplicaciones y sincronización
- 📋 **Reportes Detallados**: Markdown, JSON, YAML formats
- 🛠️ **Corrección Automática**: Generación de manifests para solucionar problemas
- ⚙️ **kubectl/helm Integration**: Ejecución de comandos nativos

## 🛠️ Herramientas Disponibles

| Herramienta | Descripción | Casos de Uso |
|-------------|-------------|--------------|
| `cluster_health_check` | Análisis integral de salud | Monitoreo general, alertas |
| `get_nodes_status` | Estado detallado de nodos | Troubleshooting, capacity planning |
| `get_pods_status` | Información de pods | Debugging, resource monitoring |
| `kubectl_query` | Comandos kubectl nativos | Consultas personalizadas |
| `helm_query` | Comandos helm nativos | Gestión de releases |
| `analyze_karpenter` | Análisis de Karpenter | Autoescalado, provisioning |
| `get_argocd_status` | Estado de ArgoCD | GitOps, deployments |
| `generate_health_report` | Reportes completos | Documentación, auditorías |
| `create_resource_fixes` | Manifests de corrección | Resolución de problemas |

## 🚀 Instalación Rápida

```bash
# 1. Clonar o descargar los archivos
git clone <repository> && cd kubernetes-mcp

# 2. Ejecutar setup automático
chmod +x setup.sh
./setup.sh

# 3. Activar el entorno
source k8s-mcp-env/bin/activate

# 4. Iniciar el servidor
python kubernetes_mcp_server.py
```

## 📋 Prerequisitos

### Obligatorios
- **Python 3.8+**
- **kubectl** configurado y con acceso al cluster
- **Kubernetes cluster** (EKS, GKE, AKS, o cualquier otro)

### Opcionales (para funcionalidad completa)
- **helm** - Para gestión de charts
- **metrics-server** - Para métricas de recursos
- **Karpenter** - Para análisis de autoescalado
- **ArgoCD** - Para estado de GitOps

## 🔧 Configuración

### 1. Configuración Básica
```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "python",
      "args": ["kubernetes_mcp_server.py"],
      "env": {
        "KUBECONFIG": "~/.kube/config"
      }
    }
  }
}
```

### 2. Variables de Entorno
```bash
export KUBECONFIG=~/.kube/config
export K8S_MCP_LOG_LEVEL=INFO
export K8S_MCP_TIMEOUT=30
```

## 💡 Ejemplos de Uso

### Verificación Rápida de Salud
```python
# Usando el MCP client
response = await client.call_tool("cluster_health_check", {
    "include_recommendations": True
})
```

### Generar Reporte Completo
```python
report = await client.call_tool("generate_health_report", {
    "format": "markdown",
    "include_recommendations": True
})
```

### Análisis de Karpenter
```python
karpenter_status = await client.call_tool("analyze_karpenter", {})
```

### Crear Fixes de Recursos
```python
fixes = await client.call_tool("create_resource_fixes", {
    "issue_type": "resource_limits",
    "target": "my-deployment",
    "namespace": "production"
})
```

## 📊 Tipos de Análisis

### 🏥 Health Analysis
- Estado general del cluster
- Conteo de nodos saludables/no saludables
- Estado de pods (running, pending, failed)
- Identificación de issues críticos
- Recomendaciones automatizadas

### 📈 Resource Monitoring
- Utilización de CPU/memoria por nodo
- Métricas de pods individuales
- Detección de recursos sobrecargados
- Análisis de capacity planning

### 🚀 Karpenter Analysis
- Estado de instalación y versión
- Configuración de NodePools
- Nodos provisionados automáticamente
- Límites y restricciones configuradas

### 🔄 ArgoCD Integration
- Estado de aplicaciones GitOps
- Sincronización de repositorios
- Health status de deployments
- Aplicaciones fuera de sincronización

## 🛠️ Corrección de Problemas

El MCP puede generar automáticamente manifests para solucionar problemas comunes:

### Resource Limits
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: app-limits
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "512Mi"
    type: Container
```

### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Pod Disruption Budget
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: myapp
```

## 🔍 Monitoreo Proactivo

### Indicadores Críticos
- ❌ Nodos no saludables
- 🔴 Pods en estado Failed
- ⚠️ Alta tasa de reinicios
- 📊 Utilización de recursos > 80%