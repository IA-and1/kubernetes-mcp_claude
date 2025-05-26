import argparse
from mcp import cluster_info, node_info, pod_info, karpenter_info, helm_info, utils

def main():
    parser = argparse.ArgumentParser(description="Kubernetes MCP Info Collector (EKS Only)")
    parser.add_argument("command", choices=[
        "cluster_health_check",
        "get_nodes_status",
        "get_pods_status",
        "analyze_karpenter",
        "get_helm_releases"
    ])
    parser.add_argument("--namespace", help="Namespace para pods o helm (opcional)")
    args = parser.parse_args()

    if args.command == "cluster_health_check":
        utils.print_section("Cluster Version")
        print(cluster_info.get_cluster_version())
        utils.print_section("API Resources")
        print(cluster_info.get_api_resources())
    elif args.command == "get_nodes_status":
        utils.print_section("Nodes")
        print(node_info.get_nodes())
        utils.print_section("Node Metrics")
        print(node_info.get_node_metrics())
    elif args.command == "get_pods_status":
        utils.print_section("Pods")
        print(pod_info.get_pods(args.namespace))
        utils.print_section("Pod Metrics")
        print(pod_info.get_pod_metrics(args.namespace))
    elif args.command == "analyze_karpenter":
        utils.print_section("Karpenter Nodes")
        print(karpenter_info.get_karpenter_nodes())
        utils.print_section("Karpenter Provisioners")
        print(karpenter_info.get_karpenter_provisioners())
    elif args.command == "get_helm_releases":
        utils.print_section("Helm Releases")
        print(helm_info.get_helm_releases(args.namespace))

if __name__ == "__main__":
    main()