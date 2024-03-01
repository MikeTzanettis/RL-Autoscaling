from concurrent.futures import ProcessPoolExecutor, process
from readline import write_history_file
import requests
import time
import itertools
import csv
import subprocess
from KubernetesClient import KubernetesClient
from PrometheusClient import PrometheusClient
class SimulatedEnvironment():
    def __init__(self):
        self.workload_url = "http://localhost:3000/generate-workload?rate="
        self.cancel_script_url = "http://localhost:3000/cancel-script?process_id="
        self.process_id = None
        self.kube = KubernetesClient()
        self.prom = PrometheusClient()

        self.excluded_permutations = set(itertools.product(
            range(1, 4),
            range(1, 4),
            range(1, 4)
        ))
        self.services = {
            "deploy-service-1": {"min_replicas": 1, "max_replicas": 4},
            "deploy-service-2": {"min_replicas": 1, "max_replicas": 4},
            "deploy-service-3": {"min_replicas": 1, "max_replicas": 4}
        }

    def scale_services(self,permutation):
        print(f"Scaling service-1 to {permutation[0]} replicas...")
        self.kube.scale_deployment(permutation[0],"deploy-service-1")
        time.sleep(5)

        print(f"Scaling service-2 to {permutation[1]} replicas...")
        self.kube.scale_deployment(permutation[1],"deploy-service-2")
        time.sleep(5)

        print(f"Scaling service-3 to {permutation[2]} replicas...")
        self.kube.scale_deployment(permutation[2],"deploy-service-3")
        time.sleep(10)

        print(f"Scaled replicas to {permutation}")

    def iterate_permutations(self):
        permutation_step = 0
        rs_counter = 0
        for scaling_permutation in itertools.product(
            range(self.services["deploy-service-1"]["min_replicas"], self.services["deploy-service-1"]["max_replicas"] + 1),
            range(self.services["deploy-service-2"]["min_replicas"], self.services["deploy-service-2"]["max_replicas"] + 1),
            range(self.services["deploy-service-3"]["min_replicas"], self.services["deploy-service-3"]["max_replicas"] + 1)
        ):
            # if scaling_permutation in self.excluded_permutations:
            #     continue
            permutation_step += 1
        
            print(f"Permutation Step: {permutation_step}")
            if(permutation_step < 50):
                continue
            rs_counter += 1
            if(rs_counter == 10):
                _ = self.restart_services()
                print("Waiting to restart services...")
                time.sleep(60)
                rs_counter = 0

            _ = self.scale_services(scaling_permutation)
            _ = self.generate_workload(scaling_permutation)
            


    def generate_workload(self,scaling_permutation):
        with open("test_workload.txt", 'r') as file:
            workload_timesteps = [line.strip() for line in file]
        w_step = 0
        
        for workload_step in workload_timesteps:
            w_step += 1
            print(f"Workload  Step: {w_step} out of {len(workload_timesteps)}")
            print(self.process_id)
            if self.process_id is not None:
                print(f"cancelling script with process id: {self.process_id}")
                response = requests.get(self.cancel_script_url + str(self.process_id)).json()
                print(response)
            time.sleep(60)
            workload_generator_url = self.workload_url + workload_step
            
            print(f"Generating workload... {workload_step} requests per second")
            #target = self.prom.get_total_requests() + int(workload_step) * 60
            self.process_id = requests.get(workload_generator_url).json()["process_id"]
            time.sleep(62)
            #print(f"Target: {target}")
            metrics = self.get_metrics()
            print(f"Permutation: {scaling_permutation}, Latency: {metrics}, Rate: {workload_step}")
            self.write_to_csv(metrics,float(workload_step),scaling_permutation[0],scaling_permutation[1],scaling_permutation[2])

    def get_metrics(self):
        # total_requests = self.prom.get_total_requests()
        # start = time.time()
        # while total_requests != target and total_requests != target + 1:
        #     time.sleep(5)
        #     total_requests = self.prom.get_total_requests()
        #     print(f"Total_requests: {total_requests} out of {target}")
        # stop = time.time()
        # duration = round(stop - start) + 60
        # print(f"Duration: {duration}")
        latency = self.prom.get_average_latency()
        return latency

    def write_to_csv(self,latency, workload, replicas_1, replicas_2, replicas_3):
        # CSV file name
        file_name = 'data2.csv'

        # Data to be written
        data = [[workload, replicas_1, replicas_2, replicas_3, latency]]

        # Header for the columns
        fields = ['Workload', 'Replicas_1', 'Replicas_2', 'Replicas_3', 'Latency']

        # Writing to CSV file
        with open(file_name, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Check if file is empty, if so, write the header
            if file.tell() == 0:
                writer.writerow(fields)
            
            writer.writerows(data)

        print("Data has been written to", file_name)

    def restart_services(self):
        script_path = "/home/miketz/Documents/restart_services.sh"
        try:
            subprocess.run(["bash", script_path], check=True)
            print("Script executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error executing the script: {e}")
        except FileNotFoundError:
            print("The script file was not found.")