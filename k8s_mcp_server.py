#!/usr/bin/env python3
"""
Kubernetes MCP Server
A comprehensive Model Context Protocol server for Kubernetes cluster monitoring,
health analysis, and management operations.
"""

import asyncio
import json
import logging
import subprocess
import yaml
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("k8s-mcp")

class ClusterProvider(Enum):
    EKS = "eks"
    GKE = "gke"
    AKS = "aks"
    GENERIC = "generic"

@dataclass
class NodeMetrics:
    name: str
    cpu_usage: str
    memory_usage: str
    disk_usage: str
    status: str
    age: str
    version: str
    instance_type: Optional[str] = None
    zone: Optional[str] = None

@dataclass
class PodMetrics:
    name: str
    namespace: str
    status: str
    cpu_usage: str
    memory_usage: str
    restarts: int
    age: str
    node: str

@dataclass
class ClusterHealth:
    overall_status: str
    node_count: int
    healthy_nodes: int
    unhealthy_nodes: int
    total_pods: int
    running_pods: int
    pending_pods: int
    failed_pods: int
    cpu_utilization: float
    memory_utilization: float
    disk_utilization: float
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]

class KubernetesClient:
    def __init__(self):
        self.provider = self._detect_provider()
    
    def _detect_provider(self) -> ClusterProvider:
        """Detect the Kubernetes cluster provider"""
        try:
            # Try to get cluster info
            result = subprocess.run(
                ["kubectl", "cluster-info", "dump", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                cluster_info = result.stdout
                if "eks.amazonaws.com" in cluster_info:
                    return ClusterProvider.EKS
                elif "gke.googleapis.com" in cluster_info:
                    return ClusterProvider.GKE
                elif "aks.azure.com" in cluster_info:
                    return ClusterProvider.AKS
            
            return ClusterProvider.GENERIC
        except Exception as e:
            logger.warning(f"Could not detect provider: {e}")
            return ClusterProvider.GENERIC
    
    async def execute_kubectl(self, args: List[str]) -> Tuple[str, str, int]:
        """Execute kubectl command asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                "kubectl", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return stdout.decode(), stderr.decode(), process.returncode
        except Exception as e:
            logger.error(f"kubectl execution error: {e}")
            return "", str(e), 1
    
    async def execute_helm(self, args: List[str]) -> Tuple[str, str, int]:
        """Execute helm command asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                "helm", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return stdout.decode(), stderr.decode(), process.returncode
        except Exception as e:
            logger.error(f"helm execution error: {e}")
            return "", str(e), 1

    async def get_nodes_metrics(self) -> List[NodeMetrics]:
        """Get detailed node metrics"""
        nodes = []
        
        # Get node information
        stdout, stderr, code = await self.execute_kubectl([
            "get", "nodes", "-o", "json"
        ])
        
        if code != 0:
            logger.error(f"Failed to get nodes: {stderr}")
            return nodes
        
        try:
            nodes_data = json.loads(stdout)
            
            # Get metrics if available
            metrics_stdout, _, metrics_code = await self.execute_kubectl([
                "top", "nodes", "--no-headers"
            ])
            
            metrics_map = {}
            if metrics_code == 0:
                for line in metrics_stdout.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 3:
                            metrics_map[parts[0]] = {
                                'cpu': parts[1],
                                'memory': parts[2]
                            }
            
            for node in nodes_data.get('items', []):
                name = node['metadata']['name']
                status = "Ready" if any(
                    condition['type'] == 'Ready' and condition['status'] == 'True'
                    for condition in node['status']['conditions']
                ) else "NotReady"
                
                age = self._calculate_age(node['metadata']['creationTimestamp'])
                version = node['status']['nodeInfo']['kubeletVersion']
                
                # Extract instance type and zone if available
                instance_type = node['metadata'].get('labels', {}).get('node.kubernetes.io/instance-type')
                zone = node['metadata'].get('labels', {}).get('topology.kubernetes.io/zone')
                
                cpu_usage = metrics_map.get(name, {}).get('cpu', 'N/A')
                memory_usage = metrics_map.get(name, {}).get('memory', 'N/A')
                
                nodes.append(NodeMetrics(
                    name=name,
                    cpu_usage=cpu_usage,
                    memory_usage=memory_usage,
                    disk_usage="N/A",  # Would need additional metrics
                    status=status,
                    age=age,
                    version=version,
                    instance_type=instance_type,
                    zone=zone
                ))
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse nodes JSON: {e}")
        
        return nodes
    
    async def get_pods_metrics(self, namespace: str = "all") -> List[PodMetrics]:
        """Get detailed pod metrics"""
        pods = []
        
        args = ["get", "pods", "-o", "json"]
        if namespace != "all":
            args.extend(["-n", namespace])
        else:
            args.append("--all-namespaces")
        
        stdout, stderr, code = await self.execute_kubectl(args)
        
        if code != 0:
            logger.error(f"Failed to get pods: {stderr}")
            return pods
        
        try:
            pods_data = json.loads(stdout)
            
            # Get pod metrics if available
            metrics_args = ["top", "pods", "--no-headers"]
            if namespace != "all":
                metrics_args.extend(["-n", namespace])
            else:
                metrics_args.append("--all-namespaces")
            
            metrics_stdout, _, metrics_code = await self.execute_kubectl(metrics_args)
            
            metrics_map = {}
            if metrics_code == 0:
                for line in metrics_stdout.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if namespace == "all" and len(parts) >= 4:
                            key = f"{parts[0]}:{parts[1]}"  # namespace:name
                            metrics_map[key] = {'cpu': parts[2], 'memory': parts[3]}
                        elif namespace != "all" and len(parts) >= 3:
                            metrics_map[parts[0]] = {'cpu': parts[1], 'memory': parts[2]}
            
            for pod in pods_data.get('items', []):
                name = pod['metadata']['name']
                pod_namespace = pod['metadata']['namespace']
                
                status = pod['status']['phase']
                restarts = sum(
                    container_status.get('restartCount', 0)
                    for container_status in pod['status'].get('containerStatuses', [])
                )
                
                age = self._calculate_age(pod['metadata']['creationTimestamp'])
                node = pod['spec'].get('nodeName', 'N/A')
                
                # Get metrics
                if namespace == "all":
                    key = f"{pod_namespace}:{name}"
                else:
                    key = name
                
                cpu_usage = metrics_map.get(key, {}).get('cpu', 'N/A')
                memory_usage = metrics_map.get(key, {}).get('memory', 'N/A')
                
                pods.append(PodMetrics(
                    name=name,
                    namespace=pod_namespace,
                    status=status,
                    cpu_usage=cpu_usage,
                    memory_usage=memory_usage,
                    restarts=restarts,
                    age=age,
                    node=node
                ))
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pods JSON: {e}")
        
        return pods
    
    async def analyze_cluster_health(self) -> ClusterHealth:
        """Comprehensive cluster health analysis"""
        nodes = await self.get_nodes_metrics()
        pods = await self.get_pods_metrics()
        
        # Node analysis
        healthy_nodes = sum(1 for node in nodes if node.status == "Ready")
        unhealthy_nodes = len(nodes) - healthy_nodes
        
        # Pod analysis
        running_pods = sum(1 for pod in pods if pod.status == "Running")
        pending_pods = sum(1 for pod in pods if pod.status == "Pending")
        failed_pods = sum(1 for pod in pods if pod.status in ["Failed", "CrashLoopBackOff"])
        
        # Resource utilization (simplified calculation)
        cpu_utilization = 0.0
        memory_utilization = 0.0
        
        # Issues and recommendations
        critical_issues = []
        warnings = []
        recommendations = []
        
        if unhealthy_nodes > 0:
            critical_issues.append(f"{unhealthy_nodes} nodes are not ready")
        
        if failed_pods > 0:
            critical_issues.append(f"{failed_pods} pods are in failed state")
        
        if pending_pods > 0:
            warnings.append(f"{pending_pods} pods are pending")
        
        # High restart pods
        high_restart_pods = [pod for pod in pods if pod.restarts > 5]
        if high_restart_pods:
            warnings.append(f"{len(high_restart_pods)} pods have high restart counts")
        
        # Recommendations based on analysis
        if unhealthy_nodes > 0:
            recommendations.append("Investigate unhealthy nodes and consider replacement")
        
        if pending_pods > 0:
            recommendations.append("Check resource constraints and node availability")
        
        if high_restart_pods:
            recommendations.append("Investigate pods with high restart counts for stability issues")
        
        overall_status = "Healthy"
        if critical_issues:
            overall_status = "Critical"
        elif warnings:
            overall_status = "Warning"
        
        return ClusterHealth(
            overall_status=overall_status,
            node_count=len(nodes),
            healthy_nodes=healthy_nodes,
            unhealthy_nodes=unhealthy_nodes,
            total_pods=len(pods),
            running_pods=running_pods,
            pending_pods=pending_pods,
            failed_pods=failed_pods,
            cpu_utilization=cpu_utilization,
            memory_utilization=memory_utilization,
            disk_utilization=0.0,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations
        )
    
    async def analyze_karpenter(self) -> Dict[str, Any]:
        """Analyze Karpenter status and configuration"""
        karpenter_analysis = {
            "installed": False,
            "version": None,
            "node_pools": [],
            "provisioned_nodes": 0,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Check if Karpenter is installed
            stdout, stderr, code = await self.execute_kubectl([
                "get", "deployment", "karpenter", "-n", "karpenter", "-o", "json"
            ])
            
            if code == 0:
                karpenter_analysis["installed"] = True
                deployment_data = json.loads(stdout)
                
                # Get version from image
                containers = deployment_data['spec']['template']['spec']['containers']
                for container in containers:
                    if 'karpenter' in container['image']:
                        karpenter_analysis["version"] = container['image'].split(':')[-1]
                        break
                
                # Get NodePools
                stdout, stderr, code = await self.execute_kubectl([
                    "get", "nodepools", "-o", "json"
                ])
                
                if code == 0:
                    nodepools_data = json.loads(stdout)
                    karpenter_analysis["node_pools"] = [
                        {
                            "name": np["metadata"]["name"],
                            "instance_types": np["spec"].get("requirements", []),
                            "limits": np["spec"].get("limits", {})
                        }
                        for np in nodepools_data.get("items", [])
                    ]
                
                # Count Karpenter-provisioned nodes
                stdout, stderr, code = await self.execute_kubectl([
                    "get", "nodes", "-l", "karpenter.sh/provisioner-name", "-o", "json"
                ])
                
                if code == 0:
                    nodes_data = json.loads(stdout)
                    karpenter_analysis["provisioned_nodes"] = len(nodes_data.get("items", []))
        
        except Exception as e:
            karpenter_analysis["issues"].append(f"Error analyzing Karpenter: {str(e)}")
        
        return karpenter_analysis
    
    async def get_argocd_status(self) -> Dict[str, Any]:
        """Get ArgoCD application status"""
        argocd_status = {
            "installed": False,
            "applications": [],
            "health_status": "Unknown",
            "sync_status": "Unknown"
        }
        
        try:
            # Check if ArgoCD is installed
            stdout, stderr, code = await self.execute_kubectl([
                "get", "applications", "-n", "argocd", "-o", "json"
            ])
            
            if code == 0:
                argocd_status["installed"] = True
                apps_data = json.loads(stdout)
                
                healthy_apps = 0
                synced_apps = 0
                
                for app in apps_data.get("items", []):
                    app_info = {
                        "name": app["metadata"]["name"],
                        "health": app["status"].get("health", {}).get("status", "Unknown"),
                        "sync": app["status"].get("sync", {}).get("status", "Unknown"),
                        "repo": app["spec"]["source"]["repoURL"]
                    }
                    argocd_status["applications"].append(app_info)
                    
                    if app_info["health"] == "Healthy":
                        healthy_apps += 1
                    if app_info["sync"] == "Synced":
                        synced_apps += 1
                
                total_apps = len(apps_data.get("items", []))
                if total_apps > 0:
                    argocd_status["health_status"] = f"{healthy_apps}/{total_apps} Healthy"
                    argocd_status["sync_status"] = f"{synced_apps}/{total_apps} Synced"
        
        except Exception as e:
            logger.error(f"Error getting ArgoCD status: {e}")
        
        return argocd_status
    
    def _calculate_age(self, timestamp: str) -> str:
        """Calculate age from Kubernetes timestamp"""
        try:
            created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(created.tzinfo)
            delta = now - created
            
            if delta.days > 0:
                return f"{delta.days}d"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h"
            else:
                return f"{delta.seconds // 60}m"
        except Exception:
            return "Unknown"

# Initialize the MCP server
app = Server("kubernetes-mcp-server")
k8s_client = KubernetesClient()

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="cluster_health_check",
            description="Perform comprehensive cluster health analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_recommendations": {
                        "type": "boolean",
                        "description": "Include recommendations in the analysis",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="get_nodes_status",
            description="Get detailed information about cluster nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_metrics": {
                        "type": "boolean",
                        "description": "Include resource usage metrics",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="get_pods_status",
            description="Get detailed information about pods",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Specific namespace to query (default: all)",
                        "default": "all"
                    },
                    "include_metrics": {
                        "type": "boolean",
                        "description": "Include resource usage metrics",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="kubectl_query",
            description="Execute kubectl commands",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "kubectl command to execute (without 'kubectl' prefix)"
                    }
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="helm_query",
            description="Execute helm commands",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "helm command to execute (without 'helm' prefix)"
                    }
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="analyze_karpenter",
            description="Analyze Karpenter autoscaler status and configuration",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_argocd_status",
            description="Get ArgoCD applications status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="generate_health_report",
            description="Generate comprehensive cluster health report",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown", "yaml"],
                        "description": "Report format",
                        "default": "markdown"
                    },
                    "include_recommendations": {
                        "type": "boolean",
                        "description": "Include recommendations",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="create_resource_fixes",
            description="Generate Kubernetes manifests to fix resource issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "enum": ["resource_limits", "hpa", "pdb", "node_affinity"],
                        "description": "Type of resource issue to fix"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target resource (deployment, pod, etc.)"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Target namespace",
                        "default": "default"
                    }
                },
                "required": ["issue_type", "target"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls"""
    
    if name == "cluster_health_check":
        health = await k8s_client.analyze_cluster_health()
        result = asdict(health)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_nodes_status":
        nodes = await k8s_client.get_nodes_metrics()
        result = [asdict(node) for node in nodes]
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_pods_status":
        namespace = arguments.get("namespace", "all")
        pods = await k8s_client.get_pods_metrics(namespace)
        result = [asdict(pod) for pod in pods]
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "kubectl_query":
        command = arguments.get("command", "")
        args = command.split()
        stdout, stderr, code = await k8s_client.execute_kubectl(args)
        
        result = {
            "command": f"kubectl {command}",
            "returncode": code,
            "stdout": stdout,
            "stderr": stderr
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "helm_query":
        command = arguments.get("command", "")
        args = command.split()
        stdout, stderr, code = await k8s_client.execute_helm(args)
        
        result = {
            "command": f"helm {command}",
            "returncode": code,
            "stdout": stdout,
            "stderr": stderr
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "analyze_karpenter":
        result = await k8s_client.analyze_karpenter()
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_argocd_status":
        result = await k8s_client.get_argocd_status()
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "generate_health_report":
        format_type = arguments.get("format", "markdown")
        include_recommendations = arguments.get("include_recommendations", True)
        
        # Gather all data
        health = await k8s_client.analyze_cluster_health()
        nodes = await k8s_client.get_nodes_metrics()
        pods = await k8s_client.get_pods_metrics()
        karpenter = await k8s_client.analyze_karpenter()
        argocd = await k8s_client.get_argocd_status()
        
        if format_type == "markdown":
            report = await generate_markdown_report(health, nodes, pods, karpenter, argocd, include_recommendations)
        elif format_type == "yaml":
            report_data = {
                "cluster_health": asdict(health),
                "nodes": [asdict(node) for node in nodes],
                "karpenter": karpenter,
                "argocd": argocd,
                "generated_at": datetime.now().isoformat()
            }
            report = yaml.dump(report_data, default_flow_style=False)
        else:  # json
            report_data = {
                "cluster_health": asdict(health),
                "nodes": [asdict(node) for node in nodes],
                "karpenter": karpenter,
                "argocd": argocd,
                "generated_at": datetime.now().isoformat()
            }
            report = json.dumps(report_data, indent=2)
        
        return [types.TextContent(type="text", text=report)]
    
    elif name == "create_resource_fixes":
        issue_type = arguments.get("issue_type")
        target = arguments.get("target")
        namespace = arguments.get("namespace", "default")
        
        manifests = await generate_resource_fixes(issue_type, target, namespace)
        return [types.TextContent(type="text", text=manifests)]
    
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def generate_markdown_report(health, nodes, pods, karpenter, argocd, include_recommendations):
    """Generate a comprehensive markdown health report"""
    report = f"""# Kubernetes Cluster Health Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Provider: {k8s_client.provider.value.upper()}

## 🎯 Overall Health Status: {health.overall_status}

### 📊 Cluster Summary
- **Nodes**: {health.node_count} total ({health.healthy_nodes} healthy, {health.unhealthy_nodes} unhealthy)
- **Pods**: {health.total_pods} total ({health.running_pods} running, {health.pending_pods} pending, {health.failed_pods} failed)
- **CPU Utilization**: {health.cpu_utilization:.1f}%
- **Memory Utilization**: {health.memory_utilization:.1f}%

### 🔴 Critical Issues
"""
    
    if health.critical_issues:
        for issue in health.critical_issues:
            report += f"- ❌ {issue}\n"
    else:
        report += "- ✅ No critical issues detected\n"
    
    report += "\n### ⚠️ Warnings\n"
    if health.warnings:
        for warning in health.warnings:
            report += f"- ⚠️ {warning}\n"
    else:
        report += "- ✅ No warnings\n"
    
    # Node Details
    report += f"\n## 🖥️ Node Details ({len(nodes)} nodes)\n\n"
    report += "| Name | Status | CPU | Memory | Age | Version | Instance Type |\n"
    report += "|------|--------|-----|--------|-----|---------|---------------|\n"
    
    for node in nodes[:10]:  # Limit to first 10 nodes
        report += f"| {node.name} | {node.status} | {node.cpu_usage} | {node.memory_usage} | {node.age} | {node.version} | {node.instance_type or 'N/A'} |\n"
    
    if len(nodes) > 10:
        report += f"\n*... and {len(nodes) - 10} more nodes*\n"
    
    # Pod Issues
    problem_pods = [pod for pod in pods if pod.status != "Running" or pod.restarts > 5]
    if problem_pods:
        report += f"\n## 🚨 Problem Pods ({len(problem_pods)} pods)\n\n"
        report += "| Name | Namespace | Status | Restarts | Node |\n"
        report += "|------|-----------|--------|----------|------|\n"
        
        for pod in problem_pods[:20]:  # Limit to first 20
            report += f"| {pod.name} | {pod.namespace} | {pod.status} | {pod.restarts} | {pod.node} |\n"
    
    # Karpenter Analysis
    if karpenter["installed"]:
        report += f"\n## 🚀 Karpenter Status\n"
        report += f"- **Version**: {karpenter['version']}\n"
        report += f"- **Node Pools**: {len(karpenter['node_pools'])}\n"
        report += f"- **Provisioned Nodes**: {karpenter['provisioned_nodes']}\n"
        
        if karpenter["issues"]:
            report += "\n**Issues:**\n"
            for issue in karpenter["issues"]:
                report += f"- ❌ {issue}\n"
    else:
        report += "\n## 🚀 Karpenter Status\n- ❌ Not installed\n"
    
    # ArgoCD Status
    if argocd["installed"]:
        report += f"\n## 🔄 ArgoCD Status\n"
        report += f"- **Applications**: {len(argocd['applications'])}\n"
        report += f"- **Health**: {argocd['health_status']}\n"
        report += f"- **Sync**: {argocd['sync_status']}\n"
        
        if argocd["applications"]:
            report += "\n**Applications:**\n"
            for app in argocd["applications"][:10]:
                report += f"- {app['name']}: {app['health']}/{app['sync']}\n"
    else:
        report += "\n## 🔄 ArgoCD Status\n- ❌ Not installed\n"
    
    # Recommendations
    if include_recommendations and health.recommendations:
        report += "\n## 💡 Recommendations\n"
        for rec in health.recommendations:
            report += f"- 🔧 {rec}\n"
    
    return report

async def generate_resource_fixes(issue_type, target, namespace):
    """Generate Kubernetes manifests to fix resource issues"""
    
    if issue_type == "resource_limits":
        return f"""# Resource Limits Fix for {target}
apiVersion: v1
kind: LimitRange
metadata:
  name: {target}-limits
  namespace: {namespace}
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
---
# Patch for existing deployment
# kubectl patch deployment {target} -n {namespace} -p '{{"spec":{{"template":{{"spec":{{"containers":[{{"name":"{target}","resources":{{"limits":{{"cpu":"500m","memory":"512Mi"}},"requests":{{"cpu":"100m","memory":"128Mi"}}}}}}]}}}}}}}'
"""
    
    elif issue_type == "hpa":
        return f"""# Horizontal Pod Autoscaler for {target}