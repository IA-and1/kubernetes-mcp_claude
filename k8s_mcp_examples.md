# Kubernetes MCP Server - Usage Examples

Este documento proporciona ejemplos prácticos de cómo usar el servidor MCP de Kubernetes para monitoreo y gestión de clusters.

## 🏥 Análisis de Salud del Cluster

### Verificación Básica de Salud
```bash
# Ejemplo de consulta usando el MCP
{
  "tool": "cluster_health_check",
  "arguments": {
    "include_recommendations": true
  }
}
```

**Respuesta esperada:**
```json
{
  "overall_status": "Healthy",
  "node_count": 3,
  "healthy_nodes": 3,
  "unhealthy_nodes": 0,
  "total_pods": 45,
  "running_pods": 43,
  "pending_pods": 1,
  "failed_pods": 1,
  "critical_issues": [],
  "warnings": ["1 pods are pending"],
  "recommendations": ["Check resource constraints and node availability"]
}
```

## 📊 Monitoreo de Nodos

### Obtener Estado de Todos los Nodos
```bash
{
  "tool": "get_nodes_status",
  "arguments": {
    "include_metrics": true
  }
}
```

### Casos de Uso Comunes:
- **Identificar nodos con alta utilización de recursos**
- **Verificar versiones de Kubernetes**
- **Monitorear tipos de instancia en EKS**
- **Detectar nodos en estado NotReady**

## 🐳 Análisis de Pods

### Pods por Namespace
```bash
{
  "tool": "get_pods_status",
  "arguments": {
    "namespace": "production",
    "include_metrics": true
  }
}
```

### Todos los Pods del Cluster
```bash
{
  "tool": "get_pods_status",
  "arguments": {
    "namespace": "all",
    "include_metrics": true
  }
}
```

### Casos de Uso:
- **Detectar pods con muchos reinicios**
- **Identificar pods en estado Failed**
- **Monitorear uso de recursos por pod**
- **Verificar distribución de pods por nodo**

## 🔧 Comandos kubectl Personalizados

### Obtener Servicios
```bash
{
  "tool": "kubectl_query",
  "arguments": {
    "command": "get services --all-namespaces"
  }
}
```

### Verificar Events
```bash
{
  "tool": "kubectl_query",
  "arguments": {
    "command": "get events --sort-by=.metadata.creationTimestamp"
  }
}
```

### Describir un Pod Problemático
```bash
{
  "tool": "kubectl_query",
  "arguments": {
    "command": "describe pod problematic-pod -n production"
  }
}
```

## ⚙️ Helm Operations

### Listar Releases
```bash
{
  "tool": "helm_query",
  "arguments": {
    "command": "list --all-namespaces"
  }
}
```

### Estado de un Release
```bash
{
  "tool": "helm_query",
  "arguments": {
    "command": "status my-app -n production"
  }
}
```

### Historial de Releases
```bash
{
  "tool": "helm_query",
  "arguments": {
    "command": "history my-app -n production"
  }
}
```

## 🚀 Análisis de Karpenter

### Estado Completo de Karpenter
```bash
{
  "tool": "analyze_karpenter",
  "arguments": {}
}
```

**Use cases:**
- **Verificar configuración de NodePools**
- **Monitorear nodos provisionados automáticamente**
- **Identificar problemas de escalado**
- **Revisar límites de recursos**

## 🔄 ArgoCD Status

### Estado de Aplicaciones
```bash
{
  "tool": "get_argocd_status",
  "arguments": {}
}
```

**Información proporcionada:**
- Estado de salud de aplicaciones
- Estado de sincronización
- Repositorios configurados
- Aplicaciones fuera de sincronización

## 📋 Reportes Detallados

### Reporte en Markdown
```bash
{
  "tool": "generate_health_report",
  "arguments": {
    "format": "markdown",
    "include_recommendations": true
  }
}
```

### Reporte en JSON para Automatización
```bash
{
  "tool": "generate_health_report",
  "arguments": {
    "format": "json",
    "include_recommendations": false
  }
}
```

### Reporte en YAML
```bash
{
  "tool": "generate_health_report",
  "arguments": {
    "format": "yaml",
    "include_recommendations": true
  }
}
```

## 🛠️ Corrección de Problemas de Recursos

### Configurar Resource Limits
```bash
{
  "tool": "create_resource_fixes",
  "arguments": {
    "issue_type": "resource_limits",
    "target": "my-deployment",
    "namespace": "production"
  }
}
```

### Crear HorizontalPodAutoscaler
```bash
{
  "tool": "create_resource_fixes",
  "arguments": {
    "issue_type": "hpa",
    "target": "my-deployment",
    "namespace": "production"
  }
}
```

### Configurar PodDisruptionBudget
```bash
{
  "tool": "create_resource_fixes",
  "arguments": {
    "issue_type": "pdb",
    "target": "my-deployment",
    "namespace": "production"
  }
}
```

### Configurar Node Affinity
```bash
{
  "tool": "create_resource_fixes",
  "arguments": {
    "issue_type": "node_affinity",
    "target": "my-deployment",
    "namespace": "production"
  }
}
```

## 🔍 Casos de Uso Avanzados

### 1. Diagnóstico de Problemas de Performance
```bash
# 1. Verificar estado general
{"tool": "cluster_health_check", "arguments": {}}

# 2. Analizar nodos con alta utilización
{"tool": "get_nodes_status", "arguments": {"include_metrics": true}}

# 3. Identificar pods problemáticos
{"tool": "get_pods_status", "arguments": {"namespace": "all"}}

# 4. Verificar eventos recientes
{"tool": "kubectl_query", "arguments": {"command": "get events --sort-by=.metadata.creationTimestamp | tail -20"}}
```

### 2. Auditoría de Recursos
```bash
# 1. Generar reporte completo
{"tool": "generate_health_report", "arguments": {"format": "markdown"}}

# 2. Verificar límites de recursos
{"tool": "kubectl_query", "arguments": {"command": "describe limitranges --all-namespaces"}}

# 3. Revisar quotas de namespace
{"tool": "kubectl_query", "arguments": {"command": "describe resourcequotas --all-namespaces"}}
```

### 3. Monitoreo de Karpenter y Autoescalado
```bash
# 1. Estado de Karpenter
{"tool": "analyze_karpenter", "arguments": {}}

# 2. Nodos provisionados recientemente
{"tool": "kubectl_query", "arguments": {"command": "get nodes --sort-by=.metadata.creationTimestamp"}}

# 3. HPAs configurados
{"tool": "kubectl_query", "arguments": {"command": "get hpa --all-namespaces"}}
```

### 4. Seguimiento de Deployments con ArgoCD
```bash
# 1. Estado de ArgoCD
{"tool": "get_argocd_status", "arguments": {}}

# 2. Aplicaciones fuera de sincronización
{"tool": "kubectl_query", "arguments": {"command": "get applications -n argocd"}}

# 3. Últimos deployments
{"tool": "kubectl_query", "arguments": {"command": "get replicasets --all-namespaces --sort-by=.metadata.creationTimestamp | tail -10"}}
```

## 🚨 Alertas y Monitoreo Proactivo

### Indicadores Clave a Monitorear

1. **Nodos No Saludables**: `unhealthy_nodes > 0`
2. **Pods Fallidos**: `failed_pods > 0`
3. **Alta Tasa de Reinicios**: `restarts > 5`
4. **Pods Pendientes por Mucho Tiempo**: `pending_pods > 0 por > 5min`
5. **Utilización de Recursos Alta**: `cpu_utilization > 80%`

### Script de Monitoreo Automatizado

```python
#!/usr/bin/env python3
import asyncio
import json
from kubernetes_mcp_server import KubernetesClient

async def monitoring_check():
    client = KubernetesClient()
    health = await client.analyze_cluster_health()
    
    alerts = []
    
    if health.unhealthy_nodes > 0:
        alerts.append(f"CRITICAL: {health.unhealthy_nodes} unhealthy nodes")
    
    if health.failed_pods > 0:
        alerts.append(f"CRITICAL: {health.failed_pods} failed pods")
    
    if health.pending_pods > 5:
        alerts.append(f"WARNING: {health.pending_pods} pending pods")
    
    if alerts:
        print("🚨 CLUSTER ALERTS:")
        for alert in alerts:
            print(f"  {alert}")
    else:
        print("✅ Cluster is healthy")

if __name__ == "__main__":
    asyncio.run(monitoring_check())
```

## 💡 Mejores Prácticas

1. **Monitoreo Regular**: Ejecuta health checks cada 5-10 minutos
2. **Alertas Proactivas**: Configura alertas para métricas críticas
3. **Reportes Periódicos**: Genera reportes diarios/semanales
4. **Automatización**: Usa los manifests generados para fixes rápidos
5. **Documentación**: Mantén logs de issues y resoluciones

## 🔗 Integración con GitHub Actions

```yaml
name: Cluster Health Check
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run health check
      run: |
        python -c "
        import asyncio
        from kubernetes_mcp_server import KubernetesClient
        
        async def main():
            client = KubernetesClient()
            health = await client.analyze_cluster_health()
            
            if health.overall_status != 'Healthy':
                print(f'::error::Cluster status: {health.overall_status}')
                for issue in health.critical_issues:
                    print(f'::error::{issue}')
                exit(1)
            else:
                print('::notice::Cluster is healthy')
        
        asyncio.run(main())
        "
```

Este MCP te proporciona una plataforma completa para monitorear y gestionar tu cluster de Kubernetes de manera eficiente y automatizada.