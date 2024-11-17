import json
import os
from typing import Any

import git.exc
import streamlit as st
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2, EC2Instances, Lambda
from diagrams.aws.database import Database, ElasticacheForRedis, ElasticacheForMemcached
from diagrams.aws.integration import SimpleQueueServiceSqs, SimpleNotificationServiceSns
from diagrams.aws.management import Cloudtrail
from diagrams.aws.network import ElasticLoadBalancing, CloudFront
from diagrams.aws.storage import SimpleStorageServiceS3
from diagrams.onprem.client import Client
from diagrams.onprem.compute import Server
from git import Repo

import aws_dac_generator


# import yaml


class Services:
    WEB_SERVER = "web_server"
    LOAD_BALANCER = "lb"
    MQ = "message_queue"
    AWS_CLOUDTRAIL = "aws_cloudtrail"
    AWS_LAMBDA = "aws_lambda"
    CACHE = "cache"
    DATABASE = "database"
    DOCKER = "docker"
    APP_SERVER = "app_server"
    AWS_SERVICE = "aws_service"
    AWS_SQS = "aws_sqs"
    AWS_SNS = "aws_sns"
    AWS_RDS = "aws_rds"
    AWS_S3 = "aws_s3"
    STATIC_CONTENT= "static_content"



def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

class Githubdisovery():
    def __init__(self):
        self.services_discovered = {}

    def parse_from_docker_file(self, file_content: str):
        services_discovered = self.services_discovered
        services_discovered[Services.DOCKER] = {}
        for line in file_content.split("\n"):
            if 'CMD' in line:
                if 'npm' in line:
                    services_discovered[Services.DOCKER][Services.APP_SERVER] = "Nodejs"
                elif 'flask' in line:
                    services_discovered[Services.DOCKER][Services.APP_SERVER] = "Flask"
                elif 'django' in line:
                    services_discovered[Services.DOCKER][Services.APP_SERVER] = 'Django'
                elif 'start-kafka' in line:
                    services_discovered[Services.DOCKER][Services.MQ] = 'kafka'
                elif 'rabbitmq' in line:
                    services_discovered[Services.DOCKER][Services.MQ] = 'rabbitmq'
        print(self.services_discovered)
        return


    def parse_from_docker_compose(self, file_content: str):
        self.services_discovered[Services.DOCKER] = {}


    def parse_from_nginx_conf(self, file_content: str):
        start = "upstream backend {"
        end = "}"
        server_entries = find_between(file_content, start, end)
        servers_count =0
        servers = []
        for entry in server_entries.split("\n"):
            if entry.strip().startswith("server"):
                servers_count += 1
                servers.append(entry.strip().split(" ")[1])
        self.services_discovered[Services.LOAD_BALANCER] = {"servers_count": servers_count, "servers": servers}
        return

    def parse_from_package_json(self, file_content: str):
        json_dict = json.loads(file_content)
        services_discovered = self.services_discovered
        services_discovered[Services.APP_SERVER] = "NodeJs"
        dependencies = json_dict.get("dependencies")
        discovery_map = [
            {
                "search_service" : Services.DATABASE,
                "searchable_keywords": ["mysql", "mongodb", "postgres"]
            },
            {
                "search_service": Services.CACHE,
                "searchable_keywords": ["redis"]
            },
        ]

        if dependencies:
            for discovery_entry in discovery_map:
                search_service = discovery_entry['search_service']
                searchable_keywords = discovery_entry['searchable_keywords']
                discovered_entities = services_discovered.get(search_service, [])
                for key in dependencies.keys():
                    for keyword in searchable_keywords:
                        if keyword in key:
                            discovered_entities.append(keyword)
                services_discovered[search_service] = discovered_entities
        return

    def parse_from_requirements_txt(self, file_content: str):
        services_discovered = self.services_discovered
        discovery_map = [
            {
                "search_service" : Services.DATABASE,
                "searchable_keywords": {"mysql": "mysqlclient" , "mongodb": "pymongo", "postgres" : "postgres"}
            },
            {
                "search_service": Services.CACHE,
                "searchable_keywords": {"redis": "redis"}
            },
        ]
        lib_entries = file_content.split("\n")
        for entry in lib_entries:
            for discovery_entry in discovery_map:
                search_service = discovery_entry['search_service']
                searchable_keywords = discovery_entry['searchable_keywords']
                discovered_entities = services_discovered.get(search_service, [])
                for key,val in searchable_keywords.items():
                    if val in entry.split("==")[0]:
                        discovered_entities.append(key)
                services_discovered[search_service] = discovered_entities
        return

    def parse_from_py_files(self, file_content: str):
        services_discovered = self.services_discovered
        # Fetch from boto3 client access for AWS.
        # Similarly fetch for Azure services as well with appropriate key_words with respective cloud call
        boto3_services = {Services.AWS_S3: "s3", Services.AWS_SQS: "sqs", Services.AWS_SNS: "sns", Services.AWS_RDS: "rds",
                          Services.AWS_LAMBDA: "lambda", Services.AWS_CLOUDTRAIL: "cloudtrail"}
        for key, val in boto3_services.items():
            if f"boto3.client('{val}')" in file_content or f'boto3.client("{val}")' in file_content:
                services_discovered[key] = "enabled"

        return

    def parse_from_js_files(self, file_content: str):
        return


# List all files in the repository
    def discover_services_in_repo(self, directory):
        #files = []
        services_discovered = self.services_discovered
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if filename == 'Dockerfile':
                    file_content = read_file(file_path)
                    self.parse_from_docker_file(file_content)
                elif filename.lower() == 'package.json':
                    file_content = read_file(file_path)
                    self.parse_from_package_json(file_content)
                elif filename.lower() == 'requirements.txt':
                    file_content = read_file(file_path)
                    self.parse_from_requirements_txt(file_content)
                elif filename.endswith(".py"):
                    file_content = read_file(file_path)
                    self.parse_from_py_files(file_content)
                elif filename == 'load-balancer.conf':
                    file_content = read_file(file_path)
                    self.parse_from_nginx_conf(file_content)
                elif filename.split(".")[-1].lower() in ["jpg", "jpeg", "png", "mpg", "mp4", "swf", "avi" ]:
                    services_discovered[Services.STATIC_CONTENT] = "enabled"
                elif filename.split(".")[-1].lower() in ["js"]:
                    services_discovered[Services.WEB_SERVER] = 'enabled'

                #files.append(file_path)
        return services_discovered

# Clone a repository
def clone_repo(url, directory):
    if not os.path.exists(directory):
        Repo.clone_from(url, directory)
        print(f"Cloned repository to {directory}")
    else:
        print(f"Repository already exists at {directory}")

# Read the content of a file
def read_file(filepath):
    with open(filepath, 'r') as file:
        content = file.read()
    return content


def build_aws_architecture(customerA_services, customerB_services) -> dict:
    architecture_content_dict = {
        "Diagram": {
            "DefinitionFiles":[{
                "Type": "URL",
                "Url": "https://raw.githubusercontent.com/awslabs/diagram-as-code/main/definitions/definition-for-aws-icons-light.yaml"
            }],
            "Resources": {
            "Canvas": {
                "Type": "AWS::Diagram::Canvas",
                "Direction": "Vertical",
                "Preset" : "AWSCloudNoLogo",
                "Children": [
                    "AWSCloud"
                ]
            }
    }}}

    for customer, _services_discovered in {"CustomerA": customerA_services, "CustomerB": customerB_services}.items():
        aws_cloud = {"Type":"AWS::Diagram::Cloud", "Children": []}
        vpc = {
            "Type": "AWS::VPC",
            "Children": []
        }
        aws_cloud["Children"].append(customer)
        architecture_content_dict["Diagram"]["Resources"][customer] = vpc
        architecture_content_dict["Diagram"]["Resources"]["AWSCloud"] = aws_cloud
        if _services_discovered.get(Services.STATIC_CONTENT) == "enabled":
            cloud_front = {
                "Type": "AWS::CloudFront"
            }
            architecture_content_dict["Diagram"]["Resources"]["AWSCloudFront"] = cloud_front
            aws_cloud["Children"].append("AWSCloudFront")

        if _services_discovered.get(Services.DOCKER):
            ec2 = {
                "Type" : "AWS::EC2::Instance"
            }
            architecture_content_dict["Diagram"]["Resources"]["EC2_1"] = ec2
            vpc["Children"].append("EC2_1")

        if _services_discovered.get(Services.AWS_SQS):
            sqs = {
                "Type": "AWS::SQS"
            }
            architecture_content_dict["Diagram"]["Resources"]["SQS"] = sqs
            aws_cloud["Children"].append("SQS")


        if _services_discovered.get(Services.AWS_SNS):
            sns = {
                "Type": "AWS::SNS"
            }
            architecture_content_dict["Diagram"]["Resources"]["SNS"] = sns
            aws_cloud["Children"].append("SNS")

        if _services_discovered.get(Services.AWS_S3):
            s3 = {
                "Type": "AWS::S3"
            }
            architecture_content_dict["Diagram"]["Resources"]["S3"] = s3
            aws_cloud["Children"].append("S3")

    #print(architecture_content_dict)
    return architecture_content_dict
    #return json.dumps(architecture_content_dict)


def m1(customerArepo, customerBrepo):

    # Example usage
    # repo_url = 'https://github.com/hameem76/hameem76.git'  # Replace with your repository URL0
    repo_directory = "/tmp/testrepos/customerA"# '/home/hameem/git_repos/hameem76/test_repos/customerA'  # Replace with the desired directory
    try:
        clone_repo(customerArepo, repo_directory)
    except git.exc.GitError as ge:
        print(f"Git repo does not exist {customerArepo}")
        raise Exception(f"Git repo does not exist {customerArepo}")

    #customerA = deepcopy(discover_services_in_repo(repo_directory))
    customerA = Githubdisovery().discover_services_in_repo(repo_directory)
    #print("CustomerA", customerA)
    repo_directory = "/tmp/testrepos/customerB"#'/home/hameem/git_repos/hameem76/test_repos/customerB'  # Replace with the desired directory
    try:
        clone_repo(customerBrepo, repo_directory)
    except git.exc.GitError as ge:
        print(f"Git repo does not exist {customerBrepo}")
        raise Exception(f"Git repo does not exist {customerBrepo}")

    customerB = Githubdisovery().discover_services_in_repo(repo_directory)
    #print("CustomerB", customerA)
    #print("discovery", services_discovered)
    #print(customerA)
    architecture_content = build_aws_architecture(customerA, customerB) 
    print("architecture \n", architecture_content)
    return architecture_content
    #st.write("hello world")
    # print("Files in repository:")
    # for file in files:
    #     print(file)

def discover_services(customer, repo):
    repo_directory = f"/tmp/testrepos/{customer}"
    try:
        clone_repo(repo, repo_directory)
    except git.exc.GitError as ge:
        print(f"Git repo does not exist {repo}")
        raise Exception(f"Git repo does not exist {repo}")

    discovered_services = Githubdisovery().discover_services_in_repo(repo_directory)
    return discovered_services

def generate_architecture_diagram(customerA_discovery, customerB_discovery):
    for customer, discovery in {"CustomerA": customerA_discovery, "CustomerB": customerB_discovery}.items():
        with Diagram(f"AWS Architecture - {customer}", filename=f"/tmp/diagrams/{customer}", show=False, direction="LR"):
            client = Client("Client")
            cdn = None
            app_server = discovery.get(Services.APP_SERVER) or discovery.get(Services.DOCKER, {}).get(Services.APP_SERVER)
            ec2_object = None
            with Cluster("AWS") as aws_cluster:
                if discovery.get(Services.STATIC_CONTENT) == 'enabled':
                    cdn = CloudFront("Content Delivery")
                if elb_detail := discovery.get(Services.LOAD_BALANCER):
                    elb = ElasticLoadBalancing("Application LB")
                    if cdn:
                        cdn >> elb

                    if elb:
                        with Cluster("EC2 instance"):
                            ec2_instances = EC2Instances(f"EC2 {" ".join(elb_detail.get("servers", ""))}")
                            if app_server:
                                Server(app_server)
                            if cdn:
                                Server("Webserver")
                            ec2_object =  ec2_instances
                            elb >> ec2_instances
                else:
                    ec2 = EC2("EC2")
                    ec2_object= ec2
                    if app_server:
                        Server(app_server)
                    if cdn:
                        Server("WebServer")
                    prev_element = cdn or client
                    prev_element >> ec2

            database = discovery.get(Services.DATABASE, [])
            db_objects = []
            for db in database:
                db_obj = Database(db)
                db_objects.append(db_obj)

            ec2_links: list[Any] = db_objects
            if discovered_caches := discovery.get(Services.CACHE) :
                for cache_obj in  discovered_caches:
                    if cache_obj == 'redis':
                        cached_diag_obj = ElasticacheForRedis("Redis")
                    else:
                        cached_diag_obj = ElasticacheForMemcached("Other Cache")
                if discovery.get(Services.AWS_SQS) == 'enabled':
                    ec2_links.append(SimpleQueueServiceSqs("SQS Messaging"))
                if discovery.get(Services.AWS_SNS) == 'enabled':
                    ec2_links.append(SimpleNotificationServiceSns("SNS messaging"))
                if discovery.get(Services.AWS_S3) == 'enabled':
                    ec2_links.append(SimpleStorageServiceS3("S3"))
                if discovery.get(Services.AWS_LAMBDA) == 'enabled':
                    ec2_links.append(Lambda("Lambda"))
                if discovery.get(Services.AWS_CLOUDTRAIL) == 'enabled':
                    ec2_links.append(Cloudtrail("Cloudtrail"))

                ec2_links.append(cached_diag_obj)
            ec2_object >> ec2_links
            client >> (cdn or elb)

    #print("Diagram generated")


if __name__ == '__main__':
    import shutil
    # Buiild the UI
    standalone = False
    if standalone:
        customerA_url = "https://github.com/hameem76/test_repo_customerA"#st.text_input("CustomerA Repo URL")
        customerB_url =  "https://github.com/hameem76/test_repo_customerB"#st.text_input("CustomerB repo URL")
        #architecture = m1(customerA_url, customerB_url)
        customerA_discoveries = discover_services("CustomerA", customerA_url)
        customerB_discoveries = discover_services("CustomerB", customerB_url)
        #print(customerA_discoveries, customerB_discoveries)
        generate_architecture_diagram(customerA_discoveries, customerB_discoveries)
        # repo_dirs = ["/tmp/testrepos", "/tmp/diagrams"]
        # for repo_dir in repo_dirs:
        #     if os.path.exists(repo_dir):
        #         shutil.rmtree(repo_dir)
        #print(architecture)

    else:
        st.title("Discover Services from Git repos and build architecture")
        customerA_url = st.text_input("Customer-A Repo URL")
        customerB_url = st.text_input("Customer-B Repo URL")
        try:
            if st.button("Generate"):
                #architecture = m1(customerA_url, customerB_url)
                customerA_discoveries = discover_services("CustomerA", customerA_url)
                customerB_discoveries = discover_services("CustomerB", customerB_url)
                aws_dac_generator.generate_architecture_diagram(customerA_discoveries, customerB_discoveries)
                #generate_architecture_diagram(customerA_discoveries, customerB_discoveries)
                st.image("/tmp/diagrams/CustomerA.png")
                st.image("/tmp/diagrams/CustomerB.png")
        except Exception as ex:
            st.error(str(ex))
        finally:
            repo_dirs = ["/tmp/testrepos", "/tmp/diagrams"]
            for repo_dir in repo_dirs:
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir)
