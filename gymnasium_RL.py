import math
import requests
import numpy as np
import time
import gymnasium as gym
from gymnasium import spaces
from KubernetesClient import KubernetesClient
from PrometheusClient import PrometheusClient

class AutoScalingEnv(gym.Env):
    def __init__(self,workload_file):
        super(AutoScalingEnv, self).__init__()
        self.prometheus_client = PrometheusClient()
        self.kubernetes_client = KubernetesClient()
        self.services = ['service_1', 'service_2', 'service_3']
        self.min_pods = 1
        self.max_pods = 6
        # 3 possible actions: -1=scale down, 0=Do Nothing, +1=scale up
        self.action_space = spaces.Discrete(3 * len(self.services))
        self.replicas = len(self.services) * [1]
        self.current_workload = 0.0
        self.steps = 0
        self.max_episode_steps = 48
        self.process_id = None
        self.workload_url = "http://localhost:3000/generate-workload?rate="
        self.cancel_script_url = "http://localhost:3000/cancel-script?rateprocess_id="
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
        with open(workload_file, 'r') as file:
            self.workload_timesteps = [line.strip() for line in file]


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

        is_invalid_action = self._apply_action(action)

        if self.process_id is not None:
            cancel_k6_script_url = self.cancel_script_url + self.process_id
            _ = requests.get(cancel_k6_script_url)

        workload_rate = self.workload_timesteps[self.steps]

        workload_generator_url = self.workload_url + workload_rate
        
        print(f"Generating workload... {workload_rate} requests per second")
        self.process_id = requests.get(workload_generator_url).json()

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
                       self.replicas[0],
                       self.replicas[1],
                       self.replicas[2],
                       average_latency
                       ]

        reward,done = self._calculate_reward(observation,is_invalid_action)

        self.steps += 1
        if done:
            self.steps = 0

        return observation,reward,done
        
    def close(self):
        pass
    
    def render(self):
        pass

    def _apply_action(self, action):
        
        decoded_action = self._decimal_to_base3(action, len(self.services))
        invalid_action = False

        for index,service_name in self.services:
            current_service_replicas = self.kubernetes_client.get_replica_count(service_name)
            scaling_action = current_service_replicas + decoded_action[index]
            if(1 <= scaling_action <= 6):
                self.replicas[index] = scaling_action
                self.kubernetes_client.scale_deployment(scaling_action, service_name)
                return invalid_action
            else:
                invalid_action = True
                return invalid_action
            
    def _calculate_reward(self, observation,is_invalid_action):
        """
        Returns a reward with two components regarding the pod utilization
        and the application latency each weighted differently
        Reward range: [0, 100]
        """
        done = False
        replicas = [None] * 3
        sla_latency = 0.5

        # Unpack observation
        (_,
         _,
         replicas[0],
         replicas[1],
         replicas[2],
         latency) = observation

        reward = 0

        pod_weight = 0.5
        latency_weight = 0.5

        if is_invalid_action:
            reward = -100
            done = True
            return reward,done

        # Pod reward
        pod_reward_total = 0
        for replica_num in replicas:
            pod_reward_total += -100 / (self.max_pods - 1) * replica_num \
                + 100 * self.max_pods / (self.max_pods - 1)
        average_pod_reward = pod_reward_total / 3
        reward += pod_weight * average_pod_reward

        # Hyperparameter that determines the drop on the latency reward part
        d = 10.0
        #d = 20.0
        #d = 50.0

        # Latency as a percentage of the delcared SLA value
        latency_ratio = latency / sla_latency

        # Latency reward
        latency_ref_value = 0.8
        if latency_ratio < latency_ref_value:
            latency_reward = 100 * pow(math.e, -0.06 * d * pow(latency_ref_value - latency_ratio, 2))
        elif latency_ratio < 1:
            latency_reward = 100 * pow(math.e, -10 * d * pow(latency_ref_value - latency_ratio, 2))
        else:
            reward = -100
            done = True
            return reward,done

        reward += latency_weight * latency_reward

        return reward,done


    def _decimal_to_base3(decimal_number, number_of_services):
        result = []
        while decimal_number > 0:
            remainder = decimal_number % 3
            result.insert(0, remainder)
            decimal_number //= 3

        while len(result) < number_of_services:
            result.insert(0, 0)

        return tuple(x - 1 for x in result)
