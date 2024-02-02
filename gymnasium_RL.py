import requests
import numpy as np
import pygame
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
        # 3 possible actions: -1=scale down, 0=Do Nothing, +1=scale up
        self.action_space = spaces.Discrete(3)
        self.replicas = len(self.services) * [1]
        self.current_workload = 0.0
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

    def reset(self):
        self.current_pos = self.start_pos
        return self.current_pos

    def step(self, action):
        rate = 3000
        allocated_users = 50
        try:
            average_latency = self.prometheus_client.get_average_latency()
            workload_rate = self.prometheus_client.get_workload_rate()
            number_of_pods = self.kubernetes_client.get_replica_count()
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Prometheus or Kubernetes: {e}")
            return None
        
        workload_generator_url = f"http://localhost:3000/generate-workload?rate={rate}&allocated_users={allocated_users}"
        
        print(f"Generating workload... {rate} requests per second with {allocated_users} users.")
        response = requests.get(workload_generator_url).json()

        time.sleep(30)

    def _is_valid_position(self, pos):
        pass

    def render(self):
        pass