from prometheus_api_client import PrometheusConnect

class PrometheusClient:
    def __init__(self):
        self._prometheus_url = "http://192.168.49.2:30002/"
        self.prometheus = PrometheusConnect(url=self._prometheus_url, disable_ssl=True)

    def get_average_latency(self):
        sum_latency_query = 'python_requests_duration_seconds_sum{job="node-warehouseapi",service="service-warehouseapi"}'
        requests_query = 'python_requests_operations_total{ job="node-warehouseapi",service="service-warehouseapi"}'

        sum_latency_result = self.prometheus.custom_query(sum_latency_query)
        requests_result = self.prometheus.custom_query(requests_query)

        sum_latency = float(sum_latency_result[0]["value"][1])
        nr_of_requests = int(requests_result[0]["value"][1])

        average_latency = sum_latency / nr_of_requests

        return round(average_latency * 1000,3)
    
    def get_workload_rate(self):
        query = 'rate(python_requests_operations_total{service="service-warehouseapi"}[1m])'

        result = self.prometheus.custom_query(query)
        workload_rate = float(result[0]["value"][1])

        return round(workload_rate,2)