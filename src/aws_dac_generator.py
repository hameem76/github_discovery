from dis import disco

from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2, EC2Instance, EC2Instances, Lambda
from diagrams.aws.database import Database, ElasticacheForRedis, ElasticacheForMemcached, RDSInstance
from diagrams.aws.general import Users
from diagrams.aws.integration import SimpleQueueServiceSqs, SimpleNotificationServiceSns
from diagrams.aws.management import Cloudtrail
from diagrams.aws.network import NetworkingAndContentDelivery, VPC, ElasticLoadBalancing, CloudFront
from diagrams.aws.storage import SimpleStorageServiceS3
from diagrams.gcp.network import VirtualPrivateCloud
from diagrams.generic.network import Subnet
from diagrams.onprem.client import Client
from diagrams.onprem.compute import Server


# with Diagram("Diagram", direction="TB"):
#     with Cluster("Compute Cluster"):
#         EC2 = EC2("EC2")
#         EC2Instance = EC2Instance("EC2Instance")
#         EC2Instances = EC2Instances("EC2Instances")
#         EC2Ami = EC2Ami("EC2Ami")
#         LambdaFunction = LambdaFunction("LambdaFunction")
#
#         EC2 >> EC2Instance >> LambdaFunction


def test_diagram():
    with Diagram("AWS Infrastructure", show=False):
        # Create a Region
        vpc = VPC("My VPC")
        cdn = NetworkingAndContentDelivery("CDN")
        # Create Subnets (representing Availability Zones)
        subnet1 = Subnet("Availability Zone 1")
        subnet2 = Subnet("Availability Zone 2")

        # Attach EC2 instances inside the subnets
        ec2_1 = EC2("EC2 Instance 1")
        ec2_2 = EC2("EC2 Instance 2")
        cdn = NetworkingAndContentDelivery("CDN")
        # Define relationships between VPC, Subnets, and EC2 instances
        vpc >> subnet1 >> ec2_1
        vpc >> subnet2 >> ec2_2

def generate_architecture_diagram(customerA_discovery, customerB_discovery):
    from main import Services
    for customer, discovery in {"CustomerA": customerA_discovery, "CustomerB": customerB_discovery}.items():
        #continue
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

            ec2_links = db_objects
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

    print("Diagram generated")

if __name__ == '__main__':
    generate_architecture_diagram({}, {})
    #test_diagram()