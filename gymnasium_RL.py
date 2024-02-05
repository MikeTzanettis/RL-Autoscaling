import requests
import numpy as np
import time
import gymnasium as gym
from gymnasium import spaces
from KubernetesClient import KubernetesClient
from PrometheusClient import PrometheusClient

class AutoScalingEnv(gym.Env):
    def __init__(self):
        super(AutoScalingEnv, self).__init__()
        self.prometheus_client = PrometheusClient()
        self.kubernetes_client = KubernetesClient()
        self.services = ['service_1', 'service_2', 'service_3']
        self.min_pods = 1
        self.max_pods = 6
        # 3 possible actions: -1=scale down, 0=Do Nothing, +1=scale up
        self.action_space = spaces.Discrete(3)
        self.replicas = len(self.services) * [1]
        self.current_workload = 0.0
        self.steps = 0
        low = np.array([
            0, # arrival_rate_prediction
            0, # arrival_rate
            1, # replicas
            0  # latency
        ])
        high = np.array([
            np.inf,  # arrival_rate_prediction
            np.inf,  # arrival_rate
            6,       # replicas
            np.inf   # latency
        ])

        # Observation space is grid of size:rows x columns
        self.observation_space = spaces.Box(low, high, dtype=np.float64)

    def reset(self, seed=None, options=None):
        self.steps = 0

        observation = [
            0.0, # prediction
            0.0, # arrival rate
            1, # replicas 1
            1, # replicas 2
            1, # replicas 3
            0.0 # latency
        ]

        return observation

    def step(self, action):

        self._apply_action(action)

        rate = 3000
        allocated_users = 50

        workload_generator_url = f"http://localhost:3000/generate-workload?rate={rate}&allocated_users={allocated_users}"
        
        print(f"Generating workload... {rate} requests per second with {allocated_users} users.")
        response = requests.get(workload_generator_url).json()

        time.sleep(30)
        try:
            average_latency = self.prometheus_client.get_average_latency()
            workload_rate = self.prometheus_client.get_workload_rate()
            
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Prometheus or Kubernetes: {e}")
            return None
        predicted_workload_rate = 300.0 #Predict with ARIMA
        observation = [predicted_workload_rate,
                       workload_rate,
                       average_latency,
                       self.replicas
                       ]

        self.steps += 1
    def close(self, pos):
        pass
    
    def render(self):
        pass

    def _apply_action(self, action):
        
        decoded_action = self._decimal_to_base3(action, len(self.services))
        
        for idx,service_name in self.services:
            current_service_replicas = self.kubernetes_client.get_replica_count(service_name)
            scaling_action = current_service_replicas + decoded_action[idx]
            self.replicas[idx] = scaling_action
            self.kubernetes_client.scale_deployment(scaling_action, service_name)
            


    def _decimal_to_base3(decimal_number, number_of_services):
        result = []
        while decimal_number > 0:
            remainder = decimal_number % 3
            result.insert(0, remainder)
            decimal_number //= 3

        while len(result) < number_of_services:
            result.insert(0, 0)

        return tuple(x - 1 for x in result)
