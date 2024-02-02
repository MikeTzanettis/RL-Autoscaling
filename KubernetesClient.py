from kubernetes import client, config

class KubernetesClient:
    def __init__(self):
        self.deployment_name = "deploy-warehouseapi"

    def get_replica_count(self,namespace="default"):
        config.load_kube_config()

        apps_v1 = client.AppsV1Api()
        deployment = apps_v1.read_namespaced_deployment(self.deployment_name, namespace)

        return deployment.spec.replicas
    
    def scale_deployment(self, scale_count, namespace="default"):
        config.load_kube_config()  # Load kubeconfig file for local testing; use config.load_incluster_config() for in-cluster usage

        apps_v1 = client.AppsV1Api()
        deployment = apps_v1.read_namespaced_deployment(self.deployment_name, namespace)
        deployment.spec.replicas = scale_count
        apps_v1.patch_namespaced_deployment(
            name=self.deployment_name,
            namespace=namespace,
            body=deployment
        )