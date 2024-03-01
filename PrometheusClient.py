from prometheus_api_client import PrometheusConnect

class PrometheusClient:
    def __init__(self):
        self._prometheus_url = "http://192.168.49.2:30002/"
        self.prometheus = PrometheusConnect(url=self._prometheus_url, disable_ssl=True)

    # def get_average_latency(self,duration):
    #     query = 'sum(rate(python_requests_duration_seconds_sum{{service="service-metrics-exporter"}}[{0}s]))' \
    #     '/ sum(rate(python_requests_operations_total{{service="service-metrics-exporter"}}[{0}s]))'.format(duration)

    #     result = self.prometheus.custom_query(query)
    #     average_latency = float(result[0]["value"][1])
    #     return round(average_latency,3)
    def get_average_latency(self):
        query = 'sum(rate(python_requests_duration_seconds_sum{service="service-metrics-exporter"}[1m]))' \
        '/ sum(rate(python_requests_operations_total{service="service-metrics-exporter"}[1m]))'

        result = self.prometheus.custom_query(query)
        average_latency = float(result[0]["value"][1])
        return round(average_latency,3)
    def get_workload_rate(self):
        query = 'sum(rate(python_requests_operations_total{service="service-metrics-exporter"}[1m]))'

        result = self.prometheus.custom_query(query)
        workload_rate = float(result[0]["value"][1])

        return round(workload_rate,2)
    
    def get_total_requests(self):
        query = 'sum(python_requests_operations_total{service="service-metrics-exporter"})'

        result = self.prometheus.custom_query(query)
        print(result)
        workload_rate = int(result[0]["value"][1])

        return workload_rate